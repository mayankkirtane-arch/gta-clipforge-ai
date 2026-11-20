import enum
from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
from ..database import Base

class PublishingStatusEnum(str, enum.Enum):
    DRAFT = "draft"
    READY = "ready"
    SCHEDULED = "scheduled"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class PublishingItem(Base):
    __tablename__ = "publishing_items"
    
    id = Column(Integer, primary_key=True, index=True)
    clip_id = Column(Integer, ForeignKey("clips.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Active Metadata & Draft Options
    active_title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    hashtags = Column(Text, nullable=False)
    hook = Column(String(500), nullable=True)
    thumbnail_text = Column(String(100), nullable=True)
    pinned_comment = Column(Text, nullable=True)
    
    # Draft Title Options (JSON array)
    draft_titles_json = Column(Text, nullable=True)
    
    # Publishing Status & Scheduling
    status = Column(String(50), default="draft", nullable=False)  # draft, ready, scheduled, published, archived
    planned_publish_date = Column(DateTime(timezone=True), nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    youtube_video_id = Column(String(100), nullable=True)
    youtube_video_url = Column(String(255), nullable=True)
    
    # Publishing Checklist (JSON dictionary of boolean verification checks)
    checklist_json = Column(Text, nullable=True)
    
    # Manual Performance Metrics
    views_count = Column(Integer, default=0, nullable=False)
    likes_count = Column(Integer, default=0, nullable=False)
    comments_count = Column(Integer, default=0, nullable=False)
    shares_count = Column(Integer, default=0, nullable=False)
    watch_time_hours = Column(Float, default=0.0, nullable=False)
    avg_view_duration_pct = Column(Float, default=0.0, nullable=False)
    
    # YouTube Analytics Integration
    analytics_source = Column(String(50), default="manual", nullable=False)  # manual, youtube_api, simulated
    last_analytics_sync = Column(DateTime(timezone=True), nullable=True)
    notes = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to parent Clip
    clip = relationship("Clip", backref=backref("publishing_entry", uselist=False, cascade="all, delete-orphan"))
