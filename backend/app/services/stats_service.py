from sqlalchemy.orm import Session
from sqlalchemy import text
from ..models.recording import Recording
from ..models.clip import Clip, ClipStatus
from ..models.job import Job, JobStatus
from ..schemas.stats import DashboardStats, SystemStatus
from ..config import settings
import shutil
from pathlib import Path

def get_dashboard_stats(db: Session) -> DashboardStats:
    total_recordings = db.query(Recording).count()
    total_clips = db.query(Clip).filter(Clip.status.in_([
        ClipStatus.GENERATED, ClipStatus.APPROVED, ClipStatus.EXPORTED
    ])).count()
    processing_jobs = db.query(Job).filter(Job.status.in_([
        JobStatus.PENDING, JobStatus.QUEUED, JobStatus.PROCESSING, JobStatus.RUNNING
    ])).count()
    approved_clips = db.query(Clip).filter(Clip.is_approved == True).count()
    
    return DashboardStats(
        total_recordings=total_recordings,
        total_clips_generated=total_clips,
        processing_jobs=processing_jobs,
        approved_clips=approved_clips,
    )

def get_system_status(db: Session) -> SystemStatus:
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception:
        db_status = "error"
    
    def check_path(path_str: str) -> str:
        p = Path(path_str)
        return "ok" if p.exists() and p.is_dir() else "missing"
    
    free_gb = None
    total_gb = None
    try:
        usage = shutil.disk_usage("D:\\")
        free_gb = round(usage.free / (1024**3), 2)
        total_gb = round(usage.total / (1024**3), 2)
    except Exception:
        pass
    
    return SystemStatus(
        database=db_status,
        storage_recordings=check_path(settings.RECORDINGS_DIR),
        storage_exports=check_path(settings.EXPORTS_DIR),
        storage_shorts=check_path(settings.SHORTS_DIR),
        storage_temp=check_path(settings.TEMP_DIR),
        free_space_gb=free_gb,
        total_space_gb=total_gb,
        version=settings.APP_VERSION,
    )
