#!/usr/bin/env python3
"""Verify the raw MBPP files and write the T1 sample JSONL. English stdout."""

from __future__ import annotations

import ast
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "samples" / "t1_samples.jsonl"
T1_TASK_IDS = (2, 12, 555, 604)


def split_of(task_id: int) -> str:
    if task_id <= 10:
        return "prompt"
    if task_id <= 510:
        return "test"
    if task_id <= 600:
        return "validation"
    return "train"


def first_signature(code: str) -> tuple[str, str]:
    for node in ast.parse(code).body:
        if isinstance(node, ast.FunctionDef):
            return node.name, f"def {node.name}({ast.unparse(node.args)})"
    raise ValueError("no top-level function")


def tests_pass(code: str, imports: list[str], tests: list[str]) -> list[dict]:
    namespace: dict = {}
    exec(code, namespace)
    for statement in imports:
        exec(statement, namespace)
    results = []
    for test in tests:
        try:
            exec(test, namespace)
            results.append({"test": test, "passed": True, "error": None})
        except Exception as exc:
            results.append({"test": test, "passed": False, "error": f"{type(exc).__name__}: {exc}"})
    return results


def check(name: str, records: list[dict], imports_key: str, extra_tests_key: str | None) -> None:
    parse_fail = exec_fail = 0
    for rec in records:
        try:
            ast.parse(rec["code"])
        except SyntaxError:
            parse_fail += 1
            continue
        tests = list(rec["test_list"]) + list(rec.get(extra_tests_key) or [] if extra_tests_key else [])
        imports = rec.get(imports_key) or []
        if isinstance(imports, str):
            imports = [imports] if imports.strip() else []
        try:
            if not all(r["passed"] for r in tests_pass(rec["code"], imports, tests)):
                exec_fail += 1
        except Exception:
            exec_fail += 1
    splits = Counter(split_of(r["task_id"]) for r in records)
    print(f"{name}: {len(records)} problems, splits {dict(splits)}, "
          f"parse failures {parse_fail}, reference failing own tests {exec_fail}")


def main() -> None:
    sanitized = json.loads((RAW / "sanitized-mbpp.json").read_text())
    full = [json.loads(line) for line in (RAW / "mbpp.jsonl").read_text().splitlines() if line.strip()]
    check("sanitized", sanitized, "test_imports", None)
    check("full", full, "test_setup_code", "challenge_test_list")

    by_id = {r["task_id"]: r for r in sanitized}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w") as f:
        for task_id in T1_TASK_IDS:
            rec = by_id[task_id]
            name, signature = first_signature(rec["code"])
            imports = rec.get("test_imports") or []
            results = tests_pass(rec["code"], imports, rec["test_list"])
            sample = {
                "task_id": task_id,
                "source": "mbpp-sanitized",
                "split": split_of(task_id),
                "requirement": rec["prompt"],
                "function_name": name,
                "function_signature": signature,
                "target_code": rec["code"],
                "feedback_tests": rec["test_list"],
                "hidden_tests": [],
                "test_imports": imports,
                "reference_test_results": results,
            }
            f.write(json.dumps(sample, ensure_ascii=False) + "\n")
            passed = sum(r["passed"] for r in results)
            print(f"T1 sample {task_id} ({sample['split']}) {signature}: {passed}/{len(results)} passed")
    print(f"Wrote {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
