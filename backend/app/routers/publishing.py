from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.clip import Clip
from ..models.publishing_item import PublishingItem
from ..schemas.publishing import (
    PublishingItemResponse,
    PublishingItemUpdateRequest,
    PublishingMetricsUpdateRequest,
    PublishingWorkspaceSummary,
)
from ..services.publishing_service import publishing_service

router = APIRouter(prefix="/api/publishing", tags=["publishing"])

@router.get("/summary", response_model=PublishingWorkspaceSummary)
def get_publishing_summary(db: Session = Depends(get_db)):
    """Retrieve aggregate performance and publishing status metrics."""
    return publishing_service.get_summary(db)

@router.get("/items", response_model=List[PublishingItemResponse])
def list_publishing_items(
    status: Optional[str] = Query(None, description="Filter by status: draft, ready, scheduled, published, archived"),
    recording_id: Optional[int] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all Publishing Items with optional status and recording filters."""
    # Ensure all approved clips have publishing items
    approved_clips = db.query(Clip).filter(Clip.is_approved == True).all()
    for c in approved_clips:
        publishing_service.get_or_create_publishing_item(db, c.id)

    query = db.query(PublishingItem).join(Clip)
    if status and status != "all":
        query = query.filter(PublishingItem.status == status)
    if recording_id:
        query = query.filter(Clip.recording_id == recording_id)

    items = query.order_by(PublishingItem.updated_at.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return [publishing_service.to_response(item) for item in items]

@router.get("/items/{clip_id}", response_model=PublishingItemResponse)
def get_publishing_item(clip_id: int, db: Session = Depends(get_db)):
    """Get or initialize Publishing Item for a specific Short."""
    try:
        item = publishing_service.get_or_create_publishing_item(db, clip_id)
        return publishing_service.to_response(item)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/items/{clip_id}", response_model=PublishingItemResponse)
def update_publishing_item(
    clip_id: int,
    req: PublishingItemUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update active metadata, draft selection, planned schedule, and checklist for a Short."""
    try:
        item = publishing_service.update_publishing_item(db, clip_id, req)
        return publishing_service.to_response(item)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.put("/items/{clip_id}/metrics", response_model=PublishingItemResponse)
def update_publishing_metrics(
    clip_id: int,
    req: PublishingMetricsUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update manual performance metrics (Views, Likes, Comments, Shares, Watch Time)."""
    try:
        item = publishing_service.update_metrics(db, clip_id, req)
        return publishing_service.to_response(item)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))

@router.post("/items/{clip_id}/sync-analytics", response_model=PublishingItemResponse)
def sync_analytics(clip_id: int, db: Session = Depends(get_db)):
    """Simulate or synchronize YouTube Shorts performance analytics."""
    try:
        item = publishing_service.sync_simulated_analytics(db, clip_id)
        return publishing_service.to_response(item)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
