from __future__ import annotations

import os
from dataclasses import dataclass

from typing import Optional


@dataclass
class OpenAISettings:
    api_key: str
    base_url: Optional[str] = None  # allow overrides if needed


class OpenAIClient:
    def __init__(self, settings: Optional[OpenAISettings] = None) -> None:
        if settings is None:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                raise RuntimeError("OPENAI_API_KEY is not set in environment")
            settings = OpenAISettings(api_key=api_key)
        self.settings = settings
        # Defer importing the SDK until we actually call it (added later)
        # This keeps the scaffold runnable without network calls.

    # Placeholders for future implementations
    def generate_script(self, topic: str, model: str) -> str:
        # TODO: implement chat completion call
        raise NotImplementedError("generate_script not yet implemented")

    def tts(self, text: str, model: str, voice: str, out_path: str) -> None:
        # TODO: implement TTS call writing WAV/MP3 to out_path
        raise NotImplementedError("tts not yet implemented")
