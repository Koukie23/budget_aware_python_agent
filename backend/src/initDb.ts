import { initSchema, pool } from "./db.js";

await initSchema();
console.log("Schema ready.");
await pool.end();
