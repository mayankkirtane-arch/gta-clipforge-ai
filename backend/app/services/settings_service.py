from typing import Dict, Any
from sqlalchemy.orm import Session
from ..database import SessionLocal
from ..models.setting import AppSetting
from ..config import settings

DEFAULT_SETTINGS = {
    "enable_auto_mode": "true",
    "monitoring_paused": "false",
    "auto_analyze": "true",
    "auto_generate_clips": "true",
    "require_approval": "true",
    "watch_folder_path": settings.WATCH_DIR,
}

def get_watcher_settings(db: Session = None) -> Dict[str, Any]:
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        db_settings = {}
        rows = db.query(AppSetting).all()
        for r in rows:
            db_settings[r.key] = r.value

        result = {
            "enable_auto_mode": db_settings.get("enable_auto_mode", DEFAULT_SETTINGS["enable_auto_mode"]).lower() == "true",
            "monitoring_paused": db_settings.get("monitoring_paused", DEFAULT_SETTINGS["monitoring_paused"]).lower() == "true",
            "auto_analyze": db_settings.get("auto_analyze", DEFAULT_SETTINGS["auto_analyze"]).lower() == "true",
            "auto_generate_clips": db_settings.get("auto_generate_clips", DEFAULT_SETTINGS["auto_generate_clips"]).lower() == "true",
            "require_approval": db_settings.get("require_approval", DEFAULT_SETTINGS["require_approval"]).lower() == "true",
            "watch_folder_path": db_settings.get("watch_folder_path", DEFAULT_SETTINGS["watch_folder_path"]),
        }
        return result
    finally:
        if close_db:
            db.close()

def update_watcher_settings(new_settings: Dict[str, Any], db: Session = None) -> Dict[str, Any]:
    close_db = False
    if db is None:
        db = SessionLocal()
        close_db = True

    try:
        for k, v in new_settings.items():
            if k in DEFAULT_SETTINGS:
                str_val = str(v).lower() if isinstance(v, bool) else str(v)
                setting_row = db.query(AppSetting).filter(AppSetting.key == k).first()
                if setting_row:
                    setting_row.value = str_val
                else:
                    db.add(AppSetting(key=k, value=str_val))
        db.commit()
        return get_watcher_settings(db)
    finally:
        if close_db:
            db.close()
