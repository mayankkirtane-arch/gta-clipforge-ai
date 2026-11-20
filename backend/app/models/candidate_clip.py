from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base

class CandidateClip(Base):
    __tablename__ = "candidate_clips"

    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(Integer, ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False, index=True)
    detected_moment_id = Column(Integer, ForeignKey("detected_moments.id", ondelete="SET NULL"), nullable=True, index=True)
    
    # 8 Specialized Target Categories for YouTube Shorts
    category = Column(String(50), nullable=False, index=True)
    category_label = Column(String(100), nullable=False)
    title = Column(String(500), nullable=False)
    
    # Boundary Optimization (Seconds)
    start_time = Column(Float, nullable=False, index=True)
    end_time = Column(Float, nullable=False, index=True)
    duration = Column(Float, nullable=False, index=True)
    target_length = Column(Integer, nullable=False, default=30)  # 15, 20, 30, 45, 60
    
    climax_time = Column(Float, nullable=False)
    pre_roll_sec = Column(Float, nullable=False, default=2.5)
    post_roll_sec = Column(Float, nullable=False, default=3.0)
    
    # AI Ranking Score: 1 - 100 (Heuristic Estimate)
    ai_score = Column(Integer, nullable=False, index=True)  # 1 - 100
    score_breakdown = Column(Text, nullable=True)  # JSON: visual_excitement, unexpectedness, action_intensity, etc.
    score_reason = Column(Text, nullable=False)    # Detailed heuristic scoring rationale
    
    # Selection & Ranking
    is_selected = Column(Boolean, default=False, nullable=False, index=True)
    selection_rank = Column(Integer, nullable=True, index=True)  # 1, 2, 3... in overall recording ranking
    
    # Visual Assets
    thumbnail_path = Column(String(1000), nullable=True)
    thumbnail_url = Column(String(1000), nullable=True)
    
    # Review & Lifecycle Status
    status = Column(String(50), default="candidate", index=True)  # candidate, selected, approved, rejected, exported
    is_approved = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    recording = relationship("Recording", back_populates="candidate_clips")
    detected_moment = relationship("DetectedMoment", foreign_keys=[detected_moment_id])
