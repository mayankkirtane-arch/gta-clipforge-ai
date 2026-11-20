import os
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc, asc, func

from ..database import get_db, SessionLocal
from ..config import settings
from ..models.recording import Recording
from ..models.candidate_clip import CandidateClip
from ..models.clip import Clip, ClipStatus, MomentType
from ..models.job import Job, JobStatus, JobType
from ..schemas.candidate_clip import (
    CandidateClipResponse,
    CandidateClipUpdate,
    ClipRankingTriggerRequest,
    ClipBatchSelectRequest,
    CandidateClipListResponse,
    CandidateClipSummary,
)
from ..services.clip_ranker import clip_ranker, CLIP_CATEGORIES, TARGET_LENGTHS

router = APIRouter(prefix="/api/candidate-clips", tags=["candidate-clips"])

@router.get("/categories")
def get_clip_categories():
    """Return the 8 target YouTube Shorts categories with metadata."""
    return [
        {
            "id": k,
            "label": v["label"],
            "description": v["description"],
            "color": v["color"],
            "icon": v["icon"],
        }
        for k, v in CLIP_CATEGORIES.items()
    ]

@router.get("/target-lengths")
def get_target_lengths():
    """Return standard YouTube Shorts target durations (15s, 20s, 30s, 45s, 60s)."""
    return TARGET_LENGTHS

@router.get("", response_model=CandidateClipListResponse)
def list_candidate_clips(
    recording_id: Optional[int] = Query(None),
    category: Optional[str] = Query(None),
    target_length: Optional[int] = Query(None),
    is_selected: Optional[bool] = Query(None),
    status: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None),
    sort_by: str = Query("score", description="score, category, duration, timestamp"),
    sort_order: str = Query("desc", description="asc or desc"),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List ranked candidate clips with sorting, filtering, and summary statistics."""
    query = db.query(CandidateClip)

    if recording_id is not None:
        query = query.filter(CandidateClip.recording_id == recording_id)
    if category and category != "all":
        query = query.filter(CandidateClip.category == category)
    if target_length is not None and target_length > 0:
        query = query.filter(CandidateClip.target_length == target_length)
    if is_selected is not None:
        query = query.filter(CandidateClip.is_selected == is_selected)
    if status and status != "all":
        query = query.filter(CandidateClip.status == status)
    if min_score is not None:
        query = query.filter(CandidateClip.ai_score >= min_score)

    # Dynamic sorting
    if sort_by == "score":
        order_col = CandidateClip.ai_score
    elif sort_by == "category":
        order_col = CandidateClip.category
    elif sort_by == "duration":
        order_col = CandidateClip.duration
    elif sort_by == "timestamp":
        order_col = CandidateClip.start_time
    else:
        order_col = CandidateClip.ai_score

    if sort_order == "asc":
        query = query.order_by(asc(order_col), asc(CandidateClip.start_time))
    else:
        query = query.order_by(desc(order_col), asc(CandidateClip.start_time))

    total = query.count()
    clips = query.offset((page - 1) * page_size).limit(page_size).all()

    # Calculate summary metrics for the recording scope
    base_summary_q = db.query(CandidateClip)
    if recording_id is not None:
        base_summary_q = base_summary_q.filter(CandidateClip.recording_id == recording_id)

    total_candidates = base_summary_q.count()
    selected_count = base_summary_q.filter(CandidateClip.is_selected == True).count()
    approved_count = base_summary_q.filter(CandidateClip.is_approved == True).count()

    top_item = base_summary_q.order_by(desc(CandidateClip.ai_score)).first()
    top_score = top_item.ai_score if top_item else 0

    cat_rows = (
        db.query(CandidateClip.category, func.count(CandidateClip.id))
        .filter(CandidateClip.recording_id == recording_id if recording_id else True)
        .group_by(CandidateClip.category)
        .all()
    )
    category_counts = {r[0]: r[1] for r in cat_rows}

    dur_rows = (
        db.query(CandidateClip.target_length, func.count(CandidateClip.id))
        .filter(CandidateClip.recording_id == recording_id if recording_id else True)
        .group_by(CandidateClip.target_length)
        .all()
    )
    duration_counts = {int(r[0]): r[1] for r in dur_rows}

    items = []
    for c in clips:
        breakdown = None
        if c.score_breakdown:
            try:
                breakdown = json.loads(c.score_breakdown)
            except Exception:
                pass

        items.append(
            CandidateClipResponse(
                id=c.id,
                recording_id=c.recording_id,
                detected_moment_id=c.detected_moment_id,
                category=c.category,
                category_label=c.category_label,
                title=c.title,
                start_time=c.start_time,
                end_time=c.end_time,
                duration=c.duration,
                target_length=c.target_length,
                climax_time=c.climax_time,
                pre_roll_sec=c.pre_roll_sec,
                post_roll_sec=c.post_roll_sec,
                ai_score=c.ai_score,
                score_breakdown=breakdown,
                score_reason=c.score_reason,
                is_selected=c.is_selected,
                selection_rank=c.selection_rank,
                thumbnail_path=c.thumbnail_path,
                thumbnail_url=c.thumbnail_url,
                status=c.status,
                is_approved=c.is_approved,
                notes=c.notes,
                created_at=c.created_at,
                updated_at=c.updated_at,
            )
        )

    return CandidateClipListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        summary=CandidateClipSummary(
            total_candidates=total_candidates,
            selected_count=selected_count,
            approved_count=approved_count,
            top_score=top_score,
            category_counts=category_counts,
            duration_counts=duration_counts,
        ),
    )

@router.post("/recordings/{recording_id}/rank")
def trigger_clip_ranking(
    recording_id: int,
    req: ClipRankingTriggerRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    """
    Execute AI Clip Ranking and Intelligent Boundary Optimization for a recording.
    Ranks clips from 1 to 100 based on 9 heuristic factors across target durations (15s, 20s, 30s, 45s, 60s).
    """
    rec = db.query(Recording).filter(Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail="Recording not found")

    job = Job(
        recording_id=rec.id,
        job_type=JobType.CLIP_RANKING,
        status=JobStatus.PROCESSING,
        progress=5.0,
        message="Starting AI Clip Ranking & Boundary Optimization...",
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    def run_ranking_task(job_id: int, recording_id: int, options: ClipRankingTriggerRequest):
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

            results = clip_ranker.generate_ranked_candidates(
                recording_id=recording_id,
                target_lengths=options.target_lengths,
                categories=options.categories,
                min_score=options.min_score or 1,
                progress_cb=progress_callback,
            )

            j = task_db.query(Job).filter(Job.id == job_id).first()
            if j:
                j.status = JobStatus.COMPLETED
                j.progress = 100.0
                j.message = f"Ranked {len(results)} candidate clips. Pre-selected top 10."
                j.completed_at = func.now()
                task_db.commit()

        except Exception as e:
            try:
                j = task_db.query(Job).filter(Job.id == job_id).first()
                if j:
                    j.status = JobStatus.FAILED
                    j.error = str(e)
                    j.message = f"Ranking failed: {e}"
                    task_db.commit()
            except Exception:
                pass
        finally:
            task_db.close()

    background_tasks.add_task(run_ranking_task, job.id, rec.id, req)

    return {
        "status": "started",
        "job_id": job.id,
        "recording_id": rec.id,
    }

@router.post("/select")
def batch_select_clips(req: ClipBatchSelectRequest, db: Session = Depends(get_db)):
    """
    Batch select candidate clips: select top 5, 10, 15, 20 or custom list of IDs.
    Persists selection directly to SQLite.
    """
    selected_ids = clip_ranker.batch_select_clips(
        recording_id=req.recording_id,
        select_top_n=req.select_top_n,
        selected_ids=req.selected_ids,
        deselect_all=req.deselect_all,
    )
    return {
        "status": "success",
        "recording_id": req.recording_id,
        "selected_count": len(selected_ids),
        "selected_ids": selected_ids,
    }

@router.patch("/{clip_id}", response_model=CandidateClipResponse)
def update_candidate_clip(
    clip_id: int,
    update: CandidateClipUpdate,
    db: Session = Depends(get_db),
):
    """Toggle selection, approval, or fine-tune candidate boundaries."""
    c = db.query(CandidateClip).filter(CandidateClip.id == clip_id).first()
    if not c:
        raise HTTPException(status_code=404, detail="Candidate clip not found")

    if update.is_selected is not None:
        c.is_selected = update.is_selected
    if update.is_approved is not None:
        c.is_approved = update.is_approved
        c.status = "approved" if update.is_approved else "candidate"
    if update.status is not None:
        c.status = update.status
    if update.notes is not None:
        c.notes = update.notes
    if update.start_time is not None:
        c.start_time = update.start_time
    if update.end_time is not None:
        c.end_time = update.end_time
    if update.start_time is not None or update.end_time is not None:
        c.duration = round(max(0.1, c.end_time - c.start_time), 2)

    db.commit()
    db.refresh(c)

    breakdown = None
    if c.score_breakdown:
        try:
            breakdown = json.loads(c.score_breakdown)
        except Exception:
            pass

    return CandidateClipResponse(
        id=c.id,
        recording_id=c.recording_id,
        detected_moment_id=c.detected_moment_id,
        category=c.category,
        category_label=c.category_label,
        title=c.title,
        start_time=c.start_time,
        end_time=c.end_time,
        duration=c.duration,
        target_length=c.target_length,
        climax_time=c.climax_time,
        pre_roll_sec=c.pre_roll_sec,
        post_roll_sec=c.post_roll_sec,
        ai_score=c.ai_score,
        score_breakdown=breakdown,
        score_reason=c.score_reason,
        is_selected=c.is_selected,
        selection_rank=c.selection_rank,
        thumbnail_path=c.thumbnail_path,
        thumbnail_url=c.thumbnail_url,
        status=c.status,
        is_approved=c.is_approved,
        notes=c.notes,
        created_at=c.created_at,
        updated_at=c.updated_at,
    )

@router.post("/recordings/{recording_id}/batch-approve")
def batch_approve_selected(recording_id: int, db: Session = Depends(get_db)):
    """Approve all currently selected candidate clips."""
    selected_clips = (
        db.query(CandidateClip)
        .filter(CandidateClip.recording_id == recording_id, CandidateClip.is_selected == True)
        .all()
    )
    for c in selected_clips:
        c.is_approved = True
        c.status = "approved"
    db.commit()
    return {"status": "success", "approved_count": len(selected_clips)}

@router.post("/recordings/{recording_id}/export-selected")
def export_selected_to_clips(recording_id: int, db: Session = Depends(get_db)):
    """
    Convert all selected candidate clips into primary Clip records for YouTube Shorts generation.
    Connects Phase 5 selection to downstream export pipelines.
    """
    selected_clips = (
        db.query(CandidateClip)
        .filter(CandidateClip.recording_id == recording_id, CandidateClip.is_selected == True)
        .all()
    )

    created_clips = []
    for c in selected_clips:
        # Map category to MomentType enum
        cat_map = {
            "badass_moments": MomentType.ACTION,
            "police_chase": MomentType.CHASE,
            "car_stunts": MomentType.STUNT,
            "explosions": MomentType.EXPLOSION,
            "funny_npc": MomentType.FUNNY,
            "shootouts": MomentType.ACTION,
            "cinematic_scenes": MomentType.OTHER,
            "unexpected_events": MomentType.OTHER,
        }
        m_type = cat_map.get(c.category, MomentType.OTHER)

        clip = Clip(
            recording_id=c.recording_id,
            candidate_clip_id=c.id,
            detected_moment_id=c.detected_moment_id,
            title=c.title,
            description=c.score_reason,
            moment_type=m_type,
            start_time=c.start_time,
            end_time=c.end_time,
            duration=c.duration,
            resolution="1080x1920",
            aspect_ratio="9:16",
            fps=60,
            video_codec="h264",
            audio_codec="aac",
            render_mode="blurred_background",
            thumbnail_path=c.thumbnail_path,
            excitement_score=float(c.ai_score),
            ai_tags=f"gta6,{c.category},shorts,{c.target_length}s",
            status=ClipStatus.GENERATING,
            is_approved=True,
        )
        db.add(clip)
        c.status = "exported"
        created_clips.append(clip)

    # Queue real Phase 6 YouTube Shorts generation job
    job = None
    if created_clips:
        job = Job(
            recording_id=recording_id,
            job_type=JobType.CLIP_GENERATION,
            status=JobStatus.PENDING,
            progress=0.0,
            message=f"Queued generation of {len(created_clips)} 9:16 YouTube Shorts in GTA6_SHORTS",
        )
        db.add(job)

    db.commit()

    return {
        "status": "success",
        "exported_count": len(created_clips),
        "recording_id": recording_id,
        "job_id": job.id if job else None,
    }

@router.get("/{recording_id}/thumbnails/{filename}")
def get_candidate_thumbnail(recording_id: int, filename: str):
    """Serve representative candidate thumbnail image."""
    safe_name = Path(filename).name
    thumb_path = Path(settings.THUMBNAILS_DIR) / "candidates" / f"rec_{recording_id}" / safe_name
    if not thumb_path.is_file():
        raise HTTPException(status_code=404, detail="Candidate thumbnail not found")
    return FileResponse(str(thumb_path), media_type="image/jpeg")
