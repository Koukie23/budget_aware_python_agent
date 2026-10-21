from __future__ import annotations

from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

from training.config import BASE_MODEL_ID, MAX_LENGTH


def load_tokenizer(model_id: str = BASE_MODEL_ID):
    tokenizer = AutoTokenizer.from_pretrained(model_id)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    tokenizer.model_max_length = MAX_LENGTH
    tokenizer.padding_side = "left"
    return tokenizer


def load_base_model(model_id: str, device: torch.device):
    dtype = torch.float32 if device.type == "cpu" else torch.float16
    if device.type == "mps":
        dtype = torch.float32
    model = AutoModelForCausalLM.from_pretrained(model_id, dtype=dtype)
    model.to(device)
    model.eval()
    return model


def load_finetuned(adapter_dir: str, device: torch.device):
    tokenizer = load_tokenizer()
    model = load_base_model(BASE_MODEL_ID, device)
    model = PeftModel.from_pretrained(model, adapter_dir)
    model.eval()
    return model, tokenizer
