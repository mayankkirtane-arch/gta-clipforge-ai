from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class PublishingChecklist(BaseModel):
    aspect_ratio_verified: bool = False
    resolution_1080x1920: bool = False
    audio_normalized: bool = False
    copyright_cleared: bool = False
    thumbnail_ready: bool = False
    hook_configured: bool = False
    title_under_100_chars: bool = False
    description_with_tags: bool = False
    user_approved: bool = False

class PerformanceMetrics(BaseModel):
    views_count: int = 0
    likes_count: int = 0
    comments_count: int = 0
    shares_count: int = 0
    watch_time_hours: float = 0.0
    avg_view_duration_pct: float = 0.0
    ctr_pct: Optional[float] = 0.0

class PublishingItemResponse(BaseModel):
    id: int
    clip_id: int
    recording_id: Optional[int] = None
    
    active_title: str
    description: str
    hashtags: str
    hook: Optional[str] = None
    thumbnail_text: Optional[str] = None
    pinned_comment: Optional[str] = None
    draft_titles: List[str] = []
    
    status: str = "draft"  # draft, ready, scheduled, published, archived
    planned_publish_date: Optional[datetime] = None
    published_at: Optional[datetime] = None
    youtube_video_id: Optional[str] = None
    youtube_video_url: Optional[str] = None
    
    checklist: Dict[str, bool] = {}
    checklist_completion_pct: float = 0.0
    
    metrics: PerformanceMetrics
    analytics_source: str = "manual"
    last_analytics_sync: Optional[datetime] = None
    notes: Optional[str] = None
    
    # Clip presentation helpers
    duration: Optional[float] = None
    preset_name: Optional[str] = None
    thumbnail_url: Optional[str] = None
    clip_download_url: Optional[str] = None
    srt_download_url: Optional[str] = None
    txt_download_url: Optional[str] = None
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class PublishingItemUpdateRequest(BaseModel):
    active_title: Optional[str] = None
    description: Optional[str] = None
    hashtags: Optional[str] = None
    hook: Optional[str] = None
    thumbnail_text: Optional[str] = None
    pinned_comment: Optional[str] = None
    status: Optional[str] = None
    planned_publish_date: Optional[datetime] = None
    youtube_video_id: Optional[str] = None
    youtube_video_url: Optional[str] = None
    checklist_updates: Optional[Dict[str, bool]] = None
    notes: Optional[str] = None

class PublishingMetricsUpdateRequest(BaseModel):
    views_count: Optional[int] = None
    likes_count: Optional[int] = None
    comments_count: Optional[int] = None
    shares_count: Optional[int] = None
    watch_time_hours: Optional[float] = None
    avg_view_duration_pct: Optional[float] = None
    analytics_source: Optional[str] = "manual"

class PublishingWorkspaceSummary(BaseModel):
    total_items: int = 0
    draft_count: int = 0
    ready_count: int = 0
    scheduled_count: int = 0
    published_count: int = 0
    archived_count: int = 0
    total_views: int = 0
    total_likes: int = 0
    total_watch_hours: float = 0.0
    avg_performance_ctr: float = 0.0

class ExportPackageRequest(BaseModel):
    clip_ids: Optional[List[int]] = None
    include_subtitles_srt: bool = True
    include_transcripts_txt: bool = True
    include_metadata_csv: bool = True
    include_copyright_reports: bool = True
    include_thumbnails: bool = True
    package_name: Optional[str] = None

class ExportPackageResponse(BaseModel):
    status: str
    zip_filename: str
    zip_path: str
    zip_size_bytes: int
    zip_download_url: str
    clips_exported_count: int
    files_included: List[str] = []
