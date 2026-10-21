#!/usr/bin/env python3
"""Build train / validation / test JSONL for T4. English stdout.

Train: full MBPP, task_id 601-974.
Validation and test (evaluation): sanitized MBPP, same official ID ranges.
Hidden tests are empty until EvalPlus is reviewed before T8.
Token-limit decisions wait until the tokenizer is chosen in T5.
"""

from __future__ import annotations

import ast
import json
import statistics
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.prompt import generate_prompt  # noqa: E402

RAW = ROOT / "data" / "raw"
OUT = ROOT / "data" / "processed"
KEEP = {
    "train": "full",
    "validation": "sanitized",
    "test": "sanitized",
}


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


def as_imports(value) -> list[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value] if value.strip() else []
    return list(value)


def load_full() -> list[dict]:
    return [json.loads(line) for line in (RAW / "mbpp.jsonl").read_text().splitlines() if line.strip()]


def load_sanitized() -> list[dict]:
    return json.loads((RAW / "sanitized-mbpp.json").read_text())


def to_record(raw: dict, source: str) -> dict | None:
    task_id = raw["task_id"]
    split = split_of(task_id)
    requirement = raw["prompt"] if source == "sanitized" else raw["text"]
    imports = as_imports(raw.get("test_imports") if source == "sanitized" else raw.get("test_setup_code"))
    tests = list(raw["test_list"])
    try:
        name, signature = first_signature(raw["code"])
    except (SyntaxError, ValueError) as exc:
        return {
            "_skip": True,
            "task_id": task_id,
            "split": split,
            "source": source,
            "reason": str(exc),
        }
    prompt = generate_prompt(requirement, signature, tests)
    return {
        "task_id": task_id,
        "source": f"mbpp-{source}",
        "split": split,
        "requirement": requirement,
        "function_name": name,
        "function_signature": signature,
        "prompt": prompt,
        "target_code": raw["code"],
        "feedback_tests": tests,
        "hidden_tests": [],
        "test_imports": imports,
        "prompt_chars": len(prompt),
        "target_chars": len(raw["code"]),
        "n_feedback_tests": len(tests),
    }


def percentile(values: list[int], p: float) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    idx = min(len(ordered) - 1, max(0, int(round((p / 100) * (len(ordered) - 1)))))
    return ordered[idx]


def summarize(records: list[dict]) -> dict:
    prompts = [r["prompt_chars"] for r in records]
    targets = [r["target_chars"] for r in records]
    tests = [r["n_feedback_tests"] for r in records]
    return {
        "n": len(records),
        "task_id_min": min(r["task_id"] for r in records) if records else None,
        "task_id_max": max(r["task_id"] for r in records) if records else None,
        "prompt_chars": {
            "mean": round(statistics.fmean(prompts), 1) if prompts else 0,
            "p50": percentile(prompts, 50),
            "p95": percentile(prompts, 95),
            "max": max(prompts) if prompts else 0,
        },
        "target_chars": {
            "mean": round(statistics.fmean(targets), 1) if targets else 0,
            "p50": percentile(targets, 50),
            "p95": percentile(targets, 95),
            "max": max(targets) if targets else 0,
        },
        "n_feedback_tests": dict(Counter(tests)),
    }


def main() -> None:
    by_source = {"full": load_full(), "sanitized": load_sanitized()}
    OUT.mkdir(parents=True, exist_ok=True)
    stats = {
        "corpus_policy": KEEP,
        "hidden_tests": "empty until EvalPlus is reviewed before T8",
        "prompt": "requirement + function_signature + feedback_tests; see agent/prompt.py",
        "tokenizer": "not applied; max length is set in T5 with the chosen model tokenizer",
        "skipped": [],
        "splits": {},
    }

    for split, source in KEEP.items():
        kept: list[dict] = []
        for raw in by_source[source]:
            if split_of(raw["task_id"]) != split:
                continue
            rec = to_record(raw, source)
            if rec.get("_skip"):
                stats["skipped"].append(rec)
                continue
            rec.pop("_skip", None)
            kept.append(rec)
        kept.sort(key=lambda r: r["task_id"])
        path = OUT / f"{split}.jsonl"
        with path.open("w") as f:
            for rec in kept:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        stats["splits"][split] = summarize(kept)
        stats["splits"][split]["source"] = source
        stats["splits"][split]["path"] = str(path.relative_to(ROOT))
        print(f"{split:12} source={source:10} n={len(kept):4} -> {path.relative_to(ROOT)}")

    (OUT / "stats.json").write_text(json.dumps(stats, indent=2) + "\n")
    print(f"Wrote { (OUT / 'stats.json').relative_to(ROOT) }")
    if stats["skipped"]:
        print("Skipped:", stats["skipped"])


if __name__ == "__main__":
    main()
