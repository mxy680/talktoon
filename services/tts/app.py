from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import StreamingResponse, JSONResponse
from typing import Optional
import tempfile
import io
import os
from pathlib import Path
import json
import uuid
import soundfile as sf

# Use the local API wrapper (hardened to work without the f5_tts package install)
from api import F5TTS

app = FastAPI(title="Chatterbox TTS API")

_model: Optional[F5TTS] = None

# Ensure profiles directory exists
PROFILES_DIR = Path(__file__).parent / "profiles"
PROFILES_DIR.mkdir(parents=True, exist_ok=True)
ALIASES_PATH = PROFILES_DIR / "aliases.json"

def _load_aliases() -> dict:
    try:
        return json.loads(ALIASES_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_aliases(aliases: dict):
    try:
        ALIASES_PATH.write_text(json.dumps(aliases, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception:
        pass

def _ensure_default_peter():
    aliases = _load_aliases()
    if "peter" not in aliases:
        # If there is exactly one profile wav, assign it as 'peter'
        wavs = sorted([p for p in PROFILES_DIR.glob("*.wav")])
        if len(wavs) == 1:
            aliases["peter"] = wavs[0].stem
            _save_aliases(aliases)

_ensure_default_peter()

def get_model() -> F5TTS:
    global _model
    if _model is None:
        # Defaults to F5TTS_v1_Base and auto-selects best available device
        _model = F5TTS()
    return _model


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/transcribe")
async def transcribe(
    ref_audio: UploadFile = File(...),
    language: Optional[str] = Form(None),
):
    try:
        model = get_model()
        # Save uploaded file to a temp path for downstream code which expects a filepath
        with tempfile.NamedTemporaryFile(suffix=os.path.splitext(ref_audio.filename or "")[1] or ".wav", delete=False) as tmp:
            tmp.write(await ref_audio.read())
            tmp_path = tmp.name
        try:
            text = model.transcribe(tmp_path, language=language)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
        return {"text": text}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/profiles/aliases")
async def list_aliases():
    return _load_aliases()


# POST /profiles/aliases disabled: profiles are managed externally by copying files into /profiles


# POST /profiles/create disabled: profiles are managed externally by copying files into /profiles


@app.post("/infer")
async def infer(
    gen_text: str = Form(...),
    speaker: str = Form(...),
    ref_text: str = Form(""),
    remove_silence: bool = Form(False),
    nfe_step: int = Form(32),
    speed: float = Form(0.75),
    cross_fade_duration: float = Form(0.15),
    seed: Optional[int] = Form(None),
):
    if not gen_text.strip():
        return JSONResponse(status_code=400, content={"error": "gen_text is required"})
    if not speaker.strip():
        return JSONResponse(status_code=400, content={"error": "speaker is required"})

    try:
        model = get_model()

        # Resolve reference by speaker alias (no file uploads or IDs)
        resolved_ref_text = ref_text or ""
        aliases = _load_aliases()
        sid = aliases.get(speaker.lower())
        if not sid:
            # If no alias, attempt single-profile auto-assign
            wavs = sorted([p for p in PROFILES_DIR.glob("*.wav")])
            if len(wavs) == 1 and speaker.lower() == "peter":
                sid = wavs[0].stem
            else:
                return JSONResponse(status_code=404, content={"error": f"speaker alias '{speaker}' not found"})
        p_wav = PROFILES_DIR / f"{sid}.wav"
        p_txt = PROFILES_DIR / f"{sid}.txt"
        if not p_wav.exists():
            return JSONResponse(status_code=404, content={"error": f"speaker '{speaker}' not found"})
        resolved_ref_path = str(p_wav)
        if not resolved_ref_text and p_txt.exists():
            try:
                resolved_ref_text = p_txt.read_text(encoding="utf-8")
            except Exception:
                resolved_ref_text = ""

        try:
            wav, sr, _ = model.infer(
                ref_file=resolved_ref_path,
                ref_text=resolved_ref_text,
                gen_text=gen_text,
                remove_silence=remove_silence,
                nfe_step=nfe_step,
                speed=speed,
                cross_fade_duration=cross_fade_duration,
                seed=seed,
            )

            # Encode to WAV in-memory
            buf = io.BytesIO()
            sf.write(buf, wav, sr, format="WAV", subtype="PCM_16")
            buf.seek(0)
            return StreamingResponse(buf, media_type="audio/wav")
        finally:
            pass
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
