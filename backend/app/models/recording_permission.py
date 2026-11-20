from sqlalchemy import Column, Integer, String, Text, ForeignKey, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
from ..database import Base

class PermissionStatusEnum:
    NOT_REQUESTED = "Not Requested"
    PENDING = "Pending"
    GRANTED = "Granted"
    REJECTED = "Rejected"
    EXPIRED = "Expired"

class RiskLevelEnum:
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"

class RecordingPermission(Base):
    __tablename__ = "recording_permissions"
    
    id = Column(Integer, primary_key=True, index=True)
    recording_id = Column(Integer, ForeignKey("recordings.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    
    # Permission Metadata
    original_creator = Column(String(255), nullable=True)  # Name / Handle / Channel
    source_url = Column(String(1000), nullable=True)       # YouTube/Twitch/Kick/Drive source URL
    written_permission_evidence = Column(Text, nullable=True) # Text quote, email, DM, license link
    permission_status = Column(String(50), default="Not Requested", nullable=False) # Not Requested, Pending, Granted, Rejected, Expired
    
    # Specific Scope Permissions
    editing_permission = Column(Boolean, default=False, nullable=False)
    redistribution_permission = Column(Boolean, default=False, nullable=False)
    commercial_monetization_permission = Column(Boolean, default=False, nullable=False)
    permission_expiry_date = Column(DateTime(timezone=True), nullable=True) # None = Perpetual
    
    # 9 Risk Checks & Overall Classification
    overall_risk_level = Column(String(50), default="UNKNOWN", nullable=False) # LOW, MEDIUM, HIGH, UNKNOWN
    can_export = Column(Boolean, default=False, nullable=False)
    export_block_reason = Column(Text, nullable=True)
    risk_checks_json = Column(Text, nullable=True) # JSON containing structured results for the 9 checks
    
    # Manual Review Override for Uncertain Cases
    manual_review_status = Column(String(50), default="pending_review", nullable=False) # pending_review, approved_by_user, rejected_by_user, not_required
    manual_review_notes = Column(Text, nullable=True)
    reviewer_name = Column(String(100), nullable=True)
    reviewed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Legal Disclaimer Acknowledgement
    disclaimer_acknowledged = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationship to Recording
    recording = relationship("Recording", backref=backref("permission_entry", uselist=False, cascade="all, delete-orphan"))
