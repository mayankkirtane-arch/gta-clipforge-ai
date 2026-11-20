import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_

from ..database import get_db
from ..config import settings
from ..models.recording import Recording, RecordingStatus
from ..models.analysis import RecordingAnalysis, TimelineSegment, RecordingChunk
from ..models.job import Job, JobStatus, JobType
from ..services.video_engine import video_engine

router = APIRouter(prefix="/api/recordings", tags=["analysis"])

@router.get("/{recording_id}/analysis")
def get_recording_analysis(recording_id: int, db: Session = Depends(get_db)):
    """Retrieve full analysis summary, metrics, and waveform for a recording."""
    rec = db.query(Recording).filter(Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    analysis = db.query(RecordingAnalysis).filter(RecordingAnalysis.recording_id == recording_id).first()
    if not analysis:
        # Return initial pending state if analysis not yet created
        return {
            "recording_id": recording_id,
            "status": "pending",
            "progress": 0.0,
            "current_chunk": 0,
            "total_chunks": 0,
            "total_scenes": 0,
            "total_keyframes": 0,
            "audio_peaks_count": 0,
            "black_frames_count": 0,
            "silence_count": 0,
            "waveform_data": [],
            "scenes_data": [],
            "has_proxy": False,
            "has_thumbnail": False,
        }

    waveform = []
    if analysis.waveform_data:
        try:
            waveform = json.loads(analysis.waveform_data)
        except Exception:
            waveform = []

    scenes = []
    if analysis.scenes_data:
        try:
            scenes = json.loads(analysis.scenes_data)
        except Exception:
            scenes = []

    has_proxy = bool(analysis.proxy_path and os.path.isfile(analysis.proxy_path))
    has_thumb = bool(analysis.thumbnail_path and os.path.isfile(analysis.thumbnail_path))

    return {
        "id": analysis.id,
        "recording_id": analysis.recording_id,
        "status": analysis.status,
        "progress": analysis.progress,
        "current_chunk": analysis.current_chunk,
        "total_chunks": analysis.total_chunks,
        "total_scenes": analysis.total_scenes,
        "total_keyframes": analysis.total_keyframes,
        "audio_peaks_count": analysis.audio_peaks_count,
        "black_frames_count": analysis.black_frames_count,
        "silence_count": analysis.silence_count,
        "waveform_data": waveform,
        "scenes_data": scenes,
        "has_proxy": has_proxy,
        "has_thumbnail": has_thumb,
        "gpu_accelerated": analysis.gpu_accelerated,
        "chunk_duration_sec": analysis.chunk_duration_sec,
        "error": analysis.error,
        "created_at": analysis.created_at,
        "updated_at": analysis.updated_at,
    }

@router.get("/{recording_id}/timeline")
def get_recording_timeline(
    recording_id: int,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500),
    only_peaks: bool = Query(False),
    only_cuts: bool = Query(False),
    db: Session = Depends(get_db)
):
    """
    Retrieve timeline representation with keyframes, scene cuts,
    audio peaks, and excitement score.
    """
    rec = db.query(Recording).filter(Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    query = db.query(TimelineSegment).filter(TimelineSegment.recording_id == recording_id)
    if only_peaks:
        query = query.filter(TimelineSegment.is_audio_peak == True)
    if only_cuts:
        query = query.filter(TimelineSegment.is_scene_change == True)

    total = query.count()
    segments = query.order_by(TimelineSegment.timestamp.asc()).offset((page - 1) * page_size).limit(page_size).all()

    items = []
    for s in segments:
        kf_filename = Path(s.keyframe_path).name if s.keyframe_path else None
        kf_url = f"/api/recordings/{recording_id}/keyframes/{kf_filename}" if kf_filename else None
        items.append({
            "id": s.id,
            "timestamp": s.timestamp,
            "timestamp_formatted": s.timestamp_formatted,
            "scene_number": s.scene_number,
            "keyframe_url": kf_url,
            "keyframe_filename": kf_filename,
            "audio_peak_db": s.audio_peak_db,
            "is_audio_peak": s.is_audio_peak,
            "is_scene_change": s.is_scene_change,
            "is_black_frame": s.is_black_frame,
            "is_silence": s.is_silence,
            "excitement_score": s.excitement_score,
            "chunk_index": s.chunk_index,
        })

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }

@router.post("/{recording_id}/analyze")
def trigger_analysis(
    recording_id: int,
    force_reanalyze: bool = Query(False, description="Clear checkpoints and re-process from 0"),
    chunk_duration_sec: Optional[int] = Query(None),
    keyframe_interval_sec: Optional[float] = Query(None),
    gpu_acceleration: Optional[bool] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Trigger or resume chunk-based video processing.
    Supports recovery: resumes from last incomplete chunk unless force_reanalyze=True.
    """
    rec = db.query(Recording).filter(Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    if force_reanalyze:
        # Clear previous chunks & timeline segments
        db.query(TimelineSegment).filter(TimelineSegment.recording_id == recording_id).delete()
        db.query(RecordingChunk).filter(RecordingChunk.recording_id == recording_id).delete()
        existing_analysis = db.query(RecordingAnalysis).filter(RecordingAnalysis.recording_id == recording_id).first()
        if existing_analysis:
            db.delete(existing_analysis)
        db.commit()

    rec.status = RecordingStatus.PENDING
    job = Job(
        recording_id=rec.id,
        job_type=JobType.ANALYSIS,
        status=JobStatus.PENDING,
        progress=0.0,
        message="Queued for professional video engine processing",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    return {
        "status": "queued",
        "job_id": job.id,
        "recording_id": rec.id,
        "force_reanalyze": force_reanalyze,
    }

@router.get("/{recording_id}/keyframes/{filename}")
def get_keyframe_image(recording_id: int, filename: str):
    """Serve timeline keyframe thumbnail images."""
    safe_name = Path(filename).name
    kf_path = Path(settings.KEYFRAMES_DIR) / f"rec_{recording_id}" / safe_name
    if not kf_path.is_file():
        raise HTTPException(status_code=404, detail="Keyframe image not found")
    return FileResponse(str(kf_path), media_type="image/jpeg")

@router.get("/{recording_id}/thumbnail")
def get_thumbnail_image(recording_id: int, db: Session = Depends(get_db)):
    """Serve recording poster thumbnail."""
    thumb_path = Path(settings.THUMBNAILS_DIR) / f"thumb_rec_{recording_id}.jpg"
    if thumb_path.is_file():
        return FileResponse(str(thumb_path), media_type="image/jpeg")

    analysis = db.query(RecordingAnalysis).filter(RecordingAnalysis.recording_id == recording_id).first()
    if analysis and analysis.thumbnail_path and os.path.isfile(analysis.thumbnail_path):
        return FileResponse(analysis.thumbnail_path, media_type="image/jpeg")

    raise HTTPException(status_code=404, detail="Thumbnail not generated yet")

@router.get("/{recording_id}/proxy")
def stream_proxy_video(recording_id: int, request: Request, db: Session = Depends(get_db)):
    """Stream low-resolution 720p/480p preview proxy with HTTP range support."""
    proxy_path = Path(settings.PROXIES_DIR) / f"proxy_rec_{recording_id}.mp4"
    if not proxy_path.is_file():
        analysis = db.query(RecordingAnalysis).filter(RecordingAnalysis.recording_id == recording_id).first()
        if analysis and analysis.proxy_path and os.path.isfile(analysis.proxy_path):
            proxy_path = Path(analysis.proxy_path)
        else:
            raise HTTPException(status_code=404, detail="Proxy video not generated yet")

    file_size = os.path.getsize(str(proxy_path))
    range_header = request.headers.get("range")

    if not range_header:
        def iterfile():
            with open(str(proxy_path), "rb") as f:
                while chunk := f.read(1024 * 1024):
                    yield chunk
        return StreamingResponse(
            iterfile(),
            media_type="video/mp4",
            headers={"Content-Length": str(file_size), "Accept-Ranges": "bytes"}
        )

    # Range processing
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
        with open(str(proxy_path), "rb") as f:
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
        status_code=206,
        media_type="video/mp4",
        headers={
            "Content-Range": f"bytes {start}-{end}/{file_size}",
            "Accept-Ranges": "bytes",
            "Content-Length": str(chunk_length),
        }
    )
