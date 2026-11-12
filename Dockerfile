# ============================================================================
# Edionic — 24/7 Free Cloud Hosting Dockerfile (Hugging Face Spaces / Render / Railway)
# Runs Edionic Web Studio + Multi-Threaded Python Backend + FFmpeg 6+ + faster-whisper
# so the owner does NOT need to keep their personal PC turned on!
# ============================================================================

FROM python:3.11-slim

# Install FFmpeg (with libass subtitle rendering & filters) + fonts for all 11 caption presets
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libass9 \
    fonts-dejavu-core \
    fonts-liberation \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user (Required by Hugging Face Spaces Free 16GB RAM Docker tier)
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    EDIONIC_HOST=0.0.0.0 \
    EDIONIC_PORT=7860

WORKDIR /home/user/app

# Install lightweight CPU faster-whisper
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir faster-whisper==1.2.1

# Copy Edionic project files (excluding local Windows tools/ binaries via .dockerignore)
COPY --chown=user:user frontend ./frontend
COPY --chown=user:user backend ./backend
COPY --chown=user:user sfx ./sfx
COPY --chown=user:user projects ./projects

# Expose port 7860 (Hugging Face Spaces standard) and 8080
EXPOSE 7860 8080

CMD ["python", "backend/server.py"]
