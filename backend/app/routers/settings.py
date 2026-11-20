from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import Dict, Any
from ..config import settings
from ..database import get_db
from ..services.file_service import check_disk_space, ensure_directories, cleanup_temp
from ..services.settings_service import get_watcher_settings, update_watcher_settings
from ..services.watcher_service import folder_watcher

router = APIRouter(prefix="/api/settings", tags=["settings"])

@router.get("")
def get_settings():
    return {
        "recordings_dir": settings.RECORDINGS_DIR,
        "watch_dir": settings.WATCH_DIR,
        "models_dir": settings.MODELS_DIR,
        "temp_dir": settings.TEMP_DIR,
        "exports_dir": settings.EXPORTS_DIR,
        "logs_dir": settings.LOGS_DIR,
        "min_free_space_gb": settings.MIN_FREE_SPACE_GB,
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "allowed_extensions": settings.ALLOWED_EXTENSIONS,
    }

@router.get("/disk-space")
def disk_space():
    return check_disk_space()

@router.post("/ensure-dirs")
def ensure_dirs():
    return ensure_directories()

@router.post("/cleanup-temp")
def cleanup_temp_files(confirm: bool = False):
    return cleanup_temp(confirm=confirm)

@router.get("/watcher")
def get_watcher_config(db: Session = Depends(get_db)):
    config = get_watcher_settings(db)
    config["watcher_running"] = folder_watcher.is_running
    config["active_watch_path"] = folder_watcher.watch_path
    return config

@router.post("/watcher")
def save_watcher_config(payload: Dict[str, Any], db: Session = Depends(get_db)):
    updated = update_watcher_settings(payload, db)
    # If watch_folder_path changed and watcher is running, restart on new path
    if "watch_folder_path" in payload and payload["watch_folder_path"] != folder_watcher.watch_path:
        folder_watcher.stop()
        folder_watcher.start(payload["watch_folder_path"])
    updated["watcher_running"] = folder_watcher.is_running
    updated["active_watch_path"] = folder_watcher.watch_path
    return updated

@router.post("/watcher/pause")
def pause_watcher():
    folder_watcher.pause()
    return {"status": "paused", "monitoring_paused": True}

@router.post("/watcher/resume")
def resume_watcher():
    folder_watcher.resume()
    return {"status": "resumed", "monitoring_paused": False}

@router.post("/watcher/scan")
def scan_watch_folder():
    count = folder_watcher.scan_folder_now()
    return {"status": "scanned", "new_recordings_found": count}
