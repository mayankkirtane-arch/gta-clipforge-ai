# ==========================================
# GTA ClipForge AI - Multi-stage Render Dockerfile
# ==========================================

# Stage 1: Build Next.js Frontend
FROM node:20-alpine AS frontend-builder
WORKDIR /app/frontend

COPY frontend/package*.json ./
RUN npm ci || npm install

COPY frontend/ ./
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Stage 2: Unified Production Image (Python + Node.js + FFmpeg)
FROM python:3.11-slim

# Install system dependencies: FFmpeg, Node.js 20, and OpenCV libs
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libgl1 \
    libglib2.0-0 \
    curl \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python backend dependencies
COPY backend/requirements.txt ./backend/
RUN pip install --no-cache-dir -r ./backend/requirements.txt \
    && pip install --no-cache-dir yt-dlp opencv-python-headless

# Copy Backend Source
COPY backend/ ./backend/

# Copy Frontend Standalone Build
COPY --from=frontend-builder /app/frontend/.next/standalone ./frontend/
COPY --from=frontend-builder /app/frontend/.next/static ./frontend/.next/static
COPY --from=frontend-builder /app/frontend/public ./frontend/public

# Setup required directories
RUN mkdir -p /app/data \
    /app/recordings \
    /app/temp \
    /app/exports \
    /app/GTA6_SHORTS \
    /app/GTA6_RECORDINGS \
    /app/models \
    /app/logs \
    /app/assets/music \
    /app/assets/sfx

# Entrypoint script
COPY entrypoint.sh ./
RUN chmod +x entrypoint.sh

# Environment variables
ENV PYTHONPATH="/app/backend" \
    DATABASE_URL="sqlite:////app/data/clipforge.db" \
    RECORDINGS_DIR="/app/recordings" \
    WATCH_DIR="/app/GTA6_RECORDINGS" \
    MODELS_DIR="/app/models" \
    TEMP_DIR="/app/temp" \
    EXPORTS_DIR="/app/exports" \
    LOGS_DIR="/app/logs" \
    SHORTS_DIR="/app/GTA6_SHORTS" \
    FFMPEG_PATH="ffmpeg" \
    FFPROBE_PATH="ffprobe" \
    PORT=10000 \
    NODE_ENV=production

EXPOSE 10000

CMD ["./entrypoint.sh"]
