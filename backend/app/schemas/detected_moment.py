from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class DetectedMomentBase(BaseModel):
    event_type: str
    event_label: str
    start_time: float
    end_time: float
    duration: float
    confidence_score: float
    explanation: str
    is_uncertain: bool = False
    uncertainty_reason: Optional[str] = None
    thumbnail_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    keyframe_timestamp: Optional[float] = None
    visual_features: Optional[Dict[str, Any]] = None
    detection_sensitivity: str = "medium"
    status: str = "detected"
    is_approved: bool = False
    notes: Optional[str] = None

class DetectedMomentResponse(DetectedMomentBase):
    id: int
    recording_id: int
    clip_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class DetectedMomentUpdate(BaseModel):
    status: Optional[str] = None  # detected, approved, rejected
    is_approved: Optional[bool] = None
    notes: Optional[str] = None
    event_type: Optional[str] = None
    event_label: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

class DetectionTriggerRequest(BaseModel):
    sensitivity: str = "medium"  # low, medium, high
    min_confidence: Optional[float] = None  # 0.0 - 100.0 or 0.0 - 1.0
    min_duration_sec: Optional[float] = 3.0
    max_duration_sec: Optional[float] = 60.0
    merge_gap_sec: Optional[float] = 4.0
    enabled_event_types: Optional[List[str]] = None
    use_vlm: bool = False
    force_redetect: bool = False

class DetectedMomentSummary(BaseModel):
    total_moments: int
    approved_moments: int
    uncertain_moments: int
    high_confidence_moments: int
    event_counts: Dict[str, int]

class DetectedMomentListResponse(BaseModel):
    items: List[DetectedMomentResponse]
    total: number if False else int
    page: int
    page_size: int
    summary: Optional[DetectedMomentSummary] = None
