import os
import time
import pathlib
import requests

AUDIO_DIR = pathlib.Path(os.getenv("AUDIO_DIR", "/app/data/audio"))
AUDIO_DIR.mkdir(parents=True, exist_ok=True)
TTS_BASE_URL = os.getenv("TTS_BASE_URL", "http://tts:7861")


def tts_task(text: str, speaker: str = "peter"):
    """Background task: call TTS service and persist WAV.
    Returns a dict with path (or URL) to the generated audio.
    """
    url = f"{TTS_BASE_URL.rstrip('/')}/infer"
    files = {
        "gen_text": (None, text),
        "speaker": (None, speaker),
    }
    r = requests.post(url, files=files, timeout=300)
    r.raise_for_status()

    ts = int(time.time())
    safe_speaker = "".join(c for c in speaker if c.isalnum() or c in ("-","_")) or "speaker"
    out_path = AUDIO_DIR / f"{ts}-{safe_speaker}.wav"
    with open(out_path, "wb") as f:
        f.write(r.content)
    return {"audio_path": str(out_path)}
