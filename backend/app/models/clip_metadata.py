from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
from ..database import Base

class ClipMetadata(Base):
    __tablename__ = "clip_metadata"
    
    id = Column(Integer, primary_key=True, index=True)
    clip_id = Column(Integer, ForeignKey("clips.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Active / Selected metadata for publishing
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    hook = Column(String(500), nullable=True)
    hashtags = Column(Text, nullable=False)
    thumbnail_text = Column(String(100), nullable=True)
    pinned_comment = Column(Text, nullable=True)
    
    # 5 Title Suggestions (JSON array)
    title_suggestions = Column(Text, nullable=False)
    
    # 3 Opening Hook Suggestions (JSON array)
    hook_suggestions = Column(Text, nullable=False)
    
    # Hashtags Suggestions (JSON array)
    hashtag_suggestions = Column(Text, nullable=False)
    
    # Thumbnail Text Suggestions (JSON array)
    thumbnail_text_suggestions = Column(Text, nullable=False)
    
    # Pinned Comment Suggestions (JSON array)
    pinned_comment_suggestions = Column(Text, nullable=False)
    
    # AI Generation context
    generation_context = Column(Text, nullable=True)
    is_user_edited = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to parent Clip
    clip = relationship("Clip", backref=backref("metadata_entry", uselist=False, cascade="all, delete-orphan"))
