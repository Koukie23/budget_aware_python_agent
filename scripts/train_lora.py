#!/usr/bin/env python3
"""Fine-tune CodeGen-350M with LoRA. Loss only on target_code tokens."""

from __future__ import annotations

import json
import math
import random
import sys
import time
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from peft import LoraConfig, TaskType, get_peft_model  # noqa: E402
from torch.utils.data import DataLoader  # noqa: E402
from transformers import get_linear_schedule_with_warmup  # noqa: E402
import torch  # noqa: E402

from training.config import (  # noqa: E402
    BASE_MODEL_ID,
    BATCH_SIZE,
    EPOCHS,
    GRAD_ACCUM,
    LORA_ALPHA,
    LORA_DROPOUT,
    LORA_R,
    LORA_TARGET,
    LR,
    MAX_GRAD_NORM,
    MAX_LENGTH,
    MAX_NEW_TOKENS,
    OUTPUT,
    PROCESSED,
    SEED,
    WARMUP_RATIO,
    WEIGHT_DECAY,
)
from training.data import CausalCodeDataset, collate, load_jsonl  # noqa: E402
from training.device import pick_device  # noqa: E402
from training.evaluate import evaluate_records, write_eval  # noqa: E402
from training.load import load_base_model, load_tokenizer  # noqa: E402


def set_seed(seed: int) -> None:
    random.seed(seed)
    torch.manual_seed(seed)


def train_loss(model, batch, device) -> torch.Tensor:
    batch = {k: v.to(device) for k, v in batch.items()}
    return model(**batch).loss


def main() -> int:
    set_seed(SEED)
    device = pick_device()
    out_dir = OUTPUT / "codegen350m_lora_v2"
    out_dir.mkdir(parents=True, exist_ok=True)
    print(f"device={device} model={BASE_MODEL_ID}")

    tokenizer = load_tokenizer()
    train_recs = load_jsonl(PROCESSED / "train.jsonl")
    val_recs = load_jsonl(PROCESSED / "validation.jsonl")
    train_ds = CausalCodeDataset(train_recs, tokenizer, MAX_LENGTH)
    val_ds = CausalCodeDataset(val_recs, tokenizer, MAX_LENGTH)
    print(f"train={len(train_ds)} truncated={train_ds.skipped_truncated} val={len(val_ds)}")

    loader = DataLoader(
        train_ds,
        batch_size=BATCH_SIZE,
        shuffle=True,
        collate_fn=partial(collate, pad_id=tokenizer.pad_token_id),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=BATCH_SIZE,
        shuffle=False,
        collate_fn=partial(collate, pad_id=tokenizer.pad_token_id),
    )

    model = load_base_model(BASE_MODEL_ID, device)
    model.train()
    model = get_peft_model(
        model,
        LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=LORA_R,
            lora_alpha=LORA_ALPHA,
            lora_dropout=LORA_DROPOUT,
            target_modules=list(LORA_TARGET),
            bias="none",
        ),
    )
    model.print_trainable_parameters()

    optimizer = torch.optim.AdamW(
        (p for p in model.parameters() if p.requires_grad),
        lr=LR,
        weight_decay=WEIGHT_DECAY,
    )
    steps_per_epoch = math.ceil(len(loader) / GRAD_ACCUM)
    total_steps = steps_per_epoch * EPOCHS
    warmup = int(total_steps * WARMUP_RATIO)
    scheduler = get_linear_schedule_with_warmup(optimizer, warmup, total_steps)

    history = []
    best_pass = -1.0
    start = time.monotonic()
    global_step = 0
    for epoch in range(1, EPOCHS + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        running = 0.0
        seen = 0
        for i, batch in enumerate(loader, start=1):
            loss = train_loss(model, batch, device) / GRAD_ACCUM
            loss.backward()
            running += loss.item() * GRAD_ACCUM
            seen += 1
            if i % GRAD_ACCUM == 0 or i == len(loader):
                torch.nn.utils.clip_grad_norm_(model.parameters(), MAX_GRAD_NORM)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad(set_to_none=True)
                global_step += 1
        train_loss_epoch = running / max(seen, 1)

        model.eval()
        val_running = 0.0
        with torch.no_grad():
            for batch in val_loader:
                val_running += train_loss(model, batch, device).item()
        val_loss = val_running / max(len(val_loader), 1)
        eval_payload = evaluate_records(val_recs, model, tokenizer, device, MAX_NEW_TOKENS)
        pass1 = eval_payload["pass_at_1"]
        row = {
            "epoch": epoch,
            "train_loss": train_loss_epoch,
            "val_loss": val_loss,
            "val_pass_at_1": pass1,
            "lr": scheduler.get_last_lr()[0],
            "seconds": round(time.monotonic() - start, 1),
        }
        history.append(row)
        print(row)
        ckpt = out_dir / f"epoch_{epoch}"
        model.save_pretrained(ckpt)
        tokenizer.save_pretrained(ckpt)
        if pass1 >= best_pass:
            best_pass = pass1
            best = out_dir / "best"
            model.save_pretrained(best)
            tokenizer.save_pretrained(best)
            write_eval(best / "val_eval.json", eval_payload)

    meta = {
        "base_model": BASE_MODEL_ID,
        "device": str(device),
        "seed": SEED,
        "epochs": EPOCHS,
        "lr": LR,
        "lora": {"r" : LORA_R, "alpha": LORA_ALPHA, "target": list(LORA_TARGET)},
        "history": history,
        "best_val_pass_at_1": best_pass,
    }
    (out_dir / "train_log.json").write_text(json.dumps(meta, indent=2) + "\n")
    print(f"done best_val_pass@1={best_pass:.3f} log={ (out_dir / 'train_log.json').relative_to(ROOT) }")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
