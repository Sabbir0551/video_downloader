# syntax=docker/dockerfile:1
# ------------------------------------------------------------------------------
# Stage 1: Build Dependencies
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --user -r requirements.txt

# ------------------------------------------------------------------------------
# Stage 2: Runtime Image
# ------------------------------------------------------------------------------
FROM python:3.12-slim AS runner

# System packages: ffmpeg (audio/video merge), nodejs (yt-dlp JS signature de-obfuscation), curl (healthcheck)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    nodejs \
    curl \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Create unprivileged service user with fixed UID 10001
RUN groupadd -g 10001 anystream && \
    useradd -u 10001 -g anystream -m -d /home/anystream -s /bin/bash anystream

# Setup directories with correct permissions
RUN mkdir -p /app /storage/tmp /home/anystream/.cache && \
    chown -R anystream:anystream /app /storage /home/anystream

# Copy installed Python packages from builder
COPY --from=builder /root/.local /home/anystream/.local

# Set environment
ENV PATH="/home/anystream/.local/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    STORAGE_DIR=/storage/tmp

WORKDIR /app

# Copy application source code
COPY --chown=anystream:anystream . /app

# Switch to unprivileged user
USER 10001:10001

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
  CMD curl -f http://localhost:8000/health/live || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
