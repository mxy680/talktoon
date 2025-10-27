import os
import yaml
from typing import Any, Dict, List, Tuple

from clients.db import DB
from clients.openai_client import OpenAIClient


def load_config(path: str = "config/config.yaml") -> Dict[str, Any]:
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def get_account_settings(topic: str, cfg: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    accounts = cfg.get("accounts", {})
    acc = accounts.get(topic.lower(), {})
    models = cfg.get("models", {})
    return acc, models


def init_openai() -> OpenAIClient:
    return OpenAIClient()


async def ensure_topic_and_account(db: DB, topic: str) -> None:
    await db.ensure_topic(topic)
    await db.ensure_account_for_topic(topic)
