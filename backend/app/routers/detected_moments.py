import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from ..database import get_db, SessionLocal
from ..config import settings
from ..models.recording import Recording
from ..models.detected_moment import DetectedMoment
from ..models.clip import Clip, ClipStatus, MomentType
from ..models.job import Job, JobStatus, JobType
from ..schemas.detected_moment import (
    DetectedMomentResponse,
    DetectedMomentUpdate,
    DetectionTriggerRequest,
    DetectedMomentListResponse,
    DetectedMomentSummary,
)
from ..services.gta_detector import gta_detector, EVENT_DEFINITIONS

router = APIRouter(prefix="/api/moments", tags=["detected-moments"])

@router.get("/event-types")
def get_event_types():
    """Return all 14 GTA 6 specialized event definitions with descriptions and aesthetic styling."""
    return [
        {
            "id": k,
            "label": v["label"],
            "description": v["description"],
            "color": v["color"],
            "icon": v["icon"],
        }
        for k, v in EVENT_DEFINITIONS.items()
    ]

@router.get("", response_model=DetectedMomentListResponse)
def list_moments(
    recording_id: Optional[int] = Query(None),
    event_type: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    is_uncertain: Optional[bool] = Query(None),
    min_confidence: Optional[float] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """List detected gameplay moments across recordings with multi-criteria filtering."""
    query = db.query(DetectedMoment)

    if recording_id is not None:
        query = query.filter(DetectedMoment.recording_id == recording_id)
    if event_type and event_type != "all":
        query = query.filter(DetectedMoment.event_type == event_type)
    if status and status != "all":
        query = query.filter(DetectedMoment.status == status)
    if is_uncertain is not None:
        query = query.filter(DetectedMoment.is_uncertain == is_uncertain)
    if min_confidence is not None:
        query = query.filter(DetectedMoment.confidence_score >= min_confidence)

    total = query.count()
    moments = query.order_by(DetectedMoment.start_time.asc()).offset((page - 1) * page_size).limit(page_size).all()

    # Calculate summary metrics for the active filter scope
    base_summary_query = db.query(DetectedMoment)
    if recording_id is not None:
        base_summary_query = base_summary_query.filter(DetectedMoment.recording_id == recording_id)

    total_moments = base_summary_query.count()
    approved_moments = base_summary_query.filter(DetectedMoment.is_approved == True).count()
    uncertain_moments = base_summary_query.filter(DetectedMoment.is_uncertain == True).count()
    high_conf_moments = base_summary_query.filter(DetectedMoment.confidence_score >= 70.0).count()

    event_counts_rows = (
        db.query(DetectedMoment.event_type, func.count(DetectedMoment.id))
        .group_by(DetectedMoment.event_type)
        .all()
    )
    event_counts = {r[0]: r[1] for r in event_counts_rows}

    # Prepare response items with parsed visual_features
    items = []
    for m in moments:
        feat = None
        if m.visual_features:
            try:
                feat = json.loads(m.visual_features)
            except Exception:
                pass

        items.append(
            DetectedMomentResponse(
                id=m.id,
                recording_id=m.recording_id,
                event_type=m.event_type,
                event_label=m.event_label,
                start_time=m.start_time,
                end_time=m.end_time,
                duration=m.duration,
                confidence_score=m.confidence_score,
                explanation=m.explanation,
                is_uncertain=m.is_uncertain,
                uncertainty_reason=m.uncertainty_reason,
                thumbnail_path=m.thumbnail_path,
                thumbnail_url=m.thumbnail_url,
                keyframe_timestamp=m.keyframe_timestamp,
                visual_features=feat,
                detection_sensitivity=m.detection_sensitivity,
                status=m.status,
                is_approved=m.is_approved,
                notes=m.notes,
                clip_id=m.clip_id,
                created_at=m.created_at,
                updated_at=m.updated_at,
            )
        )

    return DetectedMomentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        summary=DetectedMomentSummary(
            total_moments=total_moments,
            approved_moments=approved_moments,
            uncertain_moments=uncertain_moments,
            high_confidence_moments=high_conf_moments,
            event_counts=event_counts,
        ),
    )

@router.get("/{moment_id}", response_model=DetectedMomentResponse)
def get_moment(moment_id: int, db: Session = Depends(get_db)):
    """Retrieve detailed moment metadata including visual feature vectors."""
    m = db.query(DetectedMoment).filter(DetectedMoment.id == moment_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Detected moment not found")

    feat = None
    if m.visual_features:
        try:
            feat = json.loads(m.visual_features)
        except Exception:
            pass

    return DetectedMomentResponse(
        id=m.id,
        recording_id=m.recording_id,
        event_type=m.event_type,
        event_label=m.event_label,
        start_time=m.start_time,
        end_time=m.end_time,
        duration=m.duration,
        confidence_score=m.confidence_score,
        explanation=m.explanation,
        is_uncertain=m.is_uncertain,
        uncertainty_reason=m.uncertainty_reason,
        thumbnail_path=m.thumbnail_path,
        thumbnail_url=m.thumbnail_url,
        keyframe_timestamp=m.keyframe_timestamp,
        visual_features=feat,
        detection_sensitivity=m.detection_sensitivity,
        status=m.status,
        is_approved=m.is_approved,
        notes=m.notes,
        clip_id=m.clip_id,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )

@router.post("/recordings/{recording_id}/detect")
def trigger_recording_moment_detection(
    recording_id: int,
    req: DetectionTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Execute GTA 6 specialized moment detection for a recording.
    Combines OpenCV optical flow, color space signatures, speech-independent acoustic analysis,
    and optional local VLM with configurable sensitivity and deduplication.
    """
    rec = db.query(Recording).filter(Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    job = Job(
        recording_id=rec.id,
        job_type=JobType.MOMENT_DETECTION,
        status=JobStatus.PROCESSING,
        progress=5.0,
        message=f"Starting GTA 6 specialized moment detection (sensitivity: {req.sensitivity})...",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    def run_detection_task(job_id: int, recording_id: int, options: DetectionTriggerRequest):
        task_db = SessionLocal()
        try:
            def progress_callback(pct: float, msg: str):
                try:
                    j = task_db.query(Job).filter(Job.id == job_id).first()
                    if j:
                        j.progress = round(pct, 1)
                        j.message = msg
                        task_db.commit()
                except Exception:
                    pass

            results = gta_detector.detect_moments_for_recording(
                recording_id=recording_id,
                sensitivity=options.sensitivity,
                min_confidence=options.min_confidence,
                min_duration_sec=options.min_duration_sec or 3.0,
                max_duration_sec=options.max_duration_sec or 60.0,
                merge_gap_sec=options.merge_gap_sec or 4.0,
                enabled_event_types=options.enabled_event_types,
                use_vlm=options.use_vlm,
                progress_cb=progress_callback,
            )

            j = task_db.query(Job).filter(Job.id == job_id).first()
            if j:
                j.status = JobStatus.COMPLETED
                j.progress = 100.0
                j.message = f"Detected {len(results)} GTA 6 gameplay moments."
                j.completed_at = func.now()
                task_db.commit()

        except Exception as e:
            try:
                j = task_db.query(Job).filter(Job.id == job_id).first()
                if j:
                    j.status = JobStatus.FAILED
                    j.error = str(e)
                    j.message = f"Detection failed: {e}"
                    task_db.commit()
            except Exception:
                pass
        finally:
            task_db.close()

    background_tasks.add_task(run_detection_task, job.id, rec.id, req)

    return {
        "status": "started",
        "job_id": job.id,
        "recording_id": rec.id,
        "sensitivity": req.sensitivity,
    }

@router.patch("/{moment_id}", response_model=DetectedMomentResponse)
def update_moment(
    moment_id: int,
    update: DetectedMomentUpdate,
    db: Session = Depends(get_db)
):
    """Approve, reject, or fine-tune a candidate moment."""
    m = db.query(DetectedMoment).filter(DetectedMoment.id == moment_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Detected moment not found")

    if update.status is not None:
        m.status = update.status
        if update.status == "approved":
            m.is_approved = True
        elif update.status in ["rejected", "detected"]:
            m.is_approved = False

    if update.is_approved is not None:
        m.is_approved = update.is_approved
        m.status = "approved" if update.is_approved else "rejected"

    if update.notes is not None:
        m.notes = update.notes
    if update.event_type is not None and update.event_type in EVENT_DEFINITIONS:
        m.event_type = update.event_type
        m.event_label = EVENT_DEFINITIONS[update.event_type]["label"]
    if update.start_time is not None:
        m.start_time = update.start_time
    if update.end_time is not None:
        m.end_time = update.end_time
    if update.start_time is not None or update.end_time is not None:
        m.duration = round(max(0.1, m.end_time - m.start_time), 2)

    db.commit()
    db.refresh(m)

    feat = None
    if m.visual_features:
        try:
            feat = json.loads(m.visual_features)
        except Exception:
            pass

    return DetectedMomentResponse(
        id=m.id,
        recording_id=m.recording_id,
        event_type=m.event_type,
        event_label=m.event_label,
        start_time=m.start_time,
        end_time=m.end_time,
        duration=m.duration,
        confidence_score=m.confidence_score,
        explanation=m.explanation,
        is_uncertain=m.is_uncertain,
        uncertainty_reason=m.uncertainty_reason,
        thumbnail_path=m.thumbnail_path,
        thumbnail_url=m.thumbnail_url,
        keyframe_timestamp=m.keyframe_timestamp,
        visual_features=feat,
        detection_sensitivity=m.detection_sensitivity,
        status=m.status,
        is_approved=m.is_approved,
        notes=m.notes,
        clip_id=m.clip_id,
        created_at=m.created_at,
        updated_at=m.updated_at,
    )

@router.post("/{moment_id}/convert-to-clip")
def convert_moment_to_clip(moment_id: int, db: Session = Depends(get_db)):
    """
    Convert an approved detected moment into a Clip ready for YouTube Shorts generation.
    Connects Phase 4 detection directly to downstream Clip Creation (Phase 5).
    """
    m = db.query(DetectedMoment).filter(DetectedMoment.id == moment_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Detected moment not found")

    # Map 14 GTA events to MomentType enum where possible
    type_map = {
        "police_chase": MomentType.CHASE,
        "high_speed_driving": MomentType.ACTION,
        "supercar_stunt": MomentType.STUNT,
        "car_crash": MomentType.FAIL,
        "explosion": MomentType.EXPLOSION,
        "shootout": MomentType.ACTION,
        "funny_npc": MomentType.FUNNY,
        "unexpected_gameplay": MomentType.OTHER,
        "cinematic_scene": MomentType.OTHER,
        "nighttime_vice_city": MomentType.OTHER,
        "interesting_weather": MomentType.OTHER,
        "action_sequence": MomentType.ACTION,
        "gameplay_fail": MomentType.FAIL,
        "unusual_visual": MomentType.OTHER,
    }
    m_type = type_map.get(m.event_type, MomentType.OTHER)

    clip = Clip(
        recording_id=m.recording_id,
        title=f"GTA 6 {m.event_label} - Short",
        description=m.explanation,
        moment_type=m_type,
        start_time=m.start_time,
        end_time=m.end_time,
        duration=m.duration,
        thumbnail_path=m.thumbnail_path,
        excitement_score=m.confidence_score,
        ai_tags=f"gta6,{m.event_type},shorts,gameplay",
        status=ClipStatus.DETECTED,
        is_approved=True,
    )
    db.add(clip)
    db.commit()
    db.refresh(clip)

    m.status = "converted"
    m.is_approved = True
    m.clip_id = clip.id
    db.commit()

    return {
        "status": "success",
        "moment_id": m.id,
        "clip_id": clip.id,
        "title": clip.title,
    }

@router.delete("/{moment_id}")
def delete_moment(moment_id: int, db: Session = Depends(get_db)):
    """Delete a detected candidate moment."""
    m = db.query(DetectedMoment).filter(DetectedMoment.id == moment_id).first()
    if not m:
        raise HTTPException(status_code=404, detail="Detected moment not found")
    db.delete(m)
    db.commit()
    return {"status": "deleted", "moment_id": moment_id}

@router.get("/{recording_id}/thumbnails/{filename}")
def get_moment_thumbnail(recording_id: int, filename: str):
    """Serve candidate thumbnail image."""
    safe_name = Path(filename).name
    thumb_path = Path(settings.THUMBNAILS_DIR) / "moments" / f"rec_{recording_id}" / safe_name
    if not thumb_path.is_file():
        raise HTTPException(status_code=404, detail="Moment thumbnail image not found")
    return FileResponse(str(thumb_path), media_type="image/jpeg")
