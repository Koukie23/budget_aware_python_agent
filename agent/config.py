from __future__ import annotations

# Placeholders until the fine-tuned model (T6) and the strong API model (T7) are wired.
FINETUNED_MODEL_ID = "mock-finetuned"
STRONG_MODEL_ID = "mock-strong"

# USD per 1K tokens. The fine-tuned model runs locally and has no API cost.
PRICE_PER_1K = {
    FINETUNED_MODEL_ID: {"input": 0.0, "output": 0.0},
    STRONG_MODEL_ID: {"input": 0.0025, "output": 0.01},
}

MAX_OUTPUT_TOKENS = 512
MAX_MODEL_CALLS = 3
DEFAULT_BUDGET_USD = 0.05
TEST_TIMEOUT_SEC = 5
MEMORY_LIMIT_MB = 256
