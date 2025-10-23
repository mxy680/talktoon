from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, ValidationError


class Models(BaseModel):
    script_model: str = Field(..., description="OpenAI model for script generation")
    tts_model: str = Field(..., description="OpenAI TTS model")
    tts_voice: str = Field(..., description="OpenAI TTS voice name")


class Video(BaseModel):
    width: int = 1080
    height: int = 1920
    fps: int = 30
    music_db: Optional[float] = None


class Captioning(BaseModel):
    mode: str = Field("rendered", description="rendered | srt")
    api_base: str = "http://captioning-sidecar:3123"
    style: Optional[str] = None

class AppConfig(BaseModel):
    models: Models
    video: Video = Video()
    captioning: Captioning = Captioning()


def load_config(path: str | os.PathLike = "config/config.yaml") -> AppConfig:
    cfg_path = Path(path)
    if not cfg_path.exists():
        raise FileNotFoundError(f"Config not found at {cfg_path}")
    data = yaml.safe_load(cfg_path.read_text())
    try:
        return AppConfig(**data)
    except ValidationError as e:
        # Surface a concise message; callers can print str(e) for details
        raise ValueError(f"Invalid config at {cfg_path}: {e}")
