import fs from "node:fs";
import { SAMPLES_PATH } from "./config.js";

export interface Example {
  example_task_id: number;
  split: string;
  requirement: string;
  function_name: string;
  function_signature: string;
  feedback_tests: string[];
  test_imports: string[];
}

export function loadExamples(): Example[] {
  return fs
    .readFileSync(SAMPLES_PATH, "utf8")
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => {
      const rec = JSON.parse(line);
      return {
        example_task_id: rec.task_id,
        split: rec.split,
        requirement: rec.requirement,
        function_name: rec.function_name,
        function_signature: rec.function_signature,
        feedback_tests: rec.feedback_tests,
        test_imports: rec.test_imports ?? [],
      };
    });
}
