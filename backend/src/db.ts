import fs from "node:fs";
import pg from "pg";
import { DATABASE_URL, SCHEMA_PATH } from "./config.js";

// Return NUMERIC columns as JS numbers instead of strings.
pg.types.setTypeParser(1700, (value) => Number(value));

export const pool = new pg.Pool({ connectionString: DATABASE_URL });

export async function initSchema(): Promise<void> {
  await pool.query(fs.readFileSync(SCHEMA_PATH, "utf8"));
}

export async function markInterruptedTasks(): Promise<number> {
  const result = await pool.query(
    `UPDATE tasks
        SET status = 'system_error',
            stop_reason = 'interrupted: backend restarted while the run was in progress',
            updated_at = now()
      WHERE status IN ('pending', 'running')`,
  );
  return result.rowCount ?? 0;
}
