#!/usr/bin/env python3
import os
import asyncio
import logging
from clients.db import DB
from utils.runtime import load_config, get_account_settings, init_openai, ensure_topic_and_account

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


async def main_async() -> None:
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    log = logging.getLogger("runner")
    topic = os.getenv("TOPIC", "").strip()
    log.info("topic=%s", topic)
    cfg = load_config("config/config.yaml")
    acc, models = get_account_settings(topic, cfg)
    script_prompt = acc.get("script_prompt", "")
    characters = acc.get("characters", [])
    log.info("loaded account settings: chars=%d has_prompt=%s", len(characters), bool(script_prompt))

    ai = init_openai()
    log.info("openai client initialized")

    db = DB()
    await db.connect()
    log.info("db connected")
    await ensure_topic_and_account(db, topic)
    log.info("ensured topic and account for topic=%s", topic)
    await db.disconnect()
    log.info("db disconnected")

    # Generate script using OpenAI with provided parameters
    model_name = models.get("script_model")
    log.info("generating script with model=%s", model_name)
    if script_prompt:
        script = ai.generate_script(
            topic=topic,
            model=model_name,
            script_prompt=script_prompt,
            characters=characters,
        )
        # Log dialogue lines; later we can persist to DB/file
        if isinstance(script, list):
            log.info("generated %d dialogue lines", len(script))
            for m in script:
                try:
                    log.info("%s: %s", m.get("character"), m.get("text"))
                except Exception:
                    log.info("%s", m)
        else:
            log.info("generated script:\n%s", script)


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
