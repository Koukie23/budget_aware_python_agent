from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

FINETUNED_MODEL_ID = "codegen-350m-lora-v2"
STRONG_MODEL_ID = "mock-strong"
DEFAULT_ADAPTER_DIR = ROOT / "models" / "codegen350m_lora_v2" / "best"

# USD per 1K tokens. The fine-tuned model runs locally and has no API cost.
PRICE_PER_1K = {
    FINETUNED_MODEL_ID: {"input": 0.0, "output": 0.0},
    STRONG_MODEL_ID: {"input": 0.0025, "output": 0.01},
}

MAX_OUTPUT_TOKENS = 256
MAX_MODEL_CALLS = 3
DEFAULT_BUDGET_USD = 0.05
TEST_TIMEOUT_SEC = 5
MEMORY_LIMIT_MB = 256
