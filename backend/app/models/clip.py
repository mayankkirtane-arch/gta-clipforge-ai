from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Enum as SAEnum, Text, ForeignKey, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
import enum

class ClipStatus(str, enum.Enum):
    DETECTED = "detected"
    GENERATING = "generating"
    GENERATED = "generated"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPORTED = "exported"
    FAILED = "failed"

class MomentType(str, enum.Enum):
    ACTION = "action"
    CHASE = "chase"
    EXPLOSION = "explosion"
    STUNT = "stunt"
    MISSION_COMPLETE = "mission_complete"
    FAIL = "fail"
    FUNNY = "funny"
    OTHER = "other"

class Clip(Base):
    __tablename__ = "clips"
    
    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(Integer, ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_clip_id = Column(Integer, ForeignKey("candidate_clips.id", ondelete="SET NULL"), nullable=True, index=True)
    detected_moment_id = Column(Integer, ForeignKey("detected_moments.id", ondelete="SET NULL"), nullable=True, index=True)
    
    title = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    moment_type = Column(SAEnum(MomentType), default=MomentType.OTHER)
    
    # Timing & Boundaries
    start_time = Column(Float, nullable=True)
    end_time = Column(Float, nullable=True)
    duration = Column(Float, nullable=True)
    
    # 9:16 Shorts Specifications
    resolution = Column(String(50), default="1080x1920", nullable=False)
    aspect_ratio = Column(String(20), default="9:16", nullable=False)
    fps = Column(Integer, default=60, nullable=False)
    video_codec = Column(String(50), default="h264", nullable=False)
    audio_codec = Column(String(50), default="aac", nullable=False)
    render_mode = Column(String(50), default="blurred_background", nullable=False)  # blurred_background, smart_crop, action_hybrid
    
    # Subtitles & Captions
    has_subtitles = Column(Boolean, default=False, nullable=False)
    subtitle_text = Column(String(500), nullable=True)
    subtitle_style = Column(String(50), default="vice_neon", nullable=True)

    # Phase 7: Cinematic Editing & Presets
    edit_mode = Column(String(50), default="raw", nullable=False)  # "raw" or "cinematic"
    preset_name = Column(String(100), nullable=True)  # BADASS CINEMATIC, POLICE CHASE, etc.
    zoom_intensity = Column(Float, default=1.0, nullable=False)
    slowmo_speed = Column(Float, default=1.0, nullable=False)
    color_grading_intensity = Column(Float, default=1.0, nullable=False)
    audio_volume = Column(Float, default=1.0, nullable=False)
    music_volume = Column(Float, default=0.0, nullable=False)
    music_track_id = Column(String(100), nullable=True)
    sfx_track_id = Column(String(100), nullable=True)
    transition_duration = Column(Float, default=0.35, nullable=False)
    effects_applied = Column(Text, nullable=True)
    
    # Asset paths & streaming URLs
    clip_path = Column(String(1000), nullable=True)
    stream_url = Column(String(1000), nullable=True)
    thumbnail_path = Column(String(1000), nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)
    file_size_bytes = Column(BigInteger, nullable=True)
    
    # Scoring & Status
    excitement_score = Column(Float, nullable=True)
    ai_tags = Column(Text, nullable=True)
    status = Column(SAEnum(ClipStatus), default=ClipStatus.DETECTED, index=True)
    is_approved = Column(Boolean, default=False, index=True)
    error_message = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    recording = relationship("Recording", back_populates="clips")
    candidate_clip = relationship("CandidateClip", foreign_keys=[candidate_clip_id])
    detected_moment = relationship("DetectedMoment", foreign_keys=[detected_moment_id])
