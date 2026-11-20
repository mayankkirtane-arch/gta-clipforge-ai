from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base

class DetectedMoment(Base):
    __tablename__ = "detected_moments"

    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(Integer, ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # 14 GTA 6 Specialized Event Types
    event_type = Column(String(50), nullable=False, index=True)
    event_label = Column(String(100), nullable=False)
    
    # Time boundaries (seconds)
    start_time = Column(Float, nullable=False, index=True)
    end_time = Column(Float, nullable=False, index=True)
    duration = Column(Float, nullable=False)
    
    # AI Vision & Audio Confidence Scoring
    confidence_score = Column(Float, nullable=False, index=True)  # 0.0 - 100.0
    explanation = Column(Text, nullable=False)                    # Multi-modal detection reasoning
    
    # Explicit Uncertainty Labeling
    is_uncertain = Column(Boolean, default=False, nullable=False, index=True)
    uncertainty_reason = Column(Text, nullable=True)
    
    # Visual Assets
    thumbnail_path = Column(String(1000), nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)
    keyframe_timestamp = Column(Float, nullable=True)
    
    # Multi-modal Feature Metadata (JSON string)
    visual_features = Column(Text, nullable=True)  # optical_flow, color_profile, audio_energy, siren_score, etc.
    detection_sensitivity = Column(String(20), default="medium")  # low, medium, high
    
    # Review & Lifecycle Status
    status = Column(String(50), default="detected", index=True)  # detected, approved, rejected, converted
    is_approved = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    
    clip_id = Column(Integer, ForeignKey("clips.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    recording = relationship("Recording", back_populates="detected_moments")
    clip = relationship("Clip", foreign_keys=[clip_id])
