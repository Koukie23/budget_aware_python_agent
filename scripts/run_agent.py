#!/usr/bin/env python3
"""T2 command-line prototype. All output is English."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent.config import DEFAULT_BUDGET_USD  # noqa: E402
from agent.controller import run_agent  # noqa: E402
from agent.models import CLIENT_KINDS, MOCK_SCENARIOS, make_client  # noqa: E402
from agent.policy import PREFERENCES  # noqa: E402
from agent.task import load_task  # noqa: E402

DEFAULT_SAMPLES = ROOT / "data" / "samples" / "t1_samples.jsonl"
RUNS_DIR = ROOT / "runs"


def main() -> int:
    p = argparse.ArgumentParser(description="Budget-aware Python coding agent (T2 CLI).")
    p.add_argument("--task-id", type=int, default=2)
    p.add_argument("--samples", type=Path, default=DEFAULT_SAMPLES)
    p.add_argument("--preference", choices=PREFERENCES, default="balanced")
    p.add_argument("--budget", type=float, default=DEFAULT_BUDGET_USD, help="USD")
    p.add_argument("--client", choices=CLIENT_KINDS, default="local")
    p.add_argument("--adapter", type=Path, default=None, help="LoRA adapter dir (local client)")
    p.add_argument("--mock-scenario", choices=MOCK_SCENARIOS, default="pass")
    p.add_argument("--executor", choices=("docker", "subprocess"), default="docker")
    p.add_argument("--no-save", action="store_true")
    args = p.parse_args()

    task = load_task(args.samples, args.task_id)
    client = make_client(args.client, adapter=args.adapter, mock_scenario=args.mock_scenario)
    result = run_agent(task, args.preference, args.budget, client, executor=args.executor)

    print(f"Task {task.task_id}: {task.requirement}")
    print(f"Policy ({result.preference}): {result.policy}")
    for s in result.steps:
        print(
            f"  Step {s.index} [{s.action}] {s.model_id}: tests {s.tests_passed}/{s.tests_total} "
            f"{s.test_status} | est ${s.estimated_cost_usd:.6f} actual ${s.actual_cost_usd:.6f} "
            f"| tokens {s.input_tokens}+{s.output_tokens}"
        )
        if s.error_summary:
            for line in s.error_summary.splitlines():
                print(f"      {line}")
    print(f"Status: {result.status} - {result.stop_reason}")
    print(
        f"Calls {result.model_calls} | est ${result.total_estimated_cost_usd:.6f} "
        f"| actual ${result.total_actual_cost_usd:.6f} / budget ${result.budget_usd:.6f} "
        f"| wall {result.wall_time_sec:.2f}s"
    )
    if result.final_code:
        print("Final code:")
        print(result.final_code)

    if not args.no_save:
        RUNS_DIR.mkdir(exist_ok=True)
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        out = RUNS_DIR / f"run_{task.task_id}_{args.client}_{stamp}.json"
        out.write_text(json.dumps(result.to_dict(), indent=2))
        print(f"Saved trace: {out.relative_to(ROOT)}")
    return 0 if result.status == "succeeded" else 2


if __name__ == "__main__":
    raise SystemExit(main())
