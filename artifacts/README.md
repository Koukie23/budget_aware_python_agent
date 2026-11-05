# Training artifacts (no weights)

These files are the original logs and per-task pass@1 results. The LoRA adapter itself is **not** here; download it from the GitHub Release `lora-v2`.

| File | What it is |
| --- | --- |
| `codegen350m_lora_v2/train_log.json` | Epoch train/val loss and val pass@1; best is epoch 1 |
| `codegen350m_lora_v2/adapter_config.json` | LoRA config (base id, r, alpha, target modules) |
| `e1_base/{validation,test}.json` | Untuned CodeGen-350M, one row per task |
| `e2_lora/{validation,test}.json` | First LoRA (deprecated) |
| `e2_lora_v2/{validation,test}.json` | Current LoRA used by the agent |
