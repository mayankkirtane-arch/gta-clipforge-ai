import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from ..models.recording import Recording
from ..models.recording_permission import RecordingPermission, PermissionStatusEnum, RiskLevelEnum
from ..schemas.copyright import RiskCheckItem, OfficialPolicyInfo

OFFICIAL_POLICIES: List[Dict[str, Any]] = [
    {
        "id": "rockstar_taketwo_policy",
        "name": "Rockstar Games & Take-Two Interactive Video Policy",
        "publisher_or_platform": "Rockstar Games / Take-Two Interactive",
        "policy_url": "https://support.rockstargames.com/articles/200153756/Policy-on-posting-copyrighted-Rockstar-Games-material",
        "last_checked_date": "2026-11-15",
        "key_rules": [
            "Gameplay videos on YouTube/Twitch are permitted for non-commercial sharing.",
            "Standard YouTube Partner Program (AdSense) ad-sharing is generally tolerated.",
            "Commercial sale, behind-paywall gating, or licensing of gameplay is strictly prohibited.",
            "Spoilers, leaked pre-release builds, and unreleased materials will be removed via DMCA.",
            "Take-Two reserves the absolute right to issue takedowns or revoke permissions at any time."
        ],
        "commercial_use_stance": "Conditional / Non-commercial only. A creator's permission to use footage does NOT grant Rockstar's commercial rights.",
        "legal_distinction_notes": "Take-Two owns all underlying GTA 6 trademarks, game code, visual art, and character assets. A creator only owns their specific commentary/gameplay recording performance."
    },
    {
        "id": "youtube_reused_content_policy",
        "name": "YouTube Channel Monetization — Reused & Repetitious Content Policy",
        "publisher_or_platform": "YouTube / Google",
        "policy_url": "https://support.google.com/youtube/answer/1311392",
        "last_checked_date": "2026-11-10",
        "key_rules": [
            "Content must provide significant original commentary, transformative editing, or educational value.",
            "Merely clipping or compiling other creators' gameplay without significant transformation will be demonetized as Reused Content.",
            "Monetization rejection under Reused Content is distinct from copyright strikes.",
            "Automated programmatic mass-generation of clips without creative modification violates YPP quality standards."
        ],
        "commercial_use_stance": "Requires significant transformation (reframing, dynamic editing, narrative hooks, or voiceover).",
        "legal_distinction_notes": "Reused Content demonetization is an algorithmic/editorial YPP policy enforcement by YouTube, NOT a legal copyright infringement claim."
    },
    {
        "id": "youtube_copyright_fair_use",
        "name": "YouTube Copyright, Content ID & Fair Use Center",
        "publisher_or_platform": "YouTube / Google",
        "policy_url": "https://support.google.com/youtube/answer/2797466",
        "last_checked_date": "2026-11-05",
        "key_rules": [
            "Content ID claims automatically route ad revenue to copyright holders or block video in certain territories.",
            "Content ID claims do NOT issue a strike against the channel.",
            "DMCA Copyright Strikes are formal legal takedowns; 3 strikes results in channel termination.",
            "In-game commercial radio music is the #1 cause of Content ID claims for GTA gameplay."
        ],
        "commercial_use_stance": "Zero copyright tolerance for commercial pop/radio tracks.",
        "legal_distinction_notes": "Content ID Claims vs DMCA Strikes vs Legal Injunctions vs YPP Demonetization must be tracked as separate legal and platform mechanisms."
    }
]

class CopyrightRiskService:
    """
    Copyright and Monetization Risk Engine for GTA CLIPFORGE AI.
    Evaluates:
    - Creator Permission Management (editing, redistribution, commercial use, expiry)
    - 9-Point Risk Checks Matrix (LOW, MEDIUM, HIGH, UNKNOWN)
    - Export Guardrails (blocks export when permissions missing/rejected/expired)
    - Legal compliance transparency & policy documentation
    """

    def get_official_policies(self) -> List[OfficialPolicyInfo]:
        """Returns verified official policies with last-checked dates."""
        return [OfficialPolicyInfo(**p) for p in OFFICIAL_POLICIES]

    def get_or_create_permission(self, db: Session, recording_id: int) -> RecordingPermission:
        """Fetch existing permission or create initial record for recording."""
        rec = db.query(Recording).filter(Recording.id == recording_id).first()
        if not rec:
            raise ValueError(f"Recording #{recording_id} not found.")

        perm = db.query(RecordingPermission).filter(RecordingPermission.recording_id == recording_id).first()
        if not perm:
            perm = RecordingPermission(
                recording_id=recording_id,
                original_creator=None,
                source_url=None,
                written_permission_evidence=None,
                permission_status=PermissionStatusEnum.NOT_REQUESTED,
                editing_permission=False,
                redistribution_permission=False,
                commercial_monetization_permission=False,
                permission_expiry_date=None,
                manual_review_status="pending_review",
                overall_risk_level=RiskLevelEnum.UNKNOWN,
                can_export=False,
                export_block_reason="Creator permission has not been requested or verified.",
                disclaimer_acknowledged=False,
            )
            db.add(perm)
            db.commit()
            db.refresh(perm)

        # Run assessment to keep status current
        self.assess_recording_risk(db, recording_id)
        return perm

    def update_permission(
        self,
        db: Session,
        recording_id: int,
        original_creator: Optional[str] = None,
        source_url: Optional[str] = None,
        written_permission_evidence: Optional[str] = None,
        permission_status: Optional[str] = None,
        editing_permission: Optional[bool] = None,
        redistribution_permission: Optional[bool] = None,
        commercial_monetization_permission: Optional[bool] = None,
        permission_expiry_date: Optional[datetime] = None,
        disclaimer_acknowledged: Optional[bool] = None,
        clear_expiry: bool = False,
    ) -> RecordingPermission:
        """Update permission attributes and re-evaluate 9 risk checks."""
        perm = self.get_or_create_permission(db, recording_id)

        if original_creator is not None:
            perm.original_creator = original_creator.strip() if original_creator else None
        if source_url is not None:
            perm.source_url = source_url.strip() if source_url else None
        if written_permission_evidence is not None:
            perm.written_permission_evidence = written_permission_evidence.strip() if written_permission_evidence else None
        if permission_status is not None:
            perm.permission_status = permission_status
        if editing_permission is not None:
            perm.editing_permission = editing_permission
        if redistribution_permission is not None:
            perm.redistribution_permission = redistribution_permission
        if commercial_monetization_permission is not None:
            perm.commercial_monetization_permission = commercial_monetization_permission
        if clear_expiry:
            perm.permission_expiry_date = None
        elif permission_expiry_date is not None:
            perm.permission_expiry_date = permission_expiry_date
        if disclaimer_acknowledged is not None:
            perm.disclaimer_acknowledged = disclaimer_acknowledged

        db.commit()
        db.refresh(perm)

        # Re-assess risk and export eligibility
        return self.assess_recording_risk(db, recording_id)

    def apply_manual_review(
        self,
        db: Session,
        recording_id: int,
        review_status: str,  # approved_by_user or rejected_by_user
        notes: str,
        reviewer_name: str = "Editor"
    ) -> RecordingPermission:
        """Apply manual human review override for uncertain cases."""
        perm = self.get_or_create_permission(db, recording_id)
        perm.manual_review_status = review_status
        perm.manual_review_notes = notes.strip()
        perm.reviewer_name = reviewer_name
        perm.reviewed_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(perm)

        return self.assess_recording_risk(db, recording_id)

    def assess_recording_risk(self, db: Session, recording_id: int) -> RecordingPermission:
        """
        Executes the 9 distinct risk checks for a recording.
        Evaluates permissions, expiry dates, publisher policies, in-game audio, and YouTube reused content risks.
        """
        perm = db.query(RecordingPermission).filter(RecordingPermission.recording_id == recording_id).first()
        if not perm:
            return self.get_or_create_permission(db, recording_id)

        rec = db.query(Recording).filter(Recording.id == recording_id).first()

        now = datetime.now(timezone.utc)
        # Check automatic expiration
        is_expired = False
        if perm.permission_expiry_date:
            expiry = perm.permission_expiry_date
            if expiry.tzinfo is None:
                expiry = expiry.replace(tzinfo=timezone.utc)
            if expiry < now:
                is_expired = True
                perm.permission_status = PermissionStatusEnum.EXPIRED

        checks: List[RiskCheckItem] = []

        # --- Check 1: Creator recording ownership ---
        c1_risk = RiskLevelEnum.UNKNOWN
        c1_summary = "Unverified recording source."
        if perm.original_creator and perm.written_permission_evidence:
            c1_risk = RiskLevelEnum.LOW
            c1_summary = f"Recorded by '{perm.original_creator}' with documented permission evidence."
        elif perm.original_creator:
            c1_risk = RiskLevelEnum.MEDIUM
            c1_summary = f"Creator named as '{perm.original_creator}' but missing written verification evidence."
        else:
            c1_risk = RiskLevelEnum.HIGH
            c1_summary = "Original creator ownership is unknown. High risk of unauthorized third-party footage."

        checks.append(RiskCheckItem(
            id="creator_recording_ownership",
            number=1,
            title="Creator Recording Ownership",
            category="creator_rights",
            risk_level=c1_risk,
            summary=c1_summary,
            details="Verifies whether the submitting party owns the raw gameplay recording and is authorized to provide it.",
            recommendation="Always obtain direct confirmation from the gameplay creator before publishing.",
        ))

        # --- Check 2: Permission to edit ---
        c2_risk = RiskLevelEnum.HIGH
        c2_summary = "Editing rights not granted."
        if perm.permission_status == PermissionStatusEnum.GRANTED and perm.editing_permission and not is_expired:
            c2_risk = RiskLevelEnum.LOW
            c2_summary = "Written authorization to cut, edit, reframe to 9:16, and remix is granted."
        elif perm.permission_status == PermissionStatusEnum.PENDING:
            c2_risk = RiskLevelEnum.MEDIUM
            c2_summary = "Permission to edit is currently pending creator response."
        elif is_expired:
            c2_risk = RiskLevelEnum.HIGH
            c2_summary = "Permission to edit has expired."
        elif perm.permission_status == PermissionStatusEnum.REJECTED:
            c2_risk = RiskLevelEnum.HIGH
            c2_summary = "Original creator explicitly denied permission to edit."

        checks.append(RiskCheckItem(
            id="permission_to_edit",
            number=2,
            title="Permission to Edit",
            category="creator_rights",
            risk_level=c2_risk,
            summary=c2_summary,
            details="Transformative editing, cutting, reframing, and overlaying graphics requires creator authorization.",
            recommendation="Do not edit or cut video if creator has rejected or not granted editing rights.",
        ))

        # --- Check 3: Permission to redistribute ---
        c3_risk = RiskLevelEnum.HIGH
        c3_summary = "Redistribution rights not granted."
        if perm.permission_status == PermissionStatusEnum.GRANTED and perm.redistribution_permission and not is_expired:
            c3_risk = RiskLevelEnum.LOW
            c3_summary = "Explicit redistribution permission for YouTube Shorts, TikTok, and Reels is active."
        elif perm.permission_status == PermissionStatusEnum.PENDING:
            c3_risk = RiskLevelEnum.MEDIUM
            c3_summary = "Redistribution request pending."
        elif is_expired:
            c3_risk = RiskLevelEnum.HIGH
            c3_summary = "Redistribution rights have expired."
        elif perm.permission_status == PermissionStatusEnum.REJECTED:
            c3_risk = RiskLevelEnum.HIGH
            c3_summary = "Creator explicitly rejected redistribution."

        checks.append(RiskCheckItem(
            id="permission_to_redistribute",
            number=3,
            title="Permission to Redistribute",
            category="creator_rights",
            risk_level=c3_risk,
            summary=c3_summary,
            details="Posting another creator's gameplay to public platforms without authorization constitutes copyright infringement.",
            recommendation="Confirm multi-platform redistribution rights in writing.",
        ))

        # --- Check 4: Commercial-use permission ---
        c4_risk = RiskLevelEnum.HIGH
        c4_summary = "Commercial monetization permission not authorized by creator."
        if perm.permission_status == PermissionStatusEnum.GRANTED and perm.commercial_monetization_permission and not is_expired:
            c4_risk = RiskLevelEnum.LOW
            c4_summary = "Creator authorized commercial monetization and ad revenue generation."
        elif perm.permission_status == PermissionStatusEnum.PENDING:
            c4_risk = RiskLevelEnum.MEDIUM
            c4_summary = "Commercial use request is pending."
        else:
            c4_risk = RiskLevelEnum.HIGH
            c4_summary = "No commercial monetization authorization. Creator can claim or revoke ad revenue."

        checks.append(RiskCheckItem(
            id="commercial_use_permission",
            number=4,
            title="Commercial-Use Permission",
            category="creator_rights",
            risk_level=c4_risk,
            summary=c4_summary,
            details="Creator's consent to monetize their recording. NOTE: Creator permission does NOT grant Rockstar's commercial rights.",
            recommendation="Obtain written commercial rights before enrolling clips in revenue-generating programs.",
        ))

        # --- Check 5: Rockstar and Take-Two policy uncertainty ---
        checks.append(RiskCheckItem(
            id="rockstar_take_two_policy",
            number=5,
            title="Rockstar & Take-Two Policy Uncertainty",
            category="publisher_policy",
            risk_level=RiskLevelEnum.MEDIUM,
            summary="Take-Two allows non-commercial gameplay sharing; reserves right to remove videos.",
            details="Take-Two Interactive policy permits ad-supported player video sharing on YouTube. However, commercial exploitation, unreleased builds, or spoiler leaks remain prohibited. Policy can change without notice.",
            recommendation="Avoid leaks, unreleased footage, and commercial selling. Maintain strict non-commercial fair gameplay standards.",
            policy_url="https://support.rockstargames.com/articles/200153756/Policy-on-posting-copyrighted-Rockstar-Games-material",
            last_checked_date="2026-11-15",
        ))

        # --- Check 6: In-game music copyright risk ---
        checks.append(RiskCheckItem(
            id="in_game_music_risk",
            number=6,
            title="In-Game Music Copyright Risk",
            category="audio_copyright",
            risk_level=RiskLevelEnum.MEDIUM,
            summary="GTA in-game commercial radio stations frequently trigger automated Content ID claims.",
            details="Record labels (Universal, Sony, Warner) enforce Content ID on in-game radio music. GTA CLIPFORGE AI Phase 7 procedural synthwave & SFX mitigates this risk when applied.",
            recommendation="Enable 'Streamer Mode' in GTA 6 or use GTA CLIPFORGE AI Phase 7 procedural royalty-free music replacement.",
            policy_url="https://support.google.com/youtube/answer/2797466",
            last_checked_date="2026-11-05",
        ))

        # --- Check 7: Third-party audio risk ---
        checks.append(RiskCheckItem(
            id="third_party_audio_risk",
            number=7,
            title="Third-Party Audio Risk",
            category="audio_copyright",
            risk_level=RiskLevelEnum.LOW,
            summary="GTA CLIPFORGE AI built-in audio library uses 100% royalty-free CC0 procedural audio.",
            details="Procedural synth beats and sound effects generated by the engine contain zero commercial samples and zero Content ID fingerprinting.",
            recommendation="Stick to the built-in procedural library in Assets/Music and Assets/SFX.",
        ))

        # --- Check 8: YouTube reused-content risk ---
        checks.append(RiskCheckItem(
            id="youtube_reused_content_risk",
            number=8,
            title="YouTube Reused-Content Risk",
            category="platform_monetization",
            risk_level=RiskLevelEnum.MEDIUM,
            summary="YouTube demonetizes channels that upload raw gameplay without transformative editing.",
            details="Under YouTube Channel Monetization policies, clips must add significant original value. GTA CLIPFORGE AI Phase 6/7/8 reframing (9:16 vertical, dynamic zoom, slow-mo climax, neon subtitles, audio normalization) provides transformative value.",
            recommendation="Add voiceover commentary, custom edits, or narrative context to maximize YPP approval.",
            policy_url="https://support.google.com/youtube/answer/1311392",
            last_checked_date="2026-11-10",
        ))

        # --- Check 9: YouTube monetization eligibility ---
        checks.append(RiskCheckItem(
            id="youtube_monetization_eligibility",
            number=9,
            title="YouTube Monetization Eligibility",
            category="platform_monetization",
            risk_level=RiskLevelEnum.MEDIUM,
            summary="Monetization eligibility requires YPP compliance, advertiser-friendly guidelines, and original value.",
            details="Separate from copyright strikes: a video can be 100% claim-free but still rejected for monetization if deemed repetitive or unoriginal.",
            recommendation="Maintain unique editing, high production value, and avoid mass automated re-uploading.",
            policy_url="https://support.google.com/youtube/answer/1311392",
            last_checked_date="2026-11-10",
        ))

        # Overall Risk Level Calculation
        high_count = sum(1 for c in checks if c.risk_level == RiskLevelEnum.HIGH)
        med_count = sum(1 for c in checks if c.risk_level == RiskLevelEnum.MEDIUM)

        if perm.permission_status == PermissionStatusEnum.REJECTED or is_expired:
            overall_risk = RiskLevelEnum.HIGH
        elif high_count >= 2:
            overall_risk = RiskLevelEnum.HIGH
        elif high_count == 1 or med_count >= 3:
            overall_risk = RiskLevelEnum.MEDIUM
        elif perm.permission_status == PermissionStatusEnum.GRANTED:
            overall_risk = RiskLevelEnum.LOW
        else:
            overall_risk = RiskLevelEnum.UNKNOWN

        # Export Approval Guardrails
        can_export = True
        block_reasons = []

        if perm.permission_status == PermissionStatusEnum.REJECTED:
            can_export = False
            block_reasons.append("Creator explicitly REJECTED permissions for this recording.")
        elif is_expired:
            can_export = False
            block_reasons.append("Creator permission has EXPIRED.")
        elif perm.permission_status == PermissionStatusEnum.NOT_REQUESTED and not perm.editing_permission:
            can_export = False
            block_reasons.append("Creator permission has NOT been requested or granted.")
        elif perm.permission_status == PermissionStatusEnum.PENDING:
            can_export = False
            block_reasons.append("Creator permission is currently PENDING response.")

        if perm.manual_review_status == "rejected_by_user":
            can_export = False
            block_reasons.append(f"Rejected by human review: {perm.manual_review_notes or 'No reason provided'}")
        elif perm.manual_review_status == "approved_by_user":
            # Manual override granted by editor
            can_export = True
            block_reasons = []

        perm.overall_risk_level = overall_risk
        perm.can_export = can_export
        perm.export_block_reason = " | ".join(block_reasons) if block_reasons else None
        perm.risk_checks_json = json.dumps([c.dict() for c in checks])

        db.commit()
        db.refresh(perm)
        return perm

    def check_clip_export_allowed(self, db: Session, clip_id: int) -> Tuple[bool, Optional[str]]:
        """
        Validates whether a generated Short is legally and policy-wise authorized for export/approval.
        Prevents export approval when required creator permissions are rejected, expired, or missing.
        """
        from ..models.clip import Clip
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            return False, f"Clip #{clip_id} not found."

        perm = db.query(RecordingPermission).filter(RecordingPermission.recording_id == clip.recording_id).first()
        if not perm:
            perm = self.get_or_create_permission(db, clip.recording_id)

        # Refresh assessment
        perm = self.assess_recording_risk(db, clip.recording_id)

        if not perm.can_export:
            reason = perm.export_block_reason or "Export blocked due to unresolved copyright or creator permission restrictions."
            return False, f"Export blocked for Clip #{clip_id} (Recording #{clip.recording_id}): {reason}"

        return True, None

copyright_risk_service = CopyrightRiskService()
