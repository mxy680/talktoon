# App image with uv, FFmpeg, Playwright, and an internal scheduler (supercronic)
FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    UV_SYSTEM_PYTHON=1

# System deps: ffmpeg, fonts, curl (for health), and browser deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    fonts-dejavu \
    ca-certificates \
    curl \
    git \
    wget \
    gnupg \
    libnss3 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libxshmfence1 \
    fonts-liberation \
    libappindicator3-1 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install uv
RUN pip install --no-cache-dir uv

# Copy project metadata for dependency resolution (deps will be added later)
COPY pyproject.toml ./

# Install Playwright browsers (Chromium) and deps
RUN pip install --no-cache-dir playwright && \
    python -m playwright install --with-deps chromium

# Install supercronic for cron-like scheduling in container
# Source: https://github.com/aptible/supercronic/releases
ARG SUPERCRONIC_VERSION=v0.2.27
RUN ARCH=$(dpkg --print-architecture) && \
    curl -fsSLo /usr/local/bin/supercronic \
      https://github.com/aptible/supercronic/releases/download/${SUPERCRONIC_VERSION}/supercronic-linux-${ARCH} && \
    chmod +x /usr/local/bin/supercronic

# App directories (mounted at runtime)
RUN mkdir -p /app/assets /app/config /app/data /app/orchestration/scheduler

# Default crontab (placeholder) runs a no-op until scripts are added
COPY orchestration/scheduler/crontab /app/orchestration/scheduler/crontab

# Environment file mounted at runtime
# .env should be provided via docker-compose/env_file or --env-file

# Use supercronic as PID 1 to execute schedule
CMD ["/usr/local/bin/supercronic", "/app/orchestration/scheduler/crontab"]
