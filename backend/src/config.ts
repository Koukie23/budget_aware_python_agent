import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

export const ROOT = path.resolve(here, "..", "..");
export const PORT = Number(process.env.PORT ?? 3000);
export const DATABASE_URL = process.env.DATABASE_URL ?? "postgres://localhost:5432/budget_agent";
export const AGENT_URL = process.env.AGENT_URL ?? "http://127.0.0.1:8000";
export const SAMPLES_PATH = path.join(ROOT, "data", "samples", "t1_samples.jsonl");
export const SCHEMA_PATH = path.join(ROOT, "backend", "db", "schema.sql");
