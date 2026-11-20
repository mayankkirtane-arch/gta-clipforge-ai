import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form, status, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..config import settings
from ..models.recording import Recording, RecordingStatus
from ..models.job import Job, JobType, JobStatus
from ..schemas.recording import RecordingResponse, RecordingList, RecordingLocalImport
from ..services.video_service import validate_video, calculate_file_hash
from ..services.settings_service import get_watcher_settings

router = APIRouter(prefix="/api/recordings", tags=["recordings"])

def check_path_safety(file_path: str) -> Path:
    """Security check: validate path, prevent path traversal and restrict to permitted drives."""
    try:
        resolved = Path(file_path).resolve()
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid file path format: {str(e)}")

    if not resolved.exists():
        raise HTTPException(status_code=404, detail="File does not exist on disk.")

    if not resolved.is_file():
        raise HTTPException(status_code=400, detail="The path does not point to a regular file.")

    ext = resolved.suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type '{ext}'. Allowed extensions: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    # Restrict to D: drive or project directories for safety
    drive = resolved.drive.upper()
    if drive != "D:" and not str(resolved).startswith(str(Path("D:/").resolve())):
        # If user is running tests or has recordings in project directory, allow
        allowed_parent = Path("D:/GTA_CLIPFORGE_AI").resolve()
        if not str(resolved).startswith(str(allowed_parent)) and drive != "D:":
            raise HTTPException(
                status_code=403,
                detail="Security violation: Local import is restricted to approved D: drive locations."
            )

    return resolved

@router.get("", response_model=RecordingList)
def list_recordings(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    status: Optional[RecordingStatus] = None,
    q: Optional[str] = Query(None, description="Search query for filename or notes"),
    db: Session = Depends(get_db)
):
    query = db.query(Recording)
    if status:
        query = query.filter(Recording.status == status)
    if q and q.strip():
        search = f"%{q.strip()}%"
        query = query.filter(
            or_(Recording.filename.ilike(search), Recording.original_filename.ilike(search), Recording.notes.ilike(search))
        )
    total = query.count()
    items = query.order_by(Recording.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return RecordingList(items=items, total=total, page=page, page_size=page_size)

@router.get("/{recording_id}", response_model=RecordingResponse)
def get_recording(recording_id: int, db: Session = Depends(get_db)):
    rec = db.query(Recording).filter(Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")
    return rec

@router.post("/import-local", response_model=RecordingResponse)
def import_local_recording(payload: RecordingLocalImport, db: Session = Depends(get_db)):
    """
    Import a video file from a local path on D: drive.
    Ideal for massive 1-8 hour GTA 6 gameplay recordings (up to 100GB).
    """
    resolved_path = check_path_safety(payload.file_path)

    # 1. Validate video using FFprobe
    try:
        meta = validate_video(str(resolved_path))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"FFprobe validation failed: {str(e)}")

    # 2. Calculate file hash
    file_hash = calculate_file_hash(str(resolved_path))

    # 3. Check for duplicates in SQLite
    existing = db.query(Recording).filter(
        (Recording.file_hash == file_hash) | (Recording.file_path == str(resolved_path))
    ).first()
    if existing:
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate video: Already imported as ID {existing.id} ({existing.filename})."
        )

    # 4. Save to recordings directory if not already inside project
    recordings_dir = Path(settings.RECORDINGS_DIR).resolve()
    watch_dir = Path(settings.WATCH_DIR).resolve()
    target_path = resolved_path

    # If the file is not in recordings_dir or watch_dir, copy it into recordings_dir
    if not (str(resolved_path).startswith(str(recordings_dir)) or str(resolved_path).startswith(str(watch_dir))):
        dest_filename = f"{uuid.uuid4().hex[:8]}_{resolved_path.name}"
        target_path = recordings_dir / dest_filename
        try:
            shutil.copy2(resolved_path, target_path)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to copy recording file: {str(e)}")

    # 5. Insert into SQLite
    rec = Recording(
        filename=target_path.name,
        original_filename=resolved_path.name,
        file_path=str(target_path),
        file_size_bytes=meta["file_size_bytes"],
        duration_seconds=meta["duration_seconds"],
        resolution=meta["resolution"],
        fps=meta["fps"],
        file_hash=file_hash,
        video_codec=meta["video_codec"],
        bitrate=meta["bitrate"],
        status=RecordingStatus.PENDING,
        notes=payload.notes or "Manually imported from local path",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # 6. Add analysis job
    app_settings = get_watcher_settings(db)
    if app_settings.get("auto_analyze", True):
        job = Job(
            recording_id=rec.id,
            job_type=JobType.ANALYSIS,
            status=JobStatus.PENDING,
            progress=0.0,
            message="Queued for AI analysis",
        )
        db.add(job)
        db.commit()

    return rec

@router.post("/upload", response_model=RecordingResponse)
async def upload_recording(
    file: UploadFile = File(...),
    notes: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    """
    Direct upload for video files (MP4, MKV, MOV, WebM).
    Streams chunks directly to D: drive storage.
    """
    filename = file.filename or "recording.mp4"
    ext = Path(filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file format '{ext}'. Allowed formats: {', '.join(settings.ALLOWED_EXTENSIONS)}"
        )

    recordings_dir = Path(settings.RECORDINGS_DIR).resolve()
    recordings_dir.mkdir(parents=True, exist_ok=True)
    dest_path = recordings_dir / f"{uuid.uuid4().hex[:8]}_{filename}"

    # Stream write
    try:
        with open(dest_path, "wb") as buffer:
            while chunk := await file.read(4 * 1024 * 1024):  # 4MB chunks
                buffer.write(chunk)
    except Exception as e:
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to save uploaded file: {str(e)}")

    # Validate video with FFprobe
    try:
        meta = validate_video(str(dest_path))
    except Exception as e:
        if dest_path.exists():
            dest_path.unlink()
        raise HTTPException(status_code=400, detail=f"Invalid video file: {str(e)}")

    # Hash
    file_hash = calculate_file_hash(str(dest_path))

    # Duplicate check
    existing = db.query(Recording).filter(Recording.file_hash == file_hash).first()
    if existing:
        dest_path.unlink()
        raise HTTPException(
            status_code=409,
            detail=f"Duplicate video: Identical file already exists as ID {existing.id} ({existing.filename})."
        )

    rec = Recording(
        filename=dest_path.name,
        original_filename=filename,
        file_path=str(dest_path),
        file_size_bytes=meta["file_size_bytes"],
        duration_seconds=meta["duration_seconds"],
        resolution=meta["resolution"],
        fps=meta["fps"],
        file_hash=file_hash,
        video_codec=meta["video_codec"],
        bitrate=meta["bitrate"],
        status=RecordingStatus.PENDING,
        notes=notes or "Manually uploaded file",
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    # Enqueue analysis job
    app_settings = get_watcher_settings(db)
    if app_settings.get("auto_analyze", True):
        job = Job(
            recording_id=rec.id,
            job_type=JobType.ANALYSIS,
            status=JobStatus.PENDING,
            progress=0.0,
            message="Queued for AI analysis",
        )
        db.add(job)
        db.commit()

    return rec

@router.post("/{recording_id}/reprocess", response_model=RecordingResponse)
def reprocess_recording(recording_id: int, db: Session = Depends(get_db)):
    """Reprocess an existing recording: reset status and queue a new analysis job."""
    rec = db.query(Recording).filter(Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    rec.status = RecordingStatus.PENDING
    job = Job(
        recording_id=rec.id,
        job_type=JobType.ANALYSIS,
        status=JobStatus.PENDING,
        progress=0.0,
        message="Reprocessing triggered by user",
    )
    db.add(job)
    db.commit()
    db.refresh(rec)
    return rec

@router.delete("/{recording_id}")
def delete_recording(
    recording_id: int,
    delete_file: bool = Query(False, description="Also delete physical file from disk"),
    db: Session = Depends(get_db)
):
    """Delete recording from SQLite and optionally remove file from disk."""
    rec = db.query(Recording).filter(Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    file_path = rec.file_path
    db.delete(rec)
    db.commit()

    file_deleted = False
    if delete_file and file_path and os.path.isfile(file_path):
        try:
            os.remove(file_path)
            file_deleted = True
        except Exception:
            pass

    return {
        "status": "deleted",
        "recording_id": recording_id,
        "file_deleted": file_deleted,
    }

@router.get("/{recording_id}/stream")
def stream_recording(recording_id: int, request: Request, db: Session = Depends(get_db)):
    """HTTP Range stream endpoint for video preview in browser."""
    rec = db.query(Recording).filter(Recording.id == recording_id).first()
    if not rec or not os.path.isfile(rec.file_path):
        raise HTTPException(status_code=404, detail="Video file not found")

    file_path = rec.file_path
    file_size = os.path.getsize(file_path)
    range_header = request.headers.get("range")

    content_type = "video/mp4"
    ext = Path(file_path).suffix.lower()
    if ext == ".webm":
        content_type = "video/webm"
    elif ext == ".mov":
        content_type = "video/quicktime"
    elif ext == ".mkv":
        content_type = "video/x-matroska"

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

    # Parse Range Header e.g. bytes=0-1048575
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
