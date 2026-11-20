from pydantic_settings import BaseSettings
from typing import List
from pathlib import Path
import shutil

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///D:/GTA_CLIPFORGE_AI/data/clipforge.db"
    RECORDINGS_DIR: str = "D:/GTA_CLIPFORGE_AI/recordings"
    WATCH_DIR: str = "D:/GTA_CLIPFORGE_AI/GTA6_RECORDINGS"
    MODELS_DIR: str = "D:/GTA_CLIPFORGE_AI/models"
    TEMP_DIR: str = "D:/GTA_CLIPFORGE_AI/temp"
    EXPORTS_DIR: str = "D:/GTA_CLIPFORGE_AI/exports"
    LOGS_DIR: str = "D:/GTA_CLIPFORGE_AI/logs"
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    APP_NAME: str = "GTA ClipForge AI"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    MIN_FREE_SPACE_GB: float = 5.0

    # Watcher & Auto Processing
    ENABLE_AUTO_MODE: bool = True
    MONITORING_PAUSED: bool = False
    AUTO_ANALYZE: bool = True
    AUTO_GENERATE_CLIPS: bool = True
    REQUIRE_APPROVAL_BEFORE_EXPORT: bool = True

    # Processing Engine Config (Phase 3)
    CHUNK_DURATION_SEC: int = 300           # 5 min chunks for long recordings
    PROCESSING_CONCURRENCY: int = 2         # Max concurrent chunks
    CPU_USAGE: str = "medium"               # low, medium, high
    GPU_ACCELERATION: bool = True           # CUDA / NVENC with automatic CPU fallback
    KEYFRAME_INTERVAL_SEC: float = 10.0     # Keyframe capture interval
    SCENE_THRESHOLD: float = 27.0           # PySceneDetect ContentDetector threshold
    SILENCE_THRESHOLD_DB: float = -35.0     # Silence detection dB threshold
    AUDIO_PEAK_PERCENTILE: float = 85.0     # Percentile threshold to qualify as audio peak

    # Asset directories
    PROXIES_DIR: str = "D:/GTA_CLIPFORGE_AI/temp/proxies"
    KEYFRAMES_DIR: str = "D:/GTA_CLIPFORGE_AI/temp/keyframes"
    THUMBNAILS_DIR: str = "D:/GTA_CLIPFORGE_AI/temp/thumbnails"
    AUDIO_DIR: str = "D:/GTA_CLIPFORGE_AI/temp/audio"
    SHORTS_DIR: str = "D:/GTA_CLIPFORGE_AI/GTA6_SHORTS"
    BEST_MOMENTS_DIR: str = "D:/GTA_CLIPFORGE_AI/GTA6_BEST_MOMENTS"
    REPORTS_DIR: str = "D:/GTA_CLIPFORGE_AI/GTA6_REPORTS"
    EXPORTS_PACKAGES_DIR: str = "D:/GTA_CLIPFORGE_AI/GTA6_EXPORTS"
    SHORTS_THUMBNAILS_DIR: str = "D:/GTA_CLIPFORGE_AI/temp/thumbnails/shorts"
    ASSETS_DIR: str = "D:/GTA_CLIPFORGE_AI/assets"
    MUSIC_DIR: str = "D:/GTA_CLIPFORGE_AI/assets/music"
    SFX_DIR: str = "D:/GTA_CLIPFORGE_AI/assets/sfx"
    PREVIEWS_DIR: str = "D:/GTA_CLIPFORGE_AI/temp/previews"

    # Tool paths
    FFPROBE_PATH: str = "D:/GTA_CLIPFORGE_AI/bin/ffprobe.exe" if Path("D:/GTA_CLIPFORGE_AI/bin/ffprobe.exe").exists() else (shutil.which("ffprobe") or "ffprobe")
    FFMPEG_PATH: str = "D:/GTA_CLIPFORGE_AI/bin/ffmpeg.exe" if Path("D:/GTA_CLIPFORGE_AI/bin/ffmpeg.exe").exists() else (shutil.which("ffmpeg") or "ffmpeg")

    ALLOWED_EXTENSIONS: List[str] = [".mp4", ".mkv", ".mov", ".webm"]
    
    model_config = {"env_file": "D:/GTA_CLIPFORGE_AI/backend/.env", "env_file_encoding": "utf-8", "extra": "ignore"}

settings = Settings()
