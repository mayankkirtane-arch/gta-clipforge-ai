import os
import sys
from pathlib import Path
from datetime import datetime, timedelta, timezone
from fastapi import HTTPException

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, engine, migrate_database_schema
from app.models.recording import Recording
from app.models.clip import Clip, ClipStatus, MomentType
from app.models.recording_permission import RecordingPermission, PermissionStatusEnum, RiskLevelEnum
from app.services.copyright_risk_service import copyright_risk_service
from app.routers.copyright import get_copyright_summary, _to_response
from app.routers.clips import approve_clip

def test_phase9_copyright_center():
    print("=" * 80)
    print("🛡️  STARTING PHASE 9: COPYRIGHT AND MONETIZATION RISK CENTER TEST SUITE")
    print("=" * 80)

    # 1. Database Schema & Migration Check
    print("\n--- 1. Checking Database Migration & recording_permissions Table ---")
    migrate_database_schema(engine)
    db = SessionLocal()

    # 2. Test Official Policies
    print("\n--- 2. Verifying Official Publisher & Platform Copyright Policies ---")
    policies = copyright_risk_service.get_official_policies()
    assert len(policies) >= 3, f"Expected at least 3 official policies, got {len(policies)}"
    print(f"✅ Found {len(policies)} verified official policies:")
    for p in policies:
        print(f"   • [{p.publisher_or_platform}] {p.name}")
        print(f"     URL: {p.policy_url} (Checked: {p.last_checked_date})")
        print(f"     Commercial Stance: {p.commercial_use_stance[:70]}...")
        assert p.policy_url.startswith("http")
        assert len(p.key_rules) > 0

    # 3. Setup Test Recording
    print("\n--- 3. Testing Permission Initialization on Gameplay Recording ---")
    rec = db.query(Recording).first()
    if not rec:
        rec = Recording(
            filename="phase9_test_recording.mp4",
            original_filename="phase9_test_recording.mp4",
            file_path="recordings/phase9_test_recording.mp4",
            status="analyzed",
            duration_seconds=75.0,
            resolution="1920x1080",
            fps=60.0
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)

    # Clean existing permission for fresh test
    db.query(RecordingPermission).filter(RecordingPermission.recording_id == rec.id).delete()
    db.commit()

    perm = copyright_risk_service.get_or_create_permission(db, rec.id)
    assert perm.permission_status == PermissionStatusEnum.NOT_REQUESTED
    assert perm.can_export is False
    assert perm.overall_risk_level in [RiskLevelEnum.HIGH, RiskLevelEnum.UNKNOWN]

    resp_obj = _to_response(perm)
    assert len(resp_obj.risk_checks) == 9
    print(f"✅ Initialized permission for Recording #{rec.id}:")
    print(f"   Status: {perm.permission_status}")
    print(f"   Can Export: {perm.can_export}")
    print(f"   Overall Risk: {perm.overall_risk_level}")
    print(f"   9 Risk Checks Generated: {len(resp_obj.risk_checks)} checks")
    for c in resp_obj.risk_checks:
        print(f"     - #{c.number} {c.title}: {c.risk_level} ({c.category})")

    # 4. Test Granted Permission with Future Expiry
    print("\n--- 4. Testing Creator Permission Granted (Editing, Redistribution, Commercial) ---")
    future_expiry = datetime.now(timezone.utc) + timedelta(days=365)
    perm = copyright_risk_service.update_permission(
        db=db,
        recording_id=rec.id,
        original_creator="GTA_ViceCity_Pro",
        source_url="https://youtube.com/watch?v=gta6_sample_vod",
        written_permission_evidence="Email confirmation received on 2026-11-15: 'I hereby grant permission to edit, reframe and redistribute this clip on YouTube Shorts with ad-sharing.'",
        permission_status=PermissionStatusEnum.GRANTED,
        editing_permission=True,
        redistribution_permission=True,
        commercial_monetization_permission=True,
        permission_expiry_date=future_expiry,
        disclaimer_acknowledged=True
    )
    assert perm.permission_status == PermissionStatusEnum.GRANTED
    assert perm.can_export is True
    assert perm.overall_risk_level in [RiskLevelEnum.LOW, RiskLevelEnum.MEDIUM]
    print(f"✅ Permission Granted successfully:")
    print(f"   Creator: {perm.original_creator}")
    print(f"   Status: {perm.permission_status}")
    print(f"   Overall Risk: {perm.overall_risk_level} (Low risk when all 3 permissions are granted)")
    print(f"   Can Export: {perm.can_export}")

    # 5. Test Expiration Handling
    print("\n--- 5. Testing Automatic Permission Expiration ---")
    past_expiry = datetime.now(timezone.utc) - timedelta(days=10)
    perm = copyright_risk_service.update_permission(
        db=db,
        recording_id=rec.id,
        permission_expiry_date=past_expiry
    )
    assert perm.permission_status == PermissionStatusEnum.EXPIRED
    assert perm.can_export is False
    assert perm.overall_risk_level == RiskLevelEnum.HIGH
    print(f"✅ Automatic expiration verified:")
    print(f"   Status: {perm.permission_status}")
    print(f"   Can Export: {perm.can_export} (Export BLOCKED)")
    print(f"   Export Block Reason: {perm.export_block_reason}")
    print(f"   Overall Risk: {perm.overall_risk_level}")

    # 6. Test Creator Rejection Handling
    print("\n--- 6. Testing Creator Permission Rejection ---")
    perm = copyright_risk_service.update_permission(
        db=db,
        recording_id=rec.id,
        permission_status=PermissionStatusEnum.REJECTED,
        permission_expiry_date=None,
        clear_expiry=True,
        editing_permission=False,
        redistribution_permission=False,
        commercial_monetization_permission=False
    )
    assert perm.permission_status == PermissionStatusEnum.REJECTED
    assert perm.can_export is False
    assert perm.overall_risk_level == RiskLevelEnum.HIGH
    print(f"✅ Creator rejection verified:")
    print(f"   Status: {perm.permission_status}")
    print(f"   Can Export: {perm.can_export} (Export BLOCKED)")
    print(f"   Block Reason: {perm.export_block_reason}")

    # 7. Test Export Guardrails on Short Approval
    print("\n--- 7. Testing Export Guardrails on approve_clip Endpoint ---")
    clip = db.query(Clip).filter(Clip.recording_id == rec.id).first()
    if not clip:
        clip = Clip(
            recording_id=rec.id,
            title="Phase 9 Guardrail Short",
            status=ClipStatus.GENERATED,
            is_approved=False,
            duration=30.0,
            clip_path="GTA6_SHORTS/test_phase9_guardrail.mp4"
        )
        db.add(clip)
        db.commit()
        db.refresh(clip)

    # approve_clip must raise HTTP 403 Forbidden while recording permission is REJECTED
    blocked = False
    try:
        approve_clip(clip_id=clip.id, force=False, db=db)
    except HTTPException as e:
        blocked = True
        assert e.status_code == 403
        print(f"✅ Correctly raised HTTP 403: {e.detail}")

    assert blocked, "Expected approve_clip to raise HTTPException(403) when permission is REJECTED"

    # 8. Test Human Manual Review Override
    print("\n--- 8. Testing Human Manual Review Override for Uncertain Cases ---")
    perm = copyright_risk_service.apply_manual_review(
        db=db,
        recording_id=rec.id,
        review_status="approved_by_user",
        notes="Lead editor verified single-use creator release agreement via verified Discord server on 2026-11-16.",
        reviewer_name="Chief Content Officer"
    )
    assert perm.manual_review_status == "approved_by_user"
    assert perm.can_export is True
    print(f"✅ Manual review override applied:")
    print(f"   Review Status: {perm.manual_review_status}")
    print(f"   Reviewer: {perm.reviewer_name}")
    print(f"   Notes: {perm.manual_review_notes}")
    print(f"   Can Export: {perm.can_export} (Export UNLOCKED via manual review)")

    # Now approve_clip must succeed without raising an exception
    approved = approve_clip(clip_id=clip.id, force=False, db=db)
    assert approved.is_approved is True
    assert approved.status == ClipStatus.APPROVED
    print(f"✅ Short Clip #{clip.id} successfully approved for export under manual review override!")

    # 9. Test Summary Metrics
    print("\n--- 9. Testing Copyright Summary Metrics ---")
    summary = get_copyright_summary(db=db)
    assert summary["total_recordings"] >= 1
    assert "status_breakdown" in summary
    assert "risk_breakdown" in summary
    assert "legal_notice" in summary
    print(f"✅ Summary metrics:")
    print(f"   Total Recordings: {summary['total_recordings']}")
    print(f"   Status Breakdown: {summary['status_breakdown']}")
    print(f"   Risk Breakdown: {summary['risk_breakdown']}")
    print(f"   Export Authorized: {summary['can_export_count']}")
    print(f"   Export Blocked: {summary['blocked_export_count']}")
    print(f"   Advisory Notice: {summary['legal_notice']}")

    db.close()
    print("\n" + "=" * 80)
    print("🎉 ALL PHASE 9 COPYRIGHT & MONETIZATION RISK CENTER TESTS PASSED SUCCESSFULLY!")
    print("=" * 80)

if __name__ == "__main__":
    test_phase9_copyright_center()
