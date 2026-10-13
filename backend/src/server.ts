import cors from "cors";
import express, { type NextFunction, type Request, type Response } from "express";
import { z } from "zod";
import { AGENT_URL, PORT } from "./config.js";
import { initSchema, markInterruptedTasks, pool } from "./db.js";
import { loadExamples } from "./examples.js";

const app = express();
app.use(cors());
app.use(express.json({ limit: "1mb" }));

const SIGNATURE_RE = /^def\s+([A-Za-z_]\w*)\s*\(.*\)\s*(->\s*.+)?$/;

const createTaskSchema = z.object({
  requirement: z.string().trim().min(10, "Requirement must be at least 10 characters").max(4000),
  function_signature: z
    .string()
    .trim()
    .regex(SIGNATURE_RE, "Signature must look like: def name(arg1, arg2)"),
  feedback_tests: z
    .array(z.string().trim().startsWith("assert ", "Each test must start with 'assert '"))
    .min(1, "Add at least one test")
    .max(50),
  test_imports: z.array(z.string().trim()).max(10).default([]),
  preference: z.enum(["cheap", "balanced", "quality"]),
  budget_usd: z.number().positive("Budget must be greater than 0").max(10),
  mock_scenario: z.enum(["pass", "repair", "escalate", "exhaust", "timeout"]).default("pass"),
  example_task_id: z.number().int().nullable().default(null),
});

const asyncRoute =
  (fn: (req: Request, res: Response) => Promise<unknown>) =>
  (req: Request, res: Response, next: NextFunction) =>
    fn(req, res).catch(next);

app.get("/api/health", asyncRoute(async (_req, res) => {
  await pool.query("SELECT 1");
  let agent = "unreachable";
  try {
    const r = await fetch(`${AGENT_URL}/health`);
    agent = r.ok ? "ok" : `http ${r.status}`;
  } catch {
    /* agent down */
  }
  res.json({ backend: "ok", database: "ok", agent });
}));

app.get("/api/examples", (_req, res) => {
  res.json(loadExamples());
});

app.post("/api/tasks", asyncRoute(async (req, res) => {
  const parsed = createTaskSchema.safeParse(req.body);
  if (!parsed.success) {
    res.status(400).json({ error: "Invalid input", details: parsed.error.issues.map((i) => i.message) });
    return;
  }
  const body = parsed.data;
  const functionName = SIGNATURE_RE.exec(body.function_signature)![1];
  const signature = body.function_signature.replace(/:\s*$/, "");

  const { rows } = await pool.query(
    `INSERT INTO tasks (example_task_id, requirement, function_name, function_signature,
                        feedback_tests, test_imports, preference, budget_usd, mock_scenario)
     VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
     RETURNING id`,
    [
      body.example_task_id,
      body.requirement,
      functionName,
      signature,
      JSON.stringify(body.feedback_tests),
      JSON.stringify(body.test_imports),
      body.preference,
      body.budget_usd,
      body.mock_scenario,
    ],
  );
  const taskId: number = rows[0].id;

  try {
    const agentRes = await fetch(`${AGENT_URL}/runs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        task_id: taskId,
        requirement: body.requirement,
        function_name: functionName,
        function_signature: signature,
        feedback_tests: body.feedback_tests,
        test_imports: body.test_imports,
        preference: body.preference,
        budget_usd: body.budget_usd,
        mock_scenario: body.mock_scenario,
        example_task_id: body.example_task_id,
      }),
    });
    if (!agentRes.ok) throw new Error(`agent service returned ${agentRes.status}`);
  } catch (err) {
    await pool.query(
      `UPDATE tasks SET status = 'system_error', stop_reason = $2, updated_at = now() WHERE id = $1`,
      [taskId, `agent service unavailable: ${(err as Error).message}`],
    );
  }
  res.status(201).json({ id: taskId });
}));

app.get("/api/tasks", asyncRoute(async (_req, res) => {
  const { rows } = await pool.query(
    `SELECT id, example_task_id, requirement, function_name, preference, budget_usd, status,
            model_calls, total_actual_cost_usd, created_at
       FROM tasks ORDER BY created_at DESC LIMIT 100`,
  );
  res.json(rows);
}));

app.get("/api/tasks/:id", asyncRoute(async (req, res) => {
  const id = Number(req.params.id);
  if (!Number.isInteger(id)) {
    res.status(400).json({ error: "Invalid task id" });
    return;
  }
  const task = await pool.query(`SELECT * FROM tasks WHERE id = $1`, [id]);
  if (task.rowCount === 0) {
    res.status(404).json({ error: "Task not found" });
    return;
  }
  const steps = await pool.query(
    `SELECT mc.step_index, mc.action, mc.model_id, mc.estimated_cost_usd, mc.actual_cost_usd,
            mc.input_tokens, mc.output_tokens, mc.latency_sec,
            cv.version, cv.code,
            tr.status AS test_status, tr.tests_passed, tr.tests_total, tr.duration_sec,
            tr.error_summary
       FROM model_calls mc
       JOIN code_versions cv ON cv.model_call_id = mc.id
       JOIN test_runs tr ON tr.code_version_id = cv.id
      WHERE mc.task_id = $1
      ORDER BY mc.step_index`,
    [id],
  );
  res.json({ ...task.rows[0], steps: steps.rows });
}));

// Callbacks from the FastAPI agent service.
app.post("/internal/tasks/:id/started", asyncRoute(async (req, res) => {
  await pool.query(
    `UPDATE tasks SET status = 'running', executor = $2, updated_at = now() WHERE id = $1`,
    [Number(req.params.id), req.body.executor ?? null],
  );
  res.json({ ok: true });
}));

app.post("/internal/tasks/:id/steps", asyncRoute(async (req, res) => {
  const taskId = Number(req.params.id);
  const s = req.body;
  const client = await pool.connect();
  try {
    await client.query("BEGIN");
    const call = await client.query(
      `INSERT INTO model_calls (task_id, step_index, action, model_id, estimated_cost_usd,
                                actual_cost_usd, input_tokens, output_tokens, latency_sec)
       VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING id`,
      [taskId, s.index, s.action, s.model_id, s.estimated_cost_usd, s.actual_cost_usd,
       s.input_tokens, s.output_tokens, s.model_latency_sec],
    );
    const version = await client.query(
      `INSERT INTO code_versions (task_id, model_call_id, version, code)
       VALUES ($1, $2, $3, $4) RETURNING id`,
      [taskId, call.rows[0].id, s.index, s.code],
    );
    await client.query(
      `INSERT INTO test_runs (task_id, code_version_id, status, tests_passed, tests_total,
                              duration_sec, error_summary)
       VALUES ($1, $2, $3, $4, $5, $6, $7)`,
      [taskId, version.rows[0].id, s.test_status, s.tests_passed, s.tests_total,
       s.test_duration_sec, s.error_summary],
    );
    await client.query(
      `UPDATE tasks
          SET model_calls = model_calls + 1,
              total_estimated_cost_usd = total_estimated_cost_usd + $2,
              total_actual_cost_usd = total_actual_cost_usd + $3,
              total_input_tokens = total_input_tokens + $4,
              total_output_tokens = total_output_tokens + $5,
              final_code = $6,
              updated_at = now()
        WHERE id = $1`,
      [taskId, s.estimated_cost_usd, s.actual_cost_usd, s.input_tokens, s.output_tokens, s.code],
    );
    await client.query("COMMIT");
  } catch (err) {
    await client.query("ROLLBACK");
    throw err;
  } finally {
    client.release();
  }
  res.json({ ok: true });
}));

app.post("/internal/tasks/:id/finish", asyncRoute(async (req, res) => {
  const r = req.body;
  await pool.query(
    `UPDATE tasks
        SET status = $2, stop_reason = $3,
            policy = COALESCE($4, policy),
            wall_time_sec = COALESCE($5, wall_time_sec), updated_at = now()
      WHERE id = $1`,
    [Number(req.params.id), r.status, r.stop_reason ?? null, r.policy ?? null,
     r.wall_time_sec ?? null],
  );
  res.json({ ok: true });
}));

app.use((err: Error, _req: Request, res: Response, _next: NextFunction) => {
  console.error(err);
  res.status(500).json({ error: "Internal server error" });
});

await initSchema();
const interrupted = await markInterruptedTasks();
if (interrupted) console.log(`Marked ${interrupted} interrupted task(s) as system_error.`);
app.listen(PORT, "127.0.0.1", () => console.log(`Backend listening on http://127.0.0.1:${PORT}`));
