#!/usr/bin/env python3
import os
import asyncio
from clients.db import DB
from utils.runtime import load_config, get_account_settings, init_openai
from clients.video_editor import VideoEditor

try:
    from dotenv import load_dotenv  # type: ignore
    load_dotenv()
except Exception:
    pass


async def main_async() -> None:
    topic = os.getenv("TOPIC", "").strip()
    dev_mode = os.getenv("DEV", "").lower() in {"1", "true", "yes"}
    cfg = load_config("config/config.yaml")
    acc, models = get_account_settings(topic, cfg)
    script_prompt = acc.get("script_prompt", "")
    characters = acc.get("characters", [])

    ai = init_openai()

    db = DB()
    await db.connect()
    # Ensure topic & account, then count unused subtopics for the account
    await db.ensure_topic(topic)
    account = await db.ensure_account_for_topic(topic)

    # Determine model early (used for subtopic generation as well)
    model_name = models.get("script_model")

    try:
        unused_count = await db.count_unused_subtopics(account.id)
    except Exception:
        unused_count = 0
    if unused_count == 0:
        # Generate more subtopics avoiding duplicates
        try:
            from clients.openai_client import OpenAIClient  # local import to avoid cycles
            used_titles = await db.list_used_subtopic_titles_for_account(account.id)
            new_titles = ai.generate_subtopics(
                topic=topic,
                model=model_name,
                existing_titles=used_titles,
                count=10,
            )
            if new_titles:
                await db.create_subtopics_for_account(account.id, new_titles)
        except Exception as e:
            print(f"Failed to generate subtopics: {e}")
        # Recount (best effort)
        try:
            unused_count = await db.count_unused_subtopics(account.id)
        except Exception:
            unused_count = 0
    # Select oldest unused subtopic (if any) for generation context
    chosen_subtopic_title = None
    chosen_subtopic_id = None
    if unused_count > 0:
        try:
            sub = await db.get_oldest_unused_subtopic(account.id)
            if sub:
                chosen_subtopic_title = getattr(sub, "title", None)
                chosen_subtopic_id = getattr(sub, "id", None)
        except Exception:
            chosen_subtopic_title = None
    print(f"unused_subtopics={unused_count} chosen_subtopic={chosen_subtopic_title}")

    # Generate script using OpenAI with provided parameters
    if script_prompt:
        script = ai.generate_script(
            topic=topic,
            model=model_name,
            script_prompt=script_prompt,
            characters=characters,
            subtopic=chosen_subtopic_title,
        )
        # Minimal stdout output; later we can persist to DB/file
        if isinstance(script, list):
            for m in script:
                try:
                    print(f"{m.get('character')}: {m.get('text')}")
                except Exception:
                    print(m)
        else:
            print(script)

        # After using a subtopic in non-dev, mark it used and create a Video linked to it
        if chosen_subtopic_id and not dev_mode:
            try:
                title_for_video = chosen_subtopic_title or (topic or "Untitled")
                await db.consume_subtopic_create_video(
                    account_id=account.id,
                    subtopic_id=chosen_subtopic_id,
                    title=title_for_video,
                )
            except Exception as e:
                print(f"Failed to create video for subtopic: {e}")

        # Start video editing session
        try:
            editor = VideoEditor()
            session = editor.begin(topic=topic, subtopic=chosen_subtopic_title, script=script if isinstance(script, list) else [])
            print(f"video_edit_session_ready topic={session.get('topic')} subtopic={session.get('subtopic')} lines={session.get('line_count')}")
        except Exception as e:
            print(f"Failed to start video editing session: {e}")

    await db.disconnect()


def main() -> None:
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
