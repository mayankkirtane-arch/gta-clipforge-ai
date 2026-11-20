from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field

class RiskCheckItem(BaseModel):
    id: str
    number: int
    title: str
    category: str  # creator_rights, publisher_policy, audio_copyright, platform_monetization
    risk_level: str  # LOW, MEDIUM, HIGH, UNKNOWN
    summary: str
    details: str
    recommendation: str
    policy_url: Optional[str] = None
    last_checked_date: Optional[str] = None

class RecordingPermissionResponse(BaseModel):
    id: int
    recording_id: int
    original_creator: Optional[str] = None
    source_url: Optional[str] = None
    written_permission_evidence: Optional[str] = None
    permission_status: str = "Not Requested"  # Not Requested, Pending, Granted, Rejected, Expired
    editing_permission: bool = False
    redistribution_permission: bool = False
    commercial_monetization_permission: bool = False
    permission_expiry_date: Optional[datetime] = None
    is_expired: bool = False
    
    overall_risk_level: str = "UNKNOWN"  # LOW, MEDIUM, HIGH, UNKNOWN
    can_export: bool = False
    export_block_reason: Optional[str] = None
    risk_checks: List[RiskCheckItem] = []
    
    manual_review_status: str = "pending_review"  # pending_review, approved_by_user, rejected_by_user, not_required
    manual_review_notes: Optional[str] = None
    reviewer_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    disclaimer_acknowledged: bool = False
    
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class RecordingPermissionUpdateRequest(BaseModel):
    original_creator: Optional[str] = None
    source_url: Optional[str] = None
    written_permission_evidence: Optional[str] = None
    permission_status: Optional[str] = None  # Not Requested, Pending, Granted, Rejected, Expired
    editing_permission: Optional[bool] = None
    redistribution_permission: Optional[bool] = None
    commercial_monetization_permission: Optional[bool] = None
    permission_expiry_date: Optional[datetime] = None
    clear_expiry: Optional[bool] = False
    disclaimer_acknowledged: Optional[bool] = None

class ManualReviewRequest(BaseModel):
    status: str  # approved_by_user, rejected_by_user
    notes: str
    reviewer_name: Optional[str] = "Editor"

class OfficialPolicyInfo(BaseModel):
    id: str
    name: str
    publisher_or_platform: str
    policy_url: str
    last_checked_date: str
    key_rules: List[str]
    commercial_use_stance: str
    legal_distinction_notes: str
