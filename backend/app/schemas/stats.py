from pydantic import BaseModel
from typing import Optional

class DashboardStats(BaseModel):
    total_recordings: int = 0
    total_clips_generated: int = 0
    processing_jobs: int = 0
    approved_clips: int = 0

class SystemStatus(BaseModel):
    database: str = "unknown"
    storage_recordings: str = "unknown"
    storage_exports: str = "unknown"
    storage_shorts: str = "unknown"
    storage_temp: str = "unknown"
    free_space_gb: Optional[float] = None
    total_space_gb: Optional[float] = None
    version: str = "1.0.0"
