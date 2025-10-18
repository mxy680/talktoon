#!/usr/bin/env python3
import os
import sys
from datetime import datetime
from pathlib import Path

from clients.config import load_config


def ensure_dirs(base: Path) -> None:
    (base / "out" / "renders").mkdir(parents=True, exist_ok=True)
    (base / "out" / "intermediates").mkdir(parents=True, exist_ok=True)


def main() -> None:
    ts = datetime.utcnow().isoformat() + "Z"

    # Verify environment
    api_key_present = bool(os.getenv("OPENAI_API_KEY"))

    # Load config
    try:
        cfg = load_config("config/config.yaml")
    except Exception as e:
        print(f"error=failed_to_load_config msg={e}", file=sys.stderr)
        return

    # Ensure output directories
    ensure_dirs(Path("data"))

    # Minimal output (placeholder for future orchestration)
    print("Hello World")
    print(
        " | ".join(
            [
                f"timestamp={ts}",
                f"api_key_set={api_key_present}",
                f"script_model={cfg.models.script_model}",
                f"tts_model={cfg.models.tts_model}",
                f"tts_voice={cfg.models.tts_voice}",
                f"video={cfg.video.width}x{cfg.video.height}@{cfg.video.fps}",
                f"caption_mode={cfg.captioning.mode}",
                f"caption_api={cfg.captioning.api_base}",
            ]
        )
    )


if __name__ == "__main__":
    main()
