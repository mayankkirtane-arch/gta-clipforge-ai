from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime
from ..models.clip import ClipStatus, MomentType

class ClipResponse(BaseModel):
    id: int
    recording_id: int
    candidate_clip_id: Optional[int] = None
    detected_moment_id: Optional[int] = None
    title: Optional[str] = None
    description: Optional[str] = None
    moment_type: MomentType
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None
    resolution: Optional[str] = "1080x1920"
    aspect_ratio: Optional[str] = "9:16"
    fps: Optional[int] = 60
    video_codec: Optional[str] = "h264"
    audio_codec: Optional[str] = "aac"
    render_mode: Optional[str] = "blurred_background"
    has_subtitles: bool = False
    subtitle_text: Optional[str] = None
    subtitle_style: Optional[str] = "vice_neon"
    edit_mode: Optional[str] = "raw"
    preset_name: Optional[str] = None
    zoom_intensity: Optional[float] = 1.0
    slowmo_speed: Optional[float] = 1.0
    color_grading_intensity: Optional[float] = 1.0
    audio_volume: Optional[float] = 1.0
    music_volume: Optional[float] = 0.0
    music_track_id: Optional[str] = None
    sfx_track_id: Optional[str] = None
    transition_duration: Optional[float] = 0.35
    effects_applied: Optional[str] = None
    clip_path: Optional[str] = None
    stream_url: Optional[str] = None
    thumbnail_path: Optional[str] = None
    thumbnail_url: Optional[str] = None
    file_size_bytes: Optional[int] = None
    excitement_score: Optional[float] = None
    ai_tags: Optional[str] = None
    status: ClipStatus
    is_approved: bool
    error_message: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    
    model_config = {"from_attributes": True}

class ShortGenerationRequest(BaseModel):
    recording_id: int
    candidate_clip_id: Optional[int] = None
    detected_moment_id: Optional[int] = None
    title: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    target_length: Optional[int] = 30  # 15, 20, 30, 45, 60
    render_mode: Optional[str] = "blurred_background"  # blurred_background, smart_crop, action_hybrid
    subtitles: Optional[bool] = False
    subtitle_text: Optional[str] = None
    subtitle_style: Optional[str] = "vice_neon"
    fps: Optional[int] = None  # None = auto (30 or 60 based on source)
    use_gpu: Optional[bool] = True

class BatchShortGenerationRequest(BaseModel):
    recording_id: int
    candidate_clip_ids: Optional[List[int]] = None  # Specific list or None for all selected/top
    select_top_n: Optional[int] = None  # 5, 10, 15, 20
    target_length: Optional[int] = None  # 15, 20, 30, 45, 60 (or None to keep candidate target_length)
    render_mode: Optional[str] = "blurred_background"
    subtitles: Optional[bool] = False
    subtitle_style: Optional[str] = "vice_neon"
    use_gpu: Optional[bool] = True

class ShortVerificationResult(BaseModel):
    is_valid: bool
    clip_id: int
    file_path: str
    width: int
    height: int
    aspect_ratio: str
    duration: float
    expected_duration: float
    duration_difference: float
    video_codec: str
    audio_codec: str
    fps: float
    file_size_bytes: int
    checks: Dict[str, bool]
    error: Optional[str] = None

# Phase 7: Cinematic Editing Schemas
class CinematicEditRequest(BaseModel):
    recording_id: int
    clip_id: Optional[int] = None
    candidate_clip_id: Optional[int] = None
    title: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    edit_mode: str = "cinematic"  # "raw" or "cinematic"
    preset_name: Optional[str] = "BADASS CINEMATIC"
    render_mode: str = "blurred_background"  # blurred_background, smart_crop, action_hybrid
    target_length: Optional[int] = 30
    zoom_intensity: Optional[float] = 1.0  # 1.0 to 1.5
    slowmo_speed: Optional[float] = 1.0  # 0.25 to 1.0
    color_grading_intensity: Optional[float] = 1.0  # 0.0 to 1.0
    audio_volume: Optional[float] = 1.0  # 0.0 to 2.0
    music_volume: Optional[float] = 0.0  # 0.0 to 1.0
    music_track_id: Optional[str] = None
    sfx_track_id: Optional[str] = None
    transition_duration: Optional[float] = 0.35
    subtitles: Optional[bool] = False
    subtitle_text: Optional[str] = None
    subtitle_style: Optional[str] = "vice_neon"
    fps: Optional[int] = None
    use_gpu: Optional[bool] = True

class CinematicPreviewRequest(BaseModel):
    recording_id: int
    start_time: float
    end_time: float
    edit_mode: str = "cinematic"
    preset_name: Optional[str] = "BADASS CINEMATIC"
    render_mode: str = "blurred_background"
    zoom_intensity: Optional[float] = 1.0
    slowmo_speed: Optional[float] = 1.0
    color_grading_intensity: Optional[float] = 1.0
    audio_volume: Optional[float] = 1.0
    music_volume: Optional[float] = 0.0
    music_track_id: Optional[str] = None
    sfx_track_id: Optional[str] = None
    transition_duration: Optional[float] = 0.35
    preview_duration: Optional[float] = 4.0

class CinematicPresetInfo(BaseModel):
    id: str
    name: str
    description: str
    tagline: str
    icon: str
    color: str
    default_zoom: float
    default_slowmo: float
    color_grade_desc: str
    audio_profile: str
    suggested_music: str
    suggested_sfx: str

class AudioTrackInfo(BaseModel):
    id: str
    title: str
    category: str  # "music" or "sfx"
    genre: str
    duration_seconds: float
    license: str
    copyright_safe: bool
    stream_url: str
