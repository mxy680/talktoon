#!/usr/bin/env python3
import os
import asyncio
from clients.db import DB
from utils.runtime import load_config, get_account_settings, init_openai, ensure_topic_and_account

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


async def main_async() -> None:
    topic = os.getenv("TOPIC", "").strip()
    cfg = load_config("config/config.yaml")
    acc, models = get_account_settings(topic, cfg)
    script_prompt = acc.get("script_prompt", "")
    characters = acc.get("characters", [])

    ai = init_openai()

    db = DB()
    await db.connect()
    await ensure_topic_and_account(db, topic)
    
    await db.disconnect()

    # Generate script using OpenAI with provided parameters
    model_name = models.get("script_model")
    if script_prompt:
        script = ai.generate_script(
            topic=topic,
            model=model_name,
            script_prompt=script_prompt,
            characters=characters,
        )
        # For now, print to stdout; later we can persist to DB/file
        print(script)


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
