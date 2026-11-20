import json
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.recording import Recording
from ..models.recording_permission import RecordingPermission, PermissionStatusEnum, RiskLevelEnum
from ..schemas.copyright import (
    RiskCheckItem,
    RecordingPermissionResponse,
    RecordingPermissionUpdateRequest,
    ManualReviewRequest,
    OfficialPolicyInfo
)
from ..services.copyright_risk_service import copyright_risk_service

router = APIRouter(prefix="/api/copyright", tags=["copyright"])

def _to_response(perm: RecordingPermission) -> RecordingPermissionResponse:
    checks: List[RiskCheckItem] = []
    if perm.risk_checks_json:
        try:
            raw_checks = json.loads(perm.risk_checks_json)
            checks = [RiskCheckItem(**c) for c in raw_checks]
        except Exception:
            checks = []

    now = datetime.now(timezone.utc)
    is_expired = False
    if perm.permission_expiry_date:
        expiry = perm.permission_expiry_date
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry < now:
            is_expired = True

    return RecordingPermissionResponse(
        id=perm.id,
        recording_id=perm.recording_id,
        original_creator=perm.original_creator,
        source_url=perm.source_url,
        written_permission_evidence=perm.written_permission_evidence,
        permission_status=perm.permission_status,
        editing_permission=perm.editing_permission,
        redistribution_permission=perm.redistribution_permission,
        commercial_monetization_permission=perm.commercial_monetization_permission,
        permission_expiry_date=perm.permission_expiry_date,
        is_expired=is_expired,
        overall_risk_level=perm.overall_risk_level,
        can_export=perm.can_export,
        export_block_reason=perm.export_block_reason,
        risk_checks=checks,
        manual_review_status=perm.manual_review_status,
        manual_review_notes=perm.manual_review_notes,
        reviewer_name=perm.reviewer_name,
        reviewed_at=perm.reviewed_at,
        disclaimer_acknowledged=perm.disclaimer_acknowledged,
        created_at=perm.created_at,
        updated_at=perm.updated_at,
    )

@router.get("/policies", response_model=List[OfficialPolicyInfo])
def get_official_policies():
    """Retrieve verified official publisher & platform copyright policies with last-checked dates."""
    return copyright_risk_service.get_official_policies()

@router.get("/summary")
def get_copyright_summary(db: Session = Depends(get_db)):
    """Retrieve aggregate copyright and permission metrics across all recordings."""
    recordings = db.query(Recording).all()
    total = len(recordings)
    
    status_counts = {
        "not_requested": 0,
        "pending": 0,
        "granted": 0,
        "rejected": 0,
        "expired": 0,
    }
    risk_counts = {
        "low": 0,
        "medium": 0,
        "high": 0,
        "unknown": 0,
    }
    can_export_count = 0
    blocked_count = 0

    for rec in recordings:
        perm = db.query(RecordingPermission).filter(RecordingPermission.recording_id == rec.id).first()
        if not perm:
            status_counts["not_requested"] += 1
            risk_counts["unknown"] += 1
            blocked_count += 1
        else:
            p_status = (perm.permission_status or "Not Requested").lower().replace(" ", "_")
            if p_status in status_counts:
                status_counts[p_status] += 1
            else:
                status_counts["not_requested"] += 1

            r_level = (perm.overall_risk_level or "UNKNOWN").lower()
            if r_level in risk_counts:
                risk_counts[r_level] += 1
            else:
                risk_counts["unknown"] += 1

            if perm.can_export:
                can_export_count += 1
            else:
                blocked_count += 1

    return {
        "total_recordings": total,
        "status_breakdown": status_counts,
        "risk_breakdown": risk_counts,
        "can_export_count": can_export_count,
        "blocked_export_count": blocked_count,
        "last_policy_check": "2026-11-15",
        "legal_notice": "GTA CLIPFORGE AI risk classifications are advisory only and do not constitute legal advice."
    }

@router.get("/recordings/{recording_id}", response_model=RecordingPermissionResponse)
def get_recording_permission(recording_id: int, db: Session = Depends(get_db)):
    """Get permission management data and 9-point risk assessment for a recording."""
    rec = db.query(Recording).filter(Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recording #{recording_id} not found")

    perm = copyright_risk_service.get_or_create_permission(db, recording_id)
    return _to_response(perm)

@router.put("/recordings/{recording_id}", response_model=RecordingPermissionResponse)
def update_recording_permission(
    recording_id: int,
    req: RecordingPermissionUpdateRequest,
    db: Session = Depends(get_db)
):
    """Update permission attributes, evidence, and re-assess risk for a recording."""
    rec = db.query(Recording).filter(Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recording #{recording_id} not found")

    perm = copyright_risk_service.update_permission(
        db=db,
        recording_id=recording_id,
        original_creator=req.original_creator,
        source_url=req.source_url,
        written_permission_evidence=req.written_permission_evidence,
        permission_status=req.permission_status,
        editing_permission=req.editing_permission,
        redistribution_permission=req.redistribution_permission,
        commercial_monetization_permission=req.commercial_monetization_permission,
        permission_expiry_date=req.permission_expiry_date,
        disclaimer_acknowledged=req.disclaimer_acknowledged,
        clear_expiry=bool(req.clear_expiry),
    )
    return _to_response(perm)

@router.post("/recordings/{recording_id}/assess", response_model=RecordingPermissionResponse)
def force_reassess_recording(recording_id: int, db: Session = Depends(get_db)):
    """Force re-evaluation of all 9 risk checks for a recording."""
    rec = db.query(Recording).filter(Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recording #{recording_id} not found")

    perm = copyright_risk_service.assess_recording_risk(db, recording_id)
    return _to_response(perm)

@router.post("/recordings/{recording_id}/manual-review", response_model=RecordingPermissionResponse)
def submit_manual_review(
    recording_id: int,
    req: ManualReviewRequest,
    db: Session = Depends(get_db)
):
    """Submit editor manual review override (approved_by_user or rejected_by_user)."""
    rec = db.query(Recording).filter(Recording.id == recording_id).first()
    if not rec:
        raise HTTPException(status_code=404, detail=f"Recording #{recording_id} not found")

    valid_statuses = ["approved_by_user", "rejected_by_user"]
    if req.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid manual review status '{req.status}'. Must be one of: {valid_statuses}"
        )

    perm = copyright_risk_service.apply_manual_review(
        db=db,
        recording_id=recording_id,
        review_status=req.status,
        notes=req.notes,
        reviewer_name=req.reviewer_name or "Editor"
    )
    return _to_response(perm)

@router.get("/clips/{clip_id}/status")
def check_clip_export_status(clip_id: int, db: Session = Depends(get_db)):
    """Check whether a specific YouTube Short is legally and policy-wise authorized for export/approval."""
    allowed, reason = copyright_risk_service.check_clip_export_allowed(db, clip_id)
    return {
        "clip_id": clip_id,
        "can_export": allowed,
        "block_reason": reason,
        "legal_disclaimer": "This check does not guarantee immunity from Content ID or DMCA claims."
    }
