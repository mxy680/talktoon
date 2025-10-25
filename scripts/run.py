#!/usr/bin/env python3
import os
import sys
import yaml
import asyncio
from clients.db import DB
from clients.openai_client import OpenAIClient

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass

def load_config() -> dict:
    with open("config/config.yaml", "r") as f:
        return yaml.safe_load(f) or {}


async def main_async() -> None:
    topic = os.getenv("TOPIC", "").strip()
    cfg = load_config()
    accounts = cfg.get("accounts", {})
    acc = accounts.get(topic.lower())
    script_prompt = acc.get("script_prompt", "")
    characters = acc.get("characters", [])
    models = cfg.get("models", {})

    ai = OpenAIClient()

    db = DB()
    await db.connect()
    await db.ensure_topic(topic)
    await db.ensure_account_for_topic(topic)
    
    await db.disconnect()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
