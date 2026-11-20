from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class ScoreBreakdown(BaseModel):
    visual_excitement: float
    unexpectedness: float
    action_intensity: float
    cinematic_quality: float
    entertainment_value: float
    audio_excitement: float
    event_completeness: float
    boundary_quality: float
    duplicate_penalty: float

class CandidateClipBase(BaseModel):
    category: str
    category_label: str
    title: str
    start_time: float
    end_time: float
    duration: float
    target_length: int
    climax_time: float
    pre_roll_sec: float
    post_roll_sec: float
    ai_score: int
    score_breakdown: Optional[Dict[str, float]] = None
    score_reason: str
    is_selected: bool = False
    selection_rank: Optional[int] = None
    thumbnail_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    status: str = "candidate"
    is_approved: bool = False
    notes: Optional[str] = None

class CandidateClipResponse(CandidateClipBase):
    id: int
    recording_id: int
    detected_moment_id: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CandidateClipUpdate(BaseModel):
    is_selected: Optional[bool] = None
    status: Optional[str] = None
    is_approved: Optional[bool] = None
    notes: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None

class ClipRankingTriggerRequest(BaseModel):
    target_lengths: Optional[List[int]] = [15, 20, 30, 45, 60]
    categories: Optional[List[str]] = None
    min_score: Optional[int] = 1
    force_rerank: bool = False

class ClipBatchSelectRequest(BaseModel):
    recording_id: int
    select_top_n: Optional[int] = None  # 5, 10, 15, 20
    selected_ids: Optional[List[int]] = None
    deselect_all: bool = False

class CandidateClipSummary(BaseModel):
    total_candidates: int
    selected_count: int
    approved_count: int
    top_score: int
    category_counts: Dict[str, int]
    duration_counts: Dict[int, int]

class CandidateClipListResponse(BaseModel):
    items: List[CandidateClipResponse]
    total: int
    page: int
    page_size: int
    summary: Optional[CandidateClipSummary] = None
