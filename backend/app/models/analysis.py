from sqlalchemy import Column, Integer, BigInteger, String, Float, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from ..database import Base

class RecordingAnalysis(Base):
    __tablename__ = "recording_analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(Integer, ForeignKey("recordings.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    status = Column(String(50), default="pending", nullable=False)  # pending, processing, completed, failed
    progress = Column(Float, default=0.0)
    current_chunk = Column(Integer, default=0)
    total_chunks = Column(Integer, default=0)
    
    # Generated asset paths
    thumbnail_path = Column(String(1000), nullable=True)
    proxy_path = Column(String(1000), nullable=True)
    audio_path = Column(String(1000), nullable=True)
    
    # Metrics
    total_scenes = Column(Integer, default=0)
    total_keyframes = Column(Integer, default=0)
    audio_peaks_count = Column(Integer, default=0)
    black_frames_count = Column(Integer, default=0)
    silence_count = Column(Integer, default=0)
    
    # Serialized data for timeline & waveform
    waveform_data = Column(Text, nullable=True)       # JSON list of normalized amplitudes
    black_frames_data = Column(Text, nullable=True)   # JSON list of {start, end, duration}
    silence_data = Column(Text, nullable=True)        # JSON list of {start, end, duration}
    scenes_data = Column(Text, nullable=True)         # JSON list of {scene_number, start, end, duration}
    
    # Hardware & settings
    gpu_accelerated = Column(Boolean, default=False)
    chunk_duration_sec = Column(Integer, default=300)
    error = Column(Text, nullable=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    recording = relationship("Recording", back_populates="analysis")


class TimelineSegment(Base):
    __tablename__ = "timeline_segments"
    
    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(Integer, ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False, index=True)
    timestamp = Column(Float, nullable=False, index=True)
    timestamp_formatted = Column(String(20), nullable=False)
    scene_number = Column(Integer, default=1, index=True)
    keyframe_path = Column(String(1000), nullable=True)
    
    # Markers
    audio_peak_db = Column(Float, nullable=True)
    is_audio_peak = Column(Boolean, default=False)
    is_scene_change = Column(Boolean, default=False)
    is_black_frame = Column(Boolean, default=False)
    is_silence = Column(Boolean, default=False)
    excitement_score = Column(Float, default=0.0)
    
    chunk_index = Column(Integer, default=0, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    recording = relationship("Recording", back_populates="timeline_segments")


class RecordingChunk(Base):
    """Tracks completed chunks for reliable recovery after interrupted processing."""
    __tablename__ = "recording_chunks"
    
    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(Integer, ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False, index=True)
    chunk_index = Column(Integer, nullable=False, index=True)
    start_time = Column(Float, nullable=False)
    end_time = Column(Float, nullable=False)
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    recording = relationship("Recording", back_populates="chunks")
