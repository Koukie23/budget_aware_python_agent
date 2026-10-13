"""Model call adapter. Only a deterministic mock exists until the real models are wired (T7)."""

from __future__ import annotations

import re
import time
from dataclasses import dataclass

from agent.config import FINETUNED_MODEL_ID, MAX_OUTPUT_TOKENS, PRICE_PER_1K, STRONG_MODEL_ID
from agent.task import CodingTask

# Scenarios control how the mock behaves so every state-machine branch can be exercised.
#   pass      : the fine-tuned model solves on the first try
#   repair    : the fine-tuned model fails once, then fixes it on repair
#   escalate  : the fine-tuned model always fails, the strong model solves
#   exhaust   : every model always fails
#   timeout   : the fine-tuned model first returns an infinite loop, then solves on repair
MOCK_SCENARIOS = ("pass", "repair", "escalate", "exhaust", "timeout")


@dataclass
class ModelResponse:
    model_id: str
    raw_text: str
    code: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_sec: float


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def price(model_id: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICE_PER_1K[model_id]
    return input_tokens / 1000 * p["input"] + output_tokens / 1000 * p["output"]


def estimate_call_cost(model_id: str, prompt: str) -> float:
    """Conservative pre-call estimate: assume the full output-token cap is used."""
    return price(model_id, estimate_tokens(prompt), MAX_OUTPUT_TOKENS)


def build_prompt(task: CodingTask, previous_code: str | None, error_summary: str | None) -> str:
    tests = "\n".join(task.feedback_tests)
    parts = [
        "You are an expert Python programmer.",
        f"Task: {task.requirement}",
        f"Implement exactly this function: {task.function_signature}",
        f"Your code should pass these tests:\n{tests}",
    ]
    if previous_code is not None:
        parts.append(f"Your previous code:\n```python\n{previous_code}\n```")
        parts.append(f"It failed with:\n{error_summary}")
        parts.append("Fix the code.")
    parts.append("Return only one ```python``` code block.")
    return "\n\n".join(parts)


def extract_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()


def _wrong_code(task: CodingTask) -> str:
    return f"{task.function_signature}:\n    return None\n"


def _loop_code(task: CodingTask) -> str:
    return f"{task.function_signature}:\n    while True:\n        pass\n"


class MockModelClient:
    def __init__(self, scenario: str):
        if scenario not in MOCK_SCENARIOS:
            raise ValueError(f"scenario must be one of {MOCK_SCENARIOS}")
        self.scenario = scenario
        self.calls: dict[str, int] = {FINETUNED_MODEL_ID: 0, STRONG_MODEL_ID: 0}

    def _solve(self, model_id: str, task: CodingTask, nth: int) -> str:
        good = task.target_code or _wrong_code(task)
        s = self.scenario
        if s == "pass":
            return good
        if s == "exhaust":
            return _wrong_code(task)
        if model_id == STRONG_MODEL_ID:
            return good
        # fine-tuned model
        if s == "repair":
            return good if nth >= 2 else _wrong_code(task)
        if s == "timeout":
            return good if nth >= 2 else _loop_code(task)
        return _wrong_code(task)  # escalate

    def generate(self, model_id: str, prompt: str, task: CodingTask) -> ModelResponse:
        start = time.monotonic()
        self.calls[model_id] += 1
        code = self._solve(model_id, task, self.calls[model_id])
        raw = f"```python\n{code}\n```"
        in_tok = estimate_tokens(prompt)
        out_tok = min(estimate_tokens(raw), MAX_OUTPUT_TOKENS)
        return ModelResponse(
            model_id=model_id,
            raw_text=raw,
            code=extract_code(raw),
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=price(model_id, in_tok, out_tok),
            latency_sec=time.monotonic() - start,
        )
