from __future__ import annotations

import os
from dataclasses import dataclass

from typing import Optional, List, Dict, Any
import hashlib
import json

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
        # Optional Redis cache (local dev only)
        self._cache = self._maybe_init_cache()

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

    @staticmethod
    def _running_in_container() -> bool:
        # Only rely on real container heuristics; ignore IN_CONTAINER from .env during local runs
        # Docker typically sets /.dockerenv; some setups export DOCKER_CONTAINER=true
        if os.path.exists("/.dockerenv"):
            return True
        if os.getenv("DOCKER_CONTAINER", "").lower() in {"1", "true", "yes"}:
            return True
        return False

    def _maybe_init_cache(self):
        """Initialize Redis cache for local dev only; return client or None."""
        try:
            if self._running_in_container():
                return None
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            import redis  # type: ignore

            client = redis.from_url(redis_url, decode_responses=True)
            # Smoke test ping (non-fatal)
            try:
                client.ping()
            except Exception:
                return None
            return client
        except Exception:
            return None

    def _cache_key(self, *, model: str, topic: str, script_prompt: str, characters: List[Dict[str, Any]] | None, subtopic: str | None = None) -> str:
        payload = {
            "model": model,
            "topic": topic,
            "script_prompt": script_prompt,
            "characters": characters or [],
            "subtopic": subtopic or "",
        }
        digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()
        return f"openai:dialogue:{digest}"

    def generate_script(
        self,
        *,
        topic: str,
        model: str,
        script_prompt: str,
        characters: List[Dict[str, Any]] | None = None,
        subtopic: str | None = None,
    ) -> List[Dict[str, str]]:
        """Generate a short dialogue script as structured outputs (list of messages)."""
        self._ensure_client()

        # Attempt cache fetch (local dev only)
        cache_hit: Optional[str] = None
        cache_key = None
        if self._cache is not None:
            cache_key = self._cache_key(model=model, topic=topic, script_prompt=script_prompt, characters=characters, subtopic=subtopic)
            try:
                cache_hit = self._cache.get(cache_key)
            except Exception:
                cache_hit = None
        if cache_hit:
            try:
                data = json.loads(cache_hit)
                if isinstance(data, list):
                    return data
            except Exception:
                pass

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
        subtopic_line = f"Subtopic: {subtopic}\n\n" if subtopic else ""
        user = (
            f"Topic: {topic}\n\n"
            + subtopic_line +
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
        messages = [{"character": m.character, "text": m.text} for m in parsed.messages]
        # Cache set (local dev only)
        if self._cache is not None and cache_key is not None:
            try:
                self._cache.setex(cache_key, int(os.getenv("OPENAI_CACHE_TTL", "3600")), json.dumps(messages))
            except Exception:
                pass
        return messages

    class SubtopicList(BaseModel):
        titles: List[str]

    def generate_subtopics(
        self,
        *,
        topic: str,
        model: str,
        existing_titles: List[str] | None = None,
        count: int = 10,
    ) -> List[str]:
        """Generate up to `count` new subtopic titles avoiding duplicates in `existing_titles`."""
        self._ensure_client()
        existing_titles = existing_titles or []
        system = (
            "You propose concise, distinct subtopic titles suitable for short-form educational videos."
        )
        user = (
            f"Parent Topic: {topic}\n\n"
            f"Already used subtopics (avoid duplicates, case-insensitive):\n"
            + "\n".join(f"- {t}" for t in existing_titles)
            + "\n\n"
            f"Generate {count} new unique subtopic titles."
        )
        response = self._client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            text_format=OpenAIClient.SubtopicList,
        )
        parsed = response.output_parsed  # type: ignore
        if not parsed or not getattr(parsed, "titles", None):
            return []
        # Filter out duplicates against provided list (case-insensitive)
        existing_lower = {t.lower().strip() for t in existing_titles}
        out: List[str] = []
        for t in parsed.titles:
            k = t.lower().strip()
            if k and k not in existing_lower:
                existing_lower.add(k)
                out.append(t.strip())
        return out[:count]