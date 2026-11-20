import os
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status, BackgroundTasks
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import desc, asc

from ..database import get_db, SessionLocal
from ..models.clip import Clip, ClipStatus, MomentType
from ..models.candidate_clip import CandidateClip
from ..models.recording import Recording
from ..models.job import Job, JobStatus, JobType
from ..schemas.clip import (
    ClipResponse,
    ShortGenerationRequest,
    BatchShortGenerationRequest,
    ShortVerificationResult,
)
from ..services.shorts_generator import shorts_generator
from ..services.copyright_risk_service import copyright_risk_service

router = APIRouter(prefix="/api/clips", tags=["clips"])

@router.get("", response_model=List[ClipResponse])
def list_clips(
    recording_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    render_mode: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("created_at", description="created_at, excitement_score, duration"),
    sort_order: str = Query("desc", description="asc or desc"),
    db: Session = Depends(get_db)
):
    """List generated clips with filtering, sorting, and pagination."""
    query = db.query(Clip)
    if recording_id:
        query = query.filter(Clip.recording_id == recording_id)
    if status and status != "all":
        query = query.filter(Clip.status == status)
    if render_mode and render_mode != "all":
        query = query.filter(Clip.render_mode == render_mode)

    if sort_by == "excitement_score":
        col = Clip.excitement_score
    elif sort_by == "duration":
        col = Clip.duration
    else:
        col = Clip.created_at

    if sort_order == "asc":
        query = query.order_by(asc(col))
    else:
        query = query.order_by(desc(col))

    return query.offset((page - 1) * page_size).limit(page_size).all()

@router.get("/{clip_id}", response_model=ClipResponse)
def get_clip(clip_id: int, db: Session = Depends(get_db)):
    """Get single clip details."""
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    return clip

@router.post("/generate", response_model=ClipResponse)
def generate_short(req: ShortGenerationRequest, db: Session = Depends(get_db)):
    """Generate a single 9:16 vertical YouTube Short synchronously."""
    recording = db.query(Recording).filter(Recording.id == req.recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    start_time = req.start_time
    end_time = req.end_time

    # If candidate_clip_id is provided, pull timings and category from candidate clip
    if req.candidate_clip_id:
        c = db.query(CandidateClip).filter(CandidateClip.id == req.candidate_clip_id).first()
        if c:
            if start_time is None:
                start_time = c.start_time
            if end_time is None:
                end_time = c.end_time
            if not req.title:
                req.title = c.title
            if not req.subtitle_text:
                req.subtitle_text = c.category_label

    if start_time is None or end_time is None:
        raise HTTPException(status_code=400, detail="Start time and end time are required.")

    try:
        res = shorts_generator.generate_single_short(
            recording_id=req.recording_id,
            start_time=start_time,
            end_time=end_time,
            title=req.title,
            candidate_clip_id=req.candidate_clip_id,
            detected_moment_id=req.detected_moment_id,
            target_length=req.target_length or 30,
            render_mode=req.render_mode or "blurred_background",
            subtitles=req.subtitles or False,
            subtitle_text=req.subtitle_text,
            subtitle_style=req.subtitle_style or "vice_neon",
            fps=req.fps,
            use_gpu=req.use_gpu if req.use_gpu is not None else True,
        )
        clip = db.query(Clip).filter(Clip.id == res["clip_id"]).first()
        return clip
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Shorts generation failed: {str(e)}")

@router.post("/batch-generate")
def batch_generate_shorts(req: BatchShortGenerationRequest, db: Session = Depends(get_db)):
    """Queue a batch YouTube Shorts generation job for candidate clips."""
    recording = db.query(Recording).filter(Recording.id == req.recording_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    job = Job(
        recording_id=req.recording_id,
        job_type=JobType.CLIP_GENERATION,
        status=JobStatus.PENDING,
        progress=0.0,
        message=f"Queued YouTube Shorts generation for {recording.original_filename} (1080x1920 9:16)",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "status": "queued",
        "job_id": job.id,
        "recording_id": req.recording_id,
        "message": "YouTube Shorts generation job queued successfully"
    }

@router.get("/{clip_id}/stream")
def stream_clip(clip_id: int, request: Request, db: Session = Depends(get_db)):
    """HTTP Range 206 video streaming for in-browser 9:16 HTML5 preview."""
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip or not clip.clip_path or not os.path.isfile(clip.clip_path):
        raise HTTPException(status_code=404, detail="Clip video file not found")

    file_path = clip.clip_path
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")

    content_type = "video/mp4"

    if not range_header:
        def iterfile():
            with open(file_path, "rb") as f:
                while chunk := f.read(1024 * 1024):
                    yield chunk
        return StreamingResponse(
            iterfile(),
            media_type=content_type,
            headers={"Content-Length": str(file_size), "Accept-Ranges": "bytes"}
        )

    range_str = range_header.strip().lower()
    if not range_str.startswith("bytes="):
        raise HTTPException(status_code=416, detail="Invalid range unit")

    ranges = range_str[6:].split("-")
    start = int(ranges[0]) if ranges[0] else 0
    end = int(ranges[1]) if ranges[1] else file_size - 1

    if start >= file_size or end >= file_size:
        raise HTTPException(status_code=416, detail="Range out of bounds")

    chunk_length = end - start + 1

    def iter_range():
        with open(file_path, "rb") as f:
            f.seek(start)
            remaining = chunk_length
            while remaining > 0:
                chunk = f.read(min(remaining, 1024 * 1024))
                if not chunk:
                    break
                remaining -= len(chunk)
                yield chunk

    return StreamingResponse(
        iter_range(),
        status_code=status.HTTP_206_PARTIAL_CONTENT,
        media_type=content_type,
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_length),
        }
    )

@router.get("/{clip_id}/thumbnail")
def get_clip_thumbnail(clip_id: int, db: Session = Depends(get_db)):
    """Serve representative 9:16 thumbnail image."""
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip or not clip.thumbnail_path or not os.path.isfile(clip.thumbnail_path):
        raise HTTPException(status_code=404, detail="Thumbnail not found")
    return FileResponse(clip.thumbnail_path, media_type="image/jpeg")

@router.get("/{clip_id}/download")
def download_clip(clip_id: int, db: Session = Depends(get_db)):
    """Download generated YouTube Short MP4 file."""
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip or not clip.clip_path or not os.path.isfile(clip.clip_path):
        raise HTTPException(status_code=404, detail="Clip video file not found")
    filename = Path(clip.clip_path).name
    return FileResponse(clip.clip_path, media_type="video/mp4", filename=filename)

@router.get("/{clip_id}/verify")
def verify_clip(clip_id: int, db: Session = Depends(get_db)):
    """Run FFprobe verification on generated YouTube Short file."""
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip or not clip.clip_path or not os.path.isfile(clip.clip_path):
        raise HTTPException(status_code=404, detail="Clip file not found on disk")

    res = shorts_generator.verify_short_file(clip.clip_path, expected_duration=clip.duration or 30.0)
    res["clip_id"] = clip.id
    return res

@router.patch("/{clip_id}/approve", response_model=ClipResponse)
def approve_clip(clip_id: int, force: bool = False, db: Session = Depends(get_db)):
    """
    Approve a clip for export/publishing.
    Guarded by Phase 9 Copyright & Creator Permission checks.
    Blocks approval if permissions are missing, rejected, or expired unless force=True or manually approved.
    """
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    allowed, block_reason = copyright_risk_service.check_clip_export_allowed(db, clip_id)
    if not allowed and not force:
        raise HTTPException(
            status_code=403,
            detail=f"{block_reason} (Update permissions or submit a manual review override in Copyright Center)"
        )

    clip.is_approved = True
    clip.status = ClipStatus.APPROVED
    db.commit()

    # Phase 10: Sync approval into Publishing Workspace checklist
    try:
        from ..services.publishing_service import publishing_service
        import json
        pub_item = publishing_service.get_or_create_publishing_item(db, clip.id)
        pub_item.status = "ready"
        chk = json.loads(pub_item.checklist_json) if pub_item.checklist_json else {}
        chk["user_approved"] = True
        chk["copyright_cleared"] = True
        pub_item.checklist_json = json.dumps(chk)
        db.commit()
    except Exception as ex:
        print(f"Publishing sync notice for Clip #{clip.id}: {ex}")

    db.refresh(clip)
    return clip

@router.patch("/{clip_id}/reject", response_model=ClipResponse)
def reject_clip(clip_id: int, db: Session = Depends(get_db)):
    """Reject a clip."""
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")
    clip.is_approved = False
    clip.status = ClipStatus.REJECTED
    db.commit()
    db.refresh(clip)
    return clip

@router.delete("/{clip_id}")
def delete_clip(clip_id: int, delete_file: bool = False, db: Session = Depends(get_db)):
    """Delete a clip record and optionally its video file from GTA6_SHORTS."""
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail="Clip not found")

    if delete_file and clip.clip_path and os.path.isfile(clip.clip_path):
        try:
            os.remove(clip.clip_path)
        except Exception:
            pass

    if delete_file and clip.thumbnail_path and os.path.isfile(clip.thumbnail_path):
        try:
            os.remove(clip.thumbnail_path)
        except Exception:
            pass

    db.delete(clip)
    db.commit()
    return {"status": "success", "deleted_clip_id": clip_id}
