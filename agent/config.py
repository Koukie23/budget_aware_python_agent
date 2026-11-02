from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv() -> None:
    path = ROOT / ".env"
    if not path.is_file():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key and key not in os.environ:
            os.environ[key] = value.strip().strip("'").strip('"')


_load_dotenv()

FINETUNED_MODEL_ID = "codegen-350m-lora-v2"
STRONG_MODEL_ID = os.environ.get("DEEPSEEK_MODEL", "deepseek-flash")
DEFAULT_ADAPTER_DIR = ROOT / "models" / "codegen350m_lora_v2" / "best"
DEEPSEEK_BASE_URL = os.environ.get("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# USD per 1K tokens. Fine-tuned model is local. Strong prices use DeepSeek Flash peak / cache-miss.
PRICE_PER_1K = {
    FINETUNED_MODEL_ID: {"input": 0.0, "output": 0.0},
    STRONG_MODEL_ID: {"input": 0.0003, "output": 0.0012},
}

MAX_OUTPUT_TOKENS = 256
STRONG_MAX_OUTPUT_TOKENS = 512
MAX_MODEL_CALLS = 3
DEFAULT_BUDGET_USD = 0.05
TEST_TIMEOUT_SEC = 5
MEMORY_LIMIT_MB = 256
