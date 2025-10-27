from __future__ import annotations

import os
from dataclasses import dataclass

from typing import Optional, List, Dict, Any
import hashlib
import json
import logging

from pydantic import BaseModel
from models import DialogueMessage, DialogueScript


@dataclass
class OpenAISettings:
    api_key: str
    base_url: Optional[str] = None  # allow overrides if needed


class OpenAIClient:
    def __init__(self, settings: Optional[OpenAISettings] = None) -> None:
        self._log = logging.getLogger("openai_client")
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
        self._log.debug("initialized OpenAIClient; cache=%s base_url=%s", bool(self._cache), self.settings.base_url)

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
                self._log.info("container detected; redis cache disabled")
                return None
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            import redis  # type: ignore

            client = redis.from_url(redis_url, decode_responses=True)
            # Smoke test ping (non-fatal)
            try:
                client.ping()
                self._log.info("redis cache available at %s", redis_url)
            except Exception:
                self._log.warning("redis ping failed; disabling cache", exc_info=False)
                return None
            return client
        except Exception:
            self._log.info("redis import/init failed; disabling cache", exc_info=False)
            return None

    def _cache_key(self, *, model: str, topic: str, script_prompt: str, characters: List[Dict[str, Any]] | None) -> str:
        payload = {
            "model": model,
            "topic": topic,
            "script_prompt": script_prompt,
            "characters": characters or [],
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
    ) -> List[Dict[str, str]]:
        """Generate a short dialogue script as structured outputs (list of messages)."""
        self._ensure_client()

        # Attempt cache fetch (local dev only)
        cache_hit: Optional[str] = None
        cache_key = None
        if self._cache is not None:
            cache_key = self._cache_key(model=model, topic=topic, script_prompt=script_prompt, characters=characters)
            try:
                cache_hit = self._cache.get(cache_key)
            except Exception:
                cache_hit = None
        if cache_hit:
            try:
                data = json.loads(cache_hit)
                if isinstance(data, list):
                    self._log.info("cache hit for model=%s topic=%s", model, topic)
                    return data
            except Exception:
                pass
        else:
            if self._cache is not None:
                self._log.info("cache miss for model=%s topic=%s", model, topic)

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
        self._log.info("calling OpenAI Responses.parse model=%s", model)
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
            self._log.warning("no structured messages returned; parsed=%s", type(parsed).__name__ if parsed else None)
            return []
        messages = [{"character": m.character, "text": m.text} for m in parsed.messages]
        # Cache set (local dev only)
        if self._cache is not None and cache_key is not None:
            try:
                self._cache.setex(cache_key, int(os.getenv("OPENAI_CACHE_TTL", "3600")), json.dumps(messages))
                self._log.debug("cached response key=%s ttl=%s", cache_key, os.getenv("OPENAI_CACHE_TTL", "3600"))
            except Exception:
                self._log.warning("failed to cache response", exc_info=False)
        return messages