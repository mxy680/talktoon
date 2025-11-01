import os
import time
import pathlib
import requests
import uuid
from typing import Optional

try:
    import boto3  # type: ignore
    from botocore.config import Config as BotoConfig  # type: ignore
except Exception:
    boto3 = None
    BotoConfig = None

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
    result = {"audio_path": str(out_path)}

    # Optional S3 upload
    s3_endpoint = os.getenv("S3_ENDPOINT")
    bucket = os.getenv("S3_BUCKET")
    if s3_endpoint and bucket and boto3 is not None:
        key = f"audio/{uuid.uuid4()}-{os.path.basename(out_path)}"
        cfg = None
        if os.getenv("S3_FORCE_PATH_STYLE", "false").lower() == "true" and BotoConfig is not None:
            cfg = BotoConfig(s3={"addressing_style": "path"})
        client = boto3.client(
            "s3",
            endpoint_url=s3_endpoint,
            aws_access_key_id=os.getenv("S3_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("S3_SECRET_ACCESS_KEY"),
            region_name=os.getenv("S3_REGION", "us-east-1"),
            config=cfg,
        )
        # Ensure bucket exists (MinIO-compatible). If it exists, creation will be ignored/raise which we catch.
        try:
            client.head_bucket(Bucket=bucket)
        except Exception:
            try:
                # MinIO typically ignores LocationConstraint; keep simple create.
                client.create_bucket(Bucket=bucket)
            except Exception:
                # If another worker created it concurrently or permissions disallow create, continue.
                pass
        client.upload_file(str(out_path), bucket, key, ExtraArgs={"ContentType": "audio/wav"})
        # Public-style URL if bucket is anonymous; otherwise caller can presign as needed.
        result["s3_url"] = f"{s3_endpoint.rstrip('/')}/{bucket}/{key}"

    return result
