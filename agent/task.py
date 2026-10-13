from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CodingTask:
    task_id: int | str
    requirement: str
    function_name: str
    function_signature: str
    feedback_tests: list[str]
    test_imports: list[str] = field(default_factory=list)
    hidden_tests: list[str] = field(default_factory=list)
    target_code: str | None = None
    split: str | None = None


def load_task(samples_path: Path, task_id: int) -> CodingTask:
    with samples_path.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec["task_id"] == task_id:
                return CodingTask(
                    task_id=rec["task_id"],
                    requirement=rec["requirement"],
                    function_name=rec["function_name"],
                    function_signature=rec["function_signature"],
                    feedback_tests=list(rec.get("feedback_tests") or []),
                    test_imports=list(rec.get("test_imports") or []),
                    hidden_tests=list(rec.get("hidden_tests") or []),
                    target_code=rec.get("target_code"),
                    split=rec.get("split"),
                )
    raise KeyError(f"task_id {task_id} not found in {samples_path}")
