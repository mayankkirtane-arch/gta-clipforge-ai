from pathlib import Path
from ..config import settings
import shutil

def check_disk_space(required_gb: float = 1.0) -> dict:
    try:
        check_path = settings.RECORDINGS_DIR if Path(settings.RECORDINGS_DIR).exists() else "/"
        usage = shutil.disk_usage(check_path)
        free_gb = usage.free / (1024**3)
        total_gb = usage.total / (1024**3)
        sufficient = free_gb >= max(required_gb, settings.MIN_FREE_SPACE_GB)
        return {
            "sufficient": sufficient,
            "free_gb": round(free_gb, 2),
            "total_gb": round(total_gb, 2),
            "required_gb": required_gb,
            "warning": not sufficient,
        }
    except Exception as e:
        return {"sufficient": False, "error": str(e)}

def ensure_directories():
    dirs = [
        settings.RECORDINGS_DIR,
        settings.WATCH_DIR,
        settings.MODELS_DIR,
        settings.TEMP_DIR,
        settings.EXPORTS_DIR,
        settings.LOGS_DIR,
        settings.PROXIES_DIR,
        settings.KEYFRAMES_DIR,
        settings.THUMBNAILS_DIR,
        settings.AUDIO_DIR,
        settings.SHORTS_DIR,
        settings.BEST_MOMENTS_DIR,
        settings.REPORTS_DIR,
        settings.EXPORTS_PACKAGES_DIR,
        settings.SHORTS_THUMBNAILS_DIR,
        settings.ASSETS_DIR,
        settings.MUSIC_DIR,
        settings.SFX_DIR,
        settings.PREVIEWS_DIR,
    ]
    for d in dirs:
        Path(d).mkdir(parents=True, exist_ok=True)
    return {"status": "ok", "dirs": dirs}

def cleanup_temp(confirm: bool = False) -> dict:
    if not confirm:
        temp_path = Path(settings.TEMP_DIR)
        files = list(temp_path.glob("*"))
        return {"files_found": len(files), "confirm_required": True}
    temp_path = Path(settings.TEMP_DIR)
    removed = 0
    for f in temp_path.glob("*"):
        try:
            if f.is_file():
                f.unlink()
                removed += 1
            elif f.is_dir() and f.name not in ["proxies", "keyframes", "thumbnails", "audio"]:
                shutil.rmtree(f, ignore_errors=True)
                removed += 1
        except Exception:
            pass
    return {"removed": removed, "status": "cleaned"}
