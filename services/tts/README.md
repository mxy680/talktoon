# Chatterbox TTS API (F5-TTS)

FastAPI-based HTTP API for text-to-speech voice cloning using F5-TTS. Uses read-only, file-based speaker profiles with aliases (e.g., `speaker=peter`). Default voice speed is 0.75 for a slower, more natural delivery. Dockerized for easy deployment.

## Features
- /health, /transcribe, /infer endpoints
- Reference-audio conditioning (no fine-tuning on each call)
- Read-only speaker profiles resolved by alias (e.g., `speaker=peter`)
- Default speed=0.75 (slower delivery)
- Works locally or in Docker

## Requirements (local)
- Python 3.11
- FFmpeg installed (for audio IO convenience)
- Install deps:
  - `pip install -r requirements.txt`
- Recommended environment:
  - Set `PYTHONHASHSEED=0` when running the server for stability

## Run locally
```
PYTHONHASHSEED=0 uvicorn app:app --host 0.0.0.0 --port 7861
```

## Endpoints

### GET /health
- Returns `{"status":"ok"}` if the server is ready.

### POST /transcribe
- Purpose: Transcribe a reference audio clip (for cases you don’t supply `ref_text`).
- Multipart form fields:
  - `ref_audio` (file)
  - `language` (optional, e.g. `en`)
- Response:
  - `{"text": "<transcription>"}`
- Example:
- Response:
  - `{"profile_id": "<uuid>", "has_ref_text": true|false}`
- Example:
```
REF_TXT="Hi, Lois. It's a great morning, no matter how you slice it. Well, that's odd. It's not like we're short on dough."
curl -sS -X POST http://localhost:7861/profiles/create \
  -F ref_audio=@peter_ref.wav \
  -F ref_text="$REF_TXT" \
  -o profile.json
```

### POST /infer
- Purpose: Generate speech from a named speaker profile.
- Multipart form fields:
  - `speaker` (required alias, e.g., `peter`)
  - `gen_text` (required string)
  - `ref_text` (optional string)
  - `remove_silence` (optional bool; default false)
  - `nfe_step` (optional int; default 32; higher → more compute/quality)
  - `speed` (optional float; default 0.75)
  - `cross_fade_duration` (optional float; default 0.15)
  - `seed` (optional int; reproducibility)
- Response: `audio/wav` stream
- Example:
```
curl -sS -X POST http://localhost:7861/infer \
  -F speaker=peter \
  -F gen_text="Containerized inference works." \
  --output container_demo.wav
```

## How it works
- Loads F5-TTS config and backbone (DiT/UNetT) and weights on first use.
- Loads a vocoder (Vocos) for waveform synthesis.
- If `ref_text` is omitted, the server uses Whisper (openai/whisper-large-v3-turbo) to transcribe the reference once.
- Per request, it performs inference conditioned on the reference (no training/fine-tuning).

## Reusable speaker profiles
- Managed by files and `aliases.json` only (no API creation route).
- Infer many times using `speaker=<alias>`.
- Files stored under `profiles/` persist across restarts.

## Docker
### Build
```
docker build -t chatterbox-tts:latest .
```

### Run (with persisted profiles and HF cache)
```
mkdir -p profiles hf_cache
docker run --rm -p 7861:7861 \
  -v $(pwd)/profiles:/app/profiles \
  -v $(pwd)/hf_cache:/cache/huggingface \
  chatterbox-tts:latest
```

### Test in container (speaker-only)
```
curl http://localhost:7861/health

# infer using alias (ensure profiles/aliases.json contains {"peter":"<uuid>"})
curl -sS -X POST http://localhost:7861/infer \
  -F speaker=peter \
  -F gen_text="Containerized inference works." \
  --output container_demo.wav
```

## Tips for best similarity
- Provide an accurate `ref_text` matching your reference clip.
- Use a clean 6–12s reference from a single speaker.
- Default `speed=0.75` (slower). Adjust as needed, e.g. `speed=0.9` (faster) or `speed=0.6` (much slower).
- Consider `nfe_step=48` for slightly better quality.
- Use `seed` for deterministic results.

## Troubleshooting
- 422: "Field required ref_audio" on /infer
  - You must supply either `profile_id` or `ref_audio`. If using a profile, you don’t need `ref_audio`.
- 500 Internal Server Error
  - Check server logs. Ensure ffmpeg and libsndfile are installed; verify model download/cache directories are writable.
- Multipart upload
  - Use `-F ref_audio=@file.wav` (with `@`), not `-F ref_audio="file.wav"`.
- Performance
  - Use profiles to avoid reupload and re-ASR per request. Persist HF cache via `-v $(pwd)/hf_cache:/cache/huggingface`.

## License / Credits
- F5-TTS model and checkpoints by the original authors (see upstream repository and model cards on Hugging Face).
- This API wraps the model for practical usage (transcription + TTS + profiles).
