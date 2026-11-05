#!/usr/bin/env python3
"""Download the released LoRA adapter. Does not include the base model."""

from __future__ import annotations

import sys
import zipfile
from pathlib import Path
from urllib.request import urlretrieve

ROOT = Path(__file__).resolve().parents[1]
URL = "https://github.com/Koukie23/budget_aware_python_agent/releases/download/lora-v2/codegen350m_lora_v2_best.zip"
DEST = ROOT / "models" / "codegen350m_lora_v2" / "best"


def main() -> int:
    DEST.mkdir(parents=True, exist_ok=True)
    archive = ROOT / "models" / "codegen350m_lora_v2_best.zip"
    print(f"downloading {URL}")
    urlretrieve(URL, archive)
    with zipfile.ZipFile(archive) as zf:
        for info in zf.infolist():
            name = Path(info.filename).name
            if not name or info.is_dir():
                continue
            target = DEST / name
            target.write_bytes(zf.read(info))
            print(f"wrote {target.relative_to(ROOT)}")
    archive.unlink(missing_ok=True)
    if not (DEST / "adapter_config.json").is_file():
        print("download incomplete", file=sys.stderr)
        return 1
    print(f"adapter ready at {DEST.relative_to(ROOT)}")
    print("base model is still downloaded by Hugging Face: Salesforce/codegen-350M-mono")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
