from __future__ import annotations

import json
from pathlib import Path

import torch
from torch.utils.data import Dataset


def load_jsonl(path: Path) -> list[dict]:
    records = []
    with path.open() as f:
        for line in f:
            if line.strip():
                records.append(json.loads(line))
    return records


class CausalCodeDataset(Dataset):
    def __init__(self, records: list[dict], tokenizer, max_length: int):
        self.examples = []
        skipped = 0
        for rec in records:
            prompt = rec["prompt"]
            # Match the prompt instruction: one fenced Python block, then EOS.
            fenced = f"```python\n{rec['target_code'].rstrip()}\n```"
            target = fenced + tokenizer.eos_token
            prompt_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
            full = tokenizer(prompt + "\n" + target, add_special_tokens=False)["input_ids"]
            if len(full) > max_length:
                skipped += 1
                full = full[:max_length]
            labels = list(full)
            cutoff = min(len(prompt_ids) + 1, len(labels))  # +1 for the newline
            for i in range(cutoff):
                labels[i] = -100
            self.examples.append({"input_ids": full, "labels": labels})
        self.skipped_truncated = skipped

    def __len__(self) -> int:
        return len(self.examples)

    def __getitem__(self, i: int) -> dict:
        return self.examples[i]


def collate(batch: list[dict], pad_id: int) -> dict[str, torch.Tensor]:
    longest = max(len(x["input_ids"]) for x in batch)
    input_ids, labels, attn = [], [], []
    for x in batch:
        pad = longest - len(x["input_ids"])
        input_ids.append(x["input_ids"] + [pad_id] * pad)
        labels.append(x["labels"] + [-100] * pad)
        attn.append([1] * len(x["input_ids"]) + [0] * pad)
    return {
        "input_ids": torch.tensor(input_ids, dtype=torch.long),
        "labels": torch.tensor(labels, dtype=torch.long),
        "attention_mask": torch.tensor(attn, dtype=torch.long),
    }
