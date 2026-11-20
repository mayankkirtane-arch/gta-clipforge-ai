from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Query, status
from pydantic import BaseModel

from ..services.youtube_service import youtube_service

router = APIRouter(prefix="/api/youtube", tags=["youtube"])

class YouTubeUrlRequest(BaseModel):
    url: str

class YouTubeImportRequest(BaseModel):
    url: str
    auto_generate_shorts: bool = True
    notes: Optional[str] = None
    has_permission: bool = False
    creator_name: Optional[str] = None

class YouTubeInfoResponse(BaseModel):
    url: str
    video_id: str
    title: str
    uploader: str
    channel_url: str
    duration_seconds: float
    duration_formatted: str
    thumbnail: str
    view_count: int
    description: str
    resolution: str
    fps: float

class YouTubeTaskResponse(BaseModel):
    task_id: str
    url: str
    title: str
    uploader: str
    thumbnail: str
    duration_seconds: float
    status: str
    progress: float
    downloaded_bytes: int
    total_bytes: int
    speed_str: str
    eta_seconds: int
    message: str
    recording_id: Optional[int] = None
    job_id: Optional[int] = None
    error: Optional[str] = None
    created_at: Optional[str] = None
    completed_at: Optional[str] = None

@router.post("/info", response_model=YouTubeInfoResponse)
def get_youtube_video_info(payload: YouTubeUrlRequest):
    """
    Extract video metadata, thumbnail, title, and channel information from YouTube URL
    without downloading the file. Provides instant preview in UI.
    """
    if not youtube_service.is_valid_youtube_url(payload.url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YouTube URL. Please provide a standard YouTube link, short link (youtu.be), or Shorts link."
        )
    try:
        info = youtube_service.extract_info(payload.url)
        return info
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unable to retrieve YouTube video info: {str(e)}"
        )

@router.post("/import", response_model=YouTubeTaskResponse)
def import_youtube_video(payload: YouTubeImportRequest):
    """
    Start downloading a YouTube video directly into GTA6_RECORDINGS.
    When download completes, automatically creates Recording and kicks off
    AI analysis and Shorts generation pipeline.
    """
    if not youtube_service.is_valid_youtube_url(payload.url):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid YouTube URL. Please provide a valid YouTube video link."
        )
    try:
        task = youtube_service.create_download_task(
            url=payload.url,
            auto_generate_shorts=payload.auto_generate_shorts,
            notes=payload.notes or "",
            has_permission=payload.has_permission,
            creator_name=payload.creator_name,
        )
        return task.to_dict()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initiate YouTube download: {str(e)}"
        )

@router.get("/tasks", response_model=List[YouTubeTaskResponse])
def list_youtube_tasks(limit: int = Query(20, ge=1, le=100)):
    """List recent and active YouTube video download tasks with progress."""
    return youtube_service.list_tasks(limit=limit)

@router.get("/tasks/{task_id}", response_model=YouTubeTaskResponse)
def get_youtube_task_status(task_id: str):
    """Get real-time download and processing progress for a specific task."""
    task = youtube_service.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="YouTube download task not found")
    return task.to_dict()

@router.post("/tasks/{task_id}/cancel")
def cancel_youtube_task(task_id: str):
    """Cancel an active YouTube download."""
    success = youtube_service.cancel_task(task_id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Task could not be cancelled (might not exist or has already completed/failed)."
        )
    return {"status": "cancelled", "task_id": task_id, "message": "Download task successfully cancelled."}
