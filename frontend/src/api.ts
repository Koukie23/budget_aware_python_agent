export type Preference = "cheap" | "balanced" | "quality";
export type MockScenario = "pass" | "repair" | "escalate" | "exhaust" | "timeout";
export type TaskStatus =
  | "pending"
  | "running"
  | "succeeded"
  | "failed"
  | "budget_exhausted"
  | "system_error";

export interface Example {
  example_task_id: number;
  split: string;
  requirement: string;
  function_name: string;
  function_signature: string;
  feedback_tests: string[];
  test_imports: string[];
}

export interface Step {
  step_index: number;
  action: "generate" | "repair" | "escalate";
  model_id: string;
  estimated_cost_usd: number;
  actual_cost_usd: number;
  input_tokens: number;
  output_tokens: number;
  latency_sec: number;
  version: number;
  code: string;
  test_status: "passed" | "failed" | "timeout" | "system_error";
  tests_passed: number;
  tests_total: number;
  duration_sec: number;
  error_summary: string | null;
}

export interface TaskDetail {
  id: number;
  example_task_id: number | null;
  requirement: string;
  function_name: string;
  function_signature: string;
  feedback_tests: string[];
  test_imports: string[];
  preference: Preference;
  budget_usd: number;
  mock_scenario: MockScenario;
  executor: string | null;
  status: TaskStatus;
  stop_reason: string | null;
  policy: string | null;
  final_code: string | null;
  model_calls: number;
  total_estimated_cost_usd: number;
  total_actual_cost_usd: number;
  total_input_tokens: number;
  total_output_tokens: number;
  wall_time_sec: number | null;
  created_at: string;
  steps: Step[];
}

export interface TaskSummary {
  id: number;
  example_task_id: number | null;
  requirement: string;
  function_name: string;
  preference: Preference;
  budget_usd: number;
  status: TaskStatus;
  model_calls: number;
  total_actual_cost_usd: number;
  created_at: string;
}

export interface CreateTaskInput {
  requirement: string;
  function_signature: string;
  feedback_tests: string[];
  test_imports: string[];
  preference: Preference;
  budget_usd: number;
  mock_scenario: MockScenario;
  example_task_id: number | null;
}

export class ApiError extends Error {
  constructor(message: string, public details: string[] = []) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    ...init,
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
  });
  const body = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(body.error ?? `Request failed (${res.status})`, body.details ?? []);
  return body as T;
}

export interface AgentOptions {
  preferences: Preference[];
  client: "local" | "mock" | "unknown";
  finetuned_model?: string;
  mock_scenarios: MockScenario[];
}

export const api = {
  options: () => request<AgentOptions>("/api/options"),
  examples: () => request<Example[]>("/api/examples"),
  createTask: (input: CreateTaskInput) =>
    request<{ id: number }>("/api/tasks", { method: "POST", body: JSON.stringify(input) }),
  task: (id: number) => request<TaskDetail>(`/api/tasks/${id}`),
  tasks: () => request<TaskSummary[]>("/api/tasks"),
};

export const isActive = (status: TaskStatus) => status === "pending" || status === "running";
