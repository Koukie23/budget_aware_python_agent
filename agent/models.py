"""Model call adapter: local LoRA for the fine-tuned model; strong API still unwired."""

from __future__ import annotations

import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from agent.config import (
    DEFAULT_ADAPTER_DIR,
    FINETUNED_MODEL_ID,
    MAX_OUTPUT_TOKENS,
    PRICE_PER_1K,
    STRONG_MODEL_ID,
)
from agent.extract import extract_code
from agent.prompt import generate_prompt, repair_prompt
from agent.task import CodingTask

# Scenarios control how the mock behaves so every state-machine branch can be exercised.
#   pass      : the fine-tuned model solves on the first try
#   repair    : the fine-tuned model fails once, then fixes it on repair
#   escalate  : the fine-tuned model always fails, the strong model solves
#   exhaust   : every model always fails
#   timeout   : the fine-tuned model first returns an infinite loop, then solves on repair
MOCK_SCENARIOS = ("pass", "repair", "escalate", "exhaust", "timeout")
CLIENT_KINDS = ("local", "mock")


@dataclass
class ModelResponse:
    model_id: str
    raw_text: str
    code: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_sec: float


class ModelClient(Protocol):
    def generate(self, model_id: str, prompt: str, task: CodingTask) -> ModelResponse: ...


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def price(model_id: str, input_tokens: int, output_tokens: int) -> float:
    p = PRICE_PER_1K[model_id]
    return input_tokens / 1000 * p["input"] + output_tokens / 1000 * p["output"]


def estimate_call_cost(model_id: str, prompt: str) -> float:
    """Conservative pre-call estimate: assume the full output-token cap is used."""
    return price(model_id, estimate_tokens(prompt), MAX_OUTPUT_TOKENS)


def build_prompt(task: CodingTask, previous_code: str | None, error_summary: str | None) -> str:
    if previous_code is None:
        return generate_prompt(task.requirement, task.function_signature, task.feedback_tests)
    return repair_prompt(
        task.requirement,
        task.function_signature,
        task.feedback_tests,
        previous_code,
        error_summary or "",
    )


def _wrong_code(task: CodingTask) -> str:
    return f"{task.function_signature}:\n    return None\n"


def _loop_code(task: CodingTask) -> str:
    return f"{task.function_signature}:\n    while True:\n        pass\n"


class MockModelClient:
    def __init__(self, scenario: str):
        if scenario not in MOCK_SCENARIOS:
            raise ValueError(f"scenario must be one of {MOCK_SCENARIOS}")
        self.scenario = scenario
        self.kind = "mock"
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
        if s == "repair":
            return good if nth >= 2 else _wrong_code(task)
        if s == "timeout":
            return good if nth >= 2 else _loop_code(task)
        return _wrong_code(task)  # escalate

    def generate(self, model_id: str, prompt: str, task: CodingTask) -> ModelResponse:
        start = time.monotonic()
        self.calls[model_id] = self.calls.get(model_id, 0) + 1
        code = self._solve(model_id, task, self.calls[model_id])
        raw = f"```python\n{code}\n```"
        in_tok = estimate_tokens(prompt)
        out_tok = min(estimate_tokens(raw), MAX_OUTPUT_TOKENS)
        return ModelResponse(
            model_id=model_id,
            raw_text=raw,
            code=extract_code(raw, function_name=task.function_name),
            input_tokens=in_tok,
            output_tokens=out_tok,
            cost_usd=price(model_id, in_tok, out_tok),
            latency_sec=time.monotonic() - start,
        )


class LocalLoraClient:
    """Fine-tuned LoRA on the local device. Strong-model calls stay unwired."""

    def __init__(self, adapter_dir: str | Path | None = None):
        self.kind = "local"
        self.adapter_dir = Path(adapter_dir) if adapter_dir else DEFAULT_ADAPTER_DIR
        if not (self.adapter_dir / "adapter_config.json").is_file():
            raise FileNotFoundError(f"LoRA adapter not found: {self.adapter_dir}")
        self._lock = threading.Lock()
        self._model = None
        self._tokenizer = None
        self.device = None
        self.calls: dict[str, int] = {FINETUNED_MODEL_ID: 0, STRONG_MODEL_ID: 0}

    def load(self) -> None:
        if self._model is not None:
            return
        from training.device import pick_device
        from training.load import load_finetuned

        device = pick_device()
        model, tokenizer = load_finetuned(str(self.adapter_dir), device)
        self._model = model
        self._tokenizer = tokenizer
        self.device = device

    def generate(self, model_id: str, prompt: str, task: CodingTask) -> ModelResponse:
        start = time.monotonic()
        self.calls[model_id] = self.calls.get(model_id, 0) + 1
        if model_id != FINETUNED_MODEL_ID:
            raw = "# strong model API is not wired yet"
            code = extract_code(_wrong_code(task), function_name=task.function_name)
            in_tok = estimate_tokens(prompt)
            out_tok = estimate_tokens(raw)
            return ModelResponse(
                model_id=model_id,
                raw_text=raw,
                code=code,
                input_tokens=in_tok,
                output_tokens=out_tok,
                cost_usd=0.0,
                latency_sec=time.monotonic() - start,
            )

        from training.generate import complete

        with self._lock:
            self.load()
            completion = complete(
                self._model,
                self._tokenizer,
                prompt,
                self.device,
                MAX_OUTPUT_TOKENS,
                function_name=task.function_name,
            )
        return ModelResponse(
            model_id=model_id,
            raw_text=completion.raw_text,
            code=completion.code,
            input_tokens=completion.input_tokens,
            output_tokens=completion.output_tokens,
            cost_usd=0.0,
            latency_sec=time.monotonic() - start,
        )


def make_client(
    kind: str | None = None,
    *,
    adapter: str | Path | None = None,
    mock_scenario: str = "pass",
) -> MockModelClient | LocalLoraClient:
    resolved = (kind or os.environ.get("AGENT_CLIENT") or "local").strip().lower()
    if resolved not in CLIENT_KINDS:
        raise ValueError(f"client must be one of {CLIENT_KINDS}")
    if resolved == "mock":
        return MockModelClient(mock_scenario)
    return LocalLoraClient(adapter or os.environ.get("LORA_ADAPTER"))
