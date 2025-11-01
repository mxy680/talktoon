# Chatterbox TTS API - Docker image
# CPU base; installs minimal system libs for soundfile and ffmpeg for convenience
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONHASHSEED=0 \
    HF_HOME=/cache/huggingface

# System deps: libsndfile for soundfile, ffmpeg for optional audio ops, git for HF
RUN apt-get update && apt-get install -y --no-install-recommends \
    libsndfile1 \
    ffmpeg \
    git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (better layer caching)
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy app code
COPY . .

# Ensure profiles dir exists (you can also mount a volume)
RUN mkdir -p /app/profiles /cache/huggingface

EXPOSE 7861

# Start the FastAPI app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7861"]
