#!/usr/bin/env python3
"""E1: greedy pass@1 of the untuned base model on a processed split."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from training.config import BASE_MODEL_ID, MAX_NEW_TOKENS, OUTPUT, PROCESSED, SEED  # noqa: E402
from training.data import load_jsonl  # noqa: E402
from training.device import pick_device  # noqa: E402
from training.evaluate import evaluate_records, write_eval  # noqa: E402
from training.load import load_base_model, load_finetuned, load_tokenizer  # noqa: E402

import torch  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--split", choices=("validation", "test"), default="validation")
    p.add_argument("--limit", type=int, default=None)
    p.add_argument("--executor", choices=("docker", "subprocess"), default="docker")
    p.add_argument("--adapter", type=Path, default=None, help="LoRA adapter directory for E2")
    p.add_argument("--tag", default=None, help="Output folder under models/, default e1_base or e2_lora")
    args = p.parse_args()

    torch.manual_seed(SEED)
    device = pick_device()
    print(f"device={device} model={BASE_MODEL_ID} split={args.split} adapter={args.adapter}")
    if args.adapter:
        model, tokenizer = load_finetuned(str(args.adapter), device)
        tag = args.tag or "e2_lora"
    else:
        tokenizer = load_tokenizer()
        model = load_base_model(BASE_MODEL_ID, device)
        tag = args.tag or "e1_base"
    records = load_jsonl(PROCESSED / f"{args.split}.jsonl")
    payload = evaluate_records(
        records, model, tokenizer, device, MAX_NEW_TOKENS, executor=args.executor, limit=args.limit
    )
    out = OUTPUT / tag / f"{args.split}.json"
    write_eval(out, payload)
    print(f"pass@1 {payload['n_pass']}/{payload['n']} = {payload['pass_at_1']:.3f}")
    print(f"extract_fail={payload['extract_fail']} wrote {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
