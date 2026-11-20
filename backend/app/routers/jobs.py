from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_
from typing import Optional, List
from ..database import get_db
from ..models.job import Job, JobStatus
from ..models.recording import Recording, RecordingStatus
from ..schemas.job import JobResponse

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

def _format_job(job: Job) -> dict:
    return {
        "id": job.id,
        "recording_id": job.recording_id,
        "recording_filename": job.recording.original_filename if job.recording else None,
        "job_type": job.job_type,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "error": job.error,
        "started_at": job.started_at,
        "completed_at": job.completed_at,
        "created_at": job.created_at,
        "updated_at": job.updated_at,
    }

@router.get("", response_model=List[JobResponse])
def list_jobs(
    status: Optional[str] = None,
    recording_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    query = db.query(Job)
    if status:
        st = status.lower()
        if st in ["pending", "queued"]:
            query = query.filter(or_(Job.status == JobStatus.PENDING, Job.status == JobStatus.QUEUED))
        elif st in ["processing", "running"]:
            query = query.filter(or_(Job.status == JobStatus.PROCESSING, Job.status == JobStatus.RUNNING))
        elif st == "completed":
            query = query.filter(Job.status == JobStatus.COMPLETED)
        elif st == "failed":
            query = query.filter(Job.status == JobStatus.FAILED)
        elif st == "cancelled":
            query = query.filter(Job.status == JobStatus.CANCELLED)

    if recording_id:
        query = query.filter(Job.recording_id == recording_id)

    jobs = query.order_by(Job.created_at.desc()).limit(limit).all()
    return [_format_job(j) for j in jobs]

@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _format_job(job)

@router.post("/{job_id}/retry", response_model=JobResponse)
def retry_job(job_id: int, db: Session = Depends(get_db)):
    """Retry a failed or cancelled job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    job.status = JobStatus.PENDING
    job.progress = 0.0
    job.error = None
    job.message = "Job queued for retry..."
    job.started_at = None
    job.completed_at = None

    if job.recording_id:
        rec = db.query(Recording).filter(Recording.id == job.recording_id).first()
        if rec and rec.status == RecordingStatus.FAILED:
            rec.status = RecordingStatus.PENDING

    db.commit()
    db.refresh(job)
    return _format_job(job)

@router.post("/{job_id}/cancel", response_model=JobResponse)
def cancel_job(job_id: int, db: Session = Depends(get_db)):
    """Cancel a pending or running job."""
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    if job.status in [JobStatus.COMPLETED]:
        raise HTTPException(status_code=400, detail="Cannot cancel a completed job.")

    job.status = JobStatus.CANCELLED
    job.message = "Cancelled by user"
    
    if job.recording_id:
        rec = db.query(Recording).filter(Recording.id == job.recording_id).first()
        if rec and rec.status == RecordingStatus.ANALYZING:
            rec.status = RecordingStatus.PENDING

    db.commit()
    db.refresh(job)
    return _format_job(job)

@router.delete("/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    db.delete(job)
    db.commit()
    return {"status": "deleted", "job_id": job_id}
