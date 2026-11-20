from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class ClipMetadataResponse(BaseModel):
    id: int
    clip_id: int
    title: str
    description: str
    hook: Optional[str] = None
    hashtags: str
    thumbnail_text: Optional[str] = None
    pinned_comment: Optional[str] = None
    
    title_suggestions: List[str]
    hook_suggestions: List[str]
    hashtag_suggestions: List[str]
    thumbnail_text_suggestions: List[str]
    pinned_comment_suggestions: List[str]
    
    generation_context: Optional[Dict[str, Any]] = None
    is_user_edited: bool = False
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class ClipMetadataUpdateRequest(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    hook: Optional[str] = None
    hashtags: Optional[str] = None
    thumbnail_text: Optional[str] = None
    pinned_comment: Optional[str] = None

class ClipMetadataGenerateRequest(BaseModel):
    tone: Optional[str] = "viral"  # viral, cinematic, humorous, dramatic
    focus_keyword: Optional[str] = None
    overwrite: Optional[bool] = True

class BatchMetadataGenerateRequest(BaseModel):
    clip_ids: Optional[List[int]] = None
    recording_id: Optional[int] = None
    overwrite_existing: Optional[bool] = False

class YouTubeShortsPublishPayload(BaseModel):
    clip_id: int
    title: str
    description: str
    tags: List[str]
    privacy_status: str = "public"
    made_for_kids: bool = False
    category_id: str = "20"  # YouTube Category 20 is "Gaming"
    pinned_comment: Optional[str] = None
    thumbnail_text: Optional[str] = None
    opening_hook: Optional[str] = None
    video_path: Optional[str] = None
    resolution: str = "1080x1920"
    aspect_ratio: str = "9:16"
    duration_seconds: Optional[float] = None
    char_count_title: int
    char_count_description: int
    is_valid_for_youtube: bool
    validation_warnings: List[str] = []
