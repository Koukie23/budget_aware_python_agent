from __future__ import annotations

from dataclasses import dataclass

import torch

from agent.extract import extract_code


@dataclass
class Completion:
    raw_text: str
    code: str
    input_tokens: int
    output_tokens: int


@torch.inference_mode()
def complete(
    model,
    tokenizer,
    prompt: str,
    device: torch.device,
    max_new_tokens: int,
    function_name: str | None = None,
) -> Completion:
    tokenizer.padding_side = "left"
    encoded = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=tokenizer.model_max_length)
    encoded = {k: v.to(device) for k, v in encoded.items()}
    input_len = encoded["input_ids"].shape[1]
    out = model.generate(
        **encoded,
        max_new_tokens=max_new_tokens,
        do_sample=False,
        pad_token_id=tokenizer.pad_token_id,
        eos_token_id=tokenizer.eos_token_id,
    )
    new_tokens = out[0, input_len:]
    raw_text = tokenizer.decode(new_tokens, skip_special_tokens=True)
    return Completion(
        raw_text=raw_text,
        code=extract_code(raw_text, function_name=function_name),
        input_tokens=input_len,
        output_tokens=int(new_tokens.shape[0]),
    )


@torch.inference_mode()
def generate_code(
    model,
    tokenizer,
    prompt: str,
    device: torch.device,
    max_new_tokens: int,
    function_name: str | None = None,
) -> str:
    return complete(model, tokenizer, prompt, device, max_new_tokens, function_name).code
