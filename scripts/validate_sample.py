#!/usr/bin/env python3
"""Execute feedback and hidden tests for a T1 sample. English stdout."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SAMPLES = ROOT / "data" / "samples" / "t1_samples.jsonl"


def load_samples(path: Path) -> list[dict]:
    records = []
    with path.open() as f:
        for line in f:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def run_tests(code: str, imports: list[str], tests: list[str]) -> list[dict]:
    namespace: dict = {}
    exec(code, namespace)
    for statement in imports or []:
        exec(statement, namespace)
    results = []
    for test in tests:
        try:
            exec(test, namespace)
            results.append({"test": test, "passed": True, "error": None})
        except Exception as exc:
            results.append(
                {
                    "test": test,
                    "passed": False,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate one T1 MBPP sample.")
    parser.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    parser.add_argument("--task-id", type=int, default=2)
    args = parser.parse_args()

    records = [r for r in load_samples(args.samples) if r["task_id"] == args.task_id]
    if not records:
        print(f"No sample with task_id={args.task_id}", file=sys.stderr)
        return 1
    sample = records[0]
    tests = list(sample.get("feedback_tests") or []) + list(sample.get("hidden_tests") or [])
    results = run_tests(sample["target_code"], sample.get("test_imports") or [], tests)
    passed = sum(1 for item in results if item["passed"])
    print(f"task_id={sample['task_id']} split={sample['split']}")
    print(f"function_signature={sample['function_signature']}")
    print(f"requirement={sample['requirement']}")
    print(f"tests {passed}/{len(results)} passed")
    for item in results:
        status = "PASSED" if item["passed"] else "FAILED"
        print(f"  [{status}] {item['test']}")
        if item["error"]:
            print(f"           {item['error']}")
    return 0 if passed == len(results) and results else 1


if __name__ == "__main__":
    raise SystemExit(main())
