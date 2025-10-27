from __future__ import annotations

import os
from dataclasses import dataclass

from typing import Optional, List, Dict, Any

from pydantic import BaseModel
from models import DialogueMessage, DialogueScript


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
            settings = OpenAISettings(api_key=api_key, base_url=os.getenv("OPENAI_BASE_URL"))
        self.settings = settings
        # Lazily initialize the SDK client
        self._client = None

    def _ensure_client(self):
        if self._client is None:
            try:
                from openai import OpenAI  # type: ignore
            except Exception as e:
                raise RuntimeError(f"Failed to import OpenAI SDK: {e}")
            if self.settings.base_url:
                self._client = OpenAI(api_key=self.settings.api_key, base_url=self.settings.base_url)
            else:
                self._client = OpenAI(api_key=self.settings.api_key)

    def generate_script(
        self,
        *,
        topic: str,
        model: str,
        script_prompt: str,
        characters: List[Dict[str, Any]] | None = None,
    ) -> List[Dict[str, str]]:
        """Generate a short dialogue script as structured outputs (list of messages)."""
        self._ensure_client()

        char_specs = []
        for c in (characters or []):
            name = (c.get("name") or c.get("id") or "Character").strip()
            persona = (c.get("persona") or "").strip()
            char_specs.append(f"- {name}: {persona}")
        char_block = "\n".join(char_specs) or "- A: host\n- B: foil"

        system = (
            "You write concise, high-energy scripts for short social videos. "
            "Return ONLY structured outputs."
        )
        user = (
            f"Topic: {topic}\n\n"
            f"Direction: {script_prompt}\n\n"
            f"Characters:\n{char_block}\n\n"
            "Output should be a sequence of messages in a two-person dialogue."
        )

        # Use Responses API with Pydantic parsing
        response = self._client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            text_format=DialogueScript,
        )
        parsed = response.output_parsed  # type: ignore
        if not parsed or not getattr(parsed, "messages", None):
            return []
        return [{"character": m.character, "text": m.text} for m in parsed.messages]