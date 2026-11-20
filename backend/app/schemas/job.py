from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from ..models.job import JobType, JobStatus

class JobCreate(BaseModel):
    recording_id: Optional[int] = None
    job_type: JobType = JobType.ANALYSIS

class JobResponse(BaseModel):
    id: int
    recording_id: Optional[int] = None
    recording_filename: Optional[str] = None
    job_type: JobType
    status: JobStatus
    progress: float
    message: Optional[str] = None
    error: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

class JobList(BaseModel):
    items: List[JobResponse]
    total: int
