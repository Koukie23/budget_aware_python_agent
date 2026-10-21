from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "models"

BASE_MODEL_ID = "Salesforce/codegen-350M-mono"
SEED = 42
MAX_LENGTH = 2048
MAX_NEW_TOKENS = 256
BATCH_SIZE = 1
GRAD_ACCUM = 8
LR = 5e-5
EPOCHS = 2
WARMUP_RATIO = 0.05
WEIGHT_DECAY = 0.01
MAX_GRAD_NORM = 1.0
LORA_R = 16
LORA_ALPHA = 32
LORA_DROPOUT = 0.05
LORA_TARGET = ("qkv_proj", "out_proj")
DECODE = {"do_sample": False}
