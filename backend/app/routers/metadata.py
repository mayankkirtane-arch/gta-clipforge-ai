import json
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.clip import Clip
from ..models.clip_metadata import ClipMetadata
from ..schemas.metadata import (
    ClipMetadataResponse,
    ClipMetadataUpdateRequest,
    ClipMetadataGenerateRequest,
    BatchMetadataGenerateRequest,
    YouTubeShortsPublishPayload,
)
from ..services.metadata_generator import metadata_generator

router = APIRouter(prefix="/api/metadata", tags=["metadata"])

def _to_response_schema(meta: ClipMetadata) -> ClipMetadataResponse:
    """Helper to deserialize JSON suggestion strings to lists."""
    return ClipMetadataResponse(
        id=meta.id,
        clip_id=meta.clip_id,
        title=meta.title,
        description=meta.description,
        hook=meta.hook,
        hashtags=meta.hashtags,
        thumbnail_text=meta.thumbnail_text,
        pinned_comment=meta.pinned_comment,
        title_suggestions=json.loads(meta.title_suggestions) if meta.title_suggestions else [],
        hook_suggestions=json.loads(meta.hook_suggestions) if meta.hook_suggestions else [],
        hashtag_suggestions=json.loads(meta.hashtag_suggestions) if meta.hashtag_suggestions else [],
        thumbnail_text_suggestions=json.loads(meta.thumbnail_text_suggestions) if meta.thumbnail_text_suggestions else [],
        pinned_comment_suggestions=json.loads(meta.pinned_comment_suggestions) if meta.pinned_comment_suggestions else [],
        generation_context=json.loads(meta.generation_context) if meta.generation_context else None,
        is_user_edited=meta.is_user_edited,
        created_at=meta.created_at,
        updated_at=meta.updated_at,
    )

@router.get("/clips/{clip_id}", response_model=ClipMetadataResponse)
def get_clip_metadata(clip_id: int, auto_generate: bool = True, db: Session = Depends(get_db)):
    """
    Get YouTube Shorts metadata for a clip.
    If none exists and auto_generate=True, generates it automatically.
    """
    meta = db.query(ClipMetadata).filter(ClipMetadata.clip_id == clip_id).first()
    if not meta:
        if auto_generate:
            clip = db.query(Clip).filter(Clip.id == clip_id).first()
            if not clip:
                raise HTTPException(status_code=404, detail=f"Clip #{clip_id} not found")
            meta = metadata_generator.generate_metadata_for_clip(db, clip_id)
        else:
            raise HTTPException(status_code=404, detail="Metadata not found for clip")

    return _to_response_schema(meta)

@router.post("/clips/{clip_id}/generate", response_model=ClipMetadataResponse)
def generate_clip_metadata(
    clip_id: int,
    req: ClipMetadataGenerateRequest,
    db: Session = Depends(get_db)
):
    """
    Generate or regenerate AI YouTube Shorts metadata for a clip.
    Produces 5 titles, 3 hooks, description, relevant hashtags, thumbnail text, and pinned comment.
    """
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail=f"Clip #{clip_id} not found")

    meta = metadata_generator.generate_metadata_for_clip(
        db=db,
        clip_id=clip_id,
        tone=req.tone or "viral",
        focus_keyword=req.focus_keyword,
        overwrite=req.overwrite if req.overwrite is not None else True,
    )
    return _to_response_schema(meta)

@router.put("/clips/{clip_id}", response_model=ClipMetadataResponse)
def update_clip_metadata(
    clip_id: int,
    req: ClipMetadataUpdateRequest,
    db: Session = Depends(get_db)
):
    """
    Manually edit YouTube Shorts metadata (title, description, hook, hashtags, thumbnail text, pinned comment).
    Saves and persists directly in SQLite.
    """
    clip = db.query(Clip).filter(Clip.id == clip_id).first()
    if not clip:
        raise HTTPException(status_code=404, detail=f"Clip #{clip_id} not found")

    meta = metadata_generator.update_metadata(
        db=db,
        clip_id=clip_id,
        title=req.title,
        description=req.description,
        hook=req.hook,
        hashtags=req.hashtags,
        thumbnail_text=req.thumbnail_text,
        pinned_comment=req.pinned_comment,
    )
    return _to_response_schema(meta)

@router.post("/batch-generate")
def batch_generate_metadata(req: BatchMetadataGenerateRequest, db: Session = Depends(get_db)):
    """
    Batch generate AI YouTube Shorts metadata across multiple clips or all clips of a recording.
    """
    query = db.query(Clip)
    if req.clip_ids:
        query = query.filter(Clip.id.in_(req.clip_ids))
    elif req.recording_id:
        query = query.filter(Clip.recording_id == req.recording_id)
    else:
        # Default to all generated or approved clips
        query = query.filter(Clip.status.in_(["generated", "approved"]))

    clips = query.all()
    generated_count = 0
    results = []

    for c in clips:
        meta = metadata_generator.generate_metadata_for_clip(
            db=db,
            clip_id=c.id,
            overwrite=req.overwrite_existing if req.overwrite_existing is not None else False
        )
        generated_count += 1
        results.append({
            "clip_id": c.id,
            "title": meta.title,
            "hashtags": meta.hashtags,
        })

    return {
        "status": "completed",
        "total_requested": len(clips),
        "generated_count": generated_count,
        "items": results,
    }

@router.get("/clips/{clip_id}/export-payload", response_model=YouTubeShortsPublishPayload)
def get_youtube_publish_payload(clip_id: int, db: Session = Depends(get_db)):
    """
    Returns ready-to-publish YouTube Shorts Data API v3 payload with character limits and validation checks.
    """
    try:
        payload = metadata_generator.build_youtube_publish_payload(db, clip_id)
        return payload
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
