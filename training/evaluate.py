from __future__ import annotations

import json
from pathlib import Path

from agent.executor import run_tests
from training.generate import generate_code


def evaluate_records(
    records: list[dict],
    model,
    tokenizer,
    device,
    max_new_tokens: int,
    executor: str = "docker",
    limit: int | None = None,
) -> dict:
    rows = records if limit is None else records[:limit]
    results = []
    n_pass = 0
    extract_fail = 0
    for rec in rows:
        code = generate_code(
            model,
            tokenizer,
            rec["prompt"],
            device,
            max_new_tokens,
            function_name=rec.get("function_name"),
        )
        if not code:
            extract_fail += 1
            report_status = "failed"
            passed = 0
            total = len(rec["feedback_tests"])
            ok = False
        else:
            report = run_tests(code, rec["feedback_tests"], rec.get("test_imports") or [], backend=executor)
            report_status = report.status
            passed = report.passed
            total = report.total
            ok = report.all_passed
        n_pass += int(ok)
        results.append(
            {
                "task_id": rec["task_id"],
                "split": rec["split"],
                "passed": ok,
                "test_status": report_status,
                "tests_passed": passed,
                "tests_total": total,
                "generated_code": code,
            }
        )
    n = len(rows)
    return {
        "n": n,
        "n_pass": n_pass,
        "pass_at_1": (n_pass / n) if n else 0.0,
        "extract_fail": extract_fail,
        "results": results,
    }


def write_eval(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    slim = {k: v for k, v in payload.items() if k != "results"}
    slim["results"] = [
        {k: r[k] for k in r if k != "generated_code"} | {"generated_chars": len(r.get("generated_code") or "")}
        for r in payload["results"]
    ]
    path.write_text(json.dumps(slim, indent=2) + "\n")
