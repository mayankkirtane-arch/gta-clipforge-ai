from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime
from ..models.recording import RecordingStatus

class RecordingCreate(BaseModel):
    filename: str
    original_filename: str
    file_path: str
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None
    resolution: Optional[str] = None
    fps: Optional[float] = None
    file_hash: Optional[str] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    bitrate: Optional[int] = None
    notes: Optional[str] = None

class RecordingLocalImport(BaseModel):
    file_path: str
    notes: Optional[str] = None

class RecordingResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    file_path: str
    file_size_bytes: Optional[int] = None
    duration_seconds: Optional[float] = None
    resolution: Optional[str] = None
    fps: Optional[float] = None
    file_hash: Optional[str] = None
    video_codec: Optional[str] = None
    audio_codec: Optional[str] = None
    bitrate: Optional[int] = None
    status: RecordingStatus
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

class RecordingList(BaseModel):
    items: List[RecordingResponse]
    total: int
    page: int
    page_size: int
