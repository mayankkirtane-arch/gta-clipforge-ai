from sqlalchemy import Column, Integer, BigInteger, String, Float, DateTime, Enum as SAEnum, Text
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base
import enum

class RecordingStatus(str, enum.Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    FAILED = "failed"

class Recording(Base):
    __tablename__ = "recordings"
    
    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    original_filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    file_size_bytes = Column(BigInteger, nullable=True)
    duration_seconds = Column(Float, nullable=True)
    resolution = Column(String(50), nullable=True)
    fps = Column(Float, nullable=True)
    file_hash = Column(String(64), nullable=True, index=True)
    video_codec = Column(String(50), nullable=True)
    audio_codec = Column(String(50), nullable=True)
    bitrate = Column(BigInteger, nullable=True)
    status = Column(SAEnum(RecordingStatus), default=RecordingStatus.PENDING, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    clips = relationship("Clip", back_populates="recording", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="recording", cascade="all, delete-orphan")
    analysis = relationship("RecordingAnalysis", back_populates="recording", uselist=False, cascade="all, delete-orphan")
    timeline_segments = relationship("TimelineSegment", back_populates="recording", cascade="all, delete-orphan")
    chunks = relationship("RecordingChunk", back_populates="recording", cascade="all, delete-orphan")
    detected_moments = relationship("DetectedMoment", back_populates="recording", cascade="all, delete-orphan")
    candidate_clips = relationship("CandidateClip", back_populates="recording", cascade="all, delete-orphan")
