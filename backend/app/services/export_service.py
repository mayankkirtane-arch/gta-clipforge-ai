import os
import csv
import json
import zipfile
import shutil
import subprocess
from io import StringIO
from pathlib import Path
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal
from ..models.recording import Recording
from ..models.clip import Clip, ClipStatus
from ..models.clip_metadata import ClipMetadata
from ..models.detected_moment import DetectedMoment
from ..models.publishing_item import PublishingItem, PublishingStatusEnum
from ..models.recording_permission import RecordingPermission
from .copyright_risk_service import copyright_risk_service

def format_srt_time(seconds: float) -> str:
    """Format seconds into standard SRT timestamp HH:MM:SS,mmm"""
    millis = int(round((seconds - int(seconds)) * 1000))
    total_seconds = int(seconds)
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"

class ExportService:
    def __init__(self):
        self.shorts_dir = Path(settings.SHORTS_DIR)
        self.best_moments_dir = Path(settings.BEST_MOMENTS_DIR)
        self.reports_dir = Path(settings.REPORTS_DIR)
        self.exports_dir = Path(settings.EXPORTS_PACKAGES_DIR)
        
        # Ensure subdirectories
        self.shorts_dir.mkdir(parents=True, exist_ok=True)
        self.best_moments_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
        self.exports_dir.mkdir(parents=True, exist_ok=True)

    def generate_srt_subtitles(self, db: Session, clip_id: int) -> str:
        """Generate accurate SRT subtitle content with millisecond timing."""
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            raise ValueError(f"Clip #{clip_id} not found")

        meta = db.query(ClipMetadata).filter(ClipMetadata.clip_id == clip_id).first()
        duration = clip.duration or 30.0

        hook_text = (meta.hook if meta and meta.hook else clip.subtitle_text) or f"Watch this GTA 6 {clip.preset_name or 'insane'} moment!"
        title_text = (meta.title if meta and meta.title else clip.title) or "Vice City Action"
        tags_text = (meta.hashtags if meta and meta.hashtags else "#GTA6 #GTA6Shorts")

        # Partition into 3-4 second natural reading segments
        segments = []
        # Segment 1: Spoken Hook (0.0 to min(3.5, duration))
        hook_end = min(3.5, duration * 0.25)
        segments.append((0.0, hook_end, hook_text))

        # Segment 2: Action Commentary
        mid_start = hook_end
        mid_end = min(duration * 0.75, duration - 3.0)
        if mid_end > mid_start:
            segments.append((mid_start, mid_end, title_text))

        # Segment 3: Climax & CTA
        climax_start = max(mid_end, duration - 3.0)
        segments.append((climax_start, duration, f"Subscribe for more Vice City! {tags_text.split()[0]}"))

        srt_lines = []
        for idx, (st, en, txt) in enumerate(segments, 1):
            srt_lines.append(f"{idx}")
            srt_lines.append(f"{format_srt_time(st)} --> {format_srt_time(en)}")
            srt_lines.append(txt)
            srt_lines.append("")

        srt_content = "\n".join(srt_lines)

        # Save to disk
        srt_file = self.exports_dir / f"short_{clip_id}.srt"
        with open(srt_file, "w", encoding="utf-8") as f:
            f.write(srt_content)

        return srt_content

    def generate_txt_transcript(self, db: Session, clip_id: int) -> str:
        """Generate clean readable plain-text transcript."""
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            raise ValueError(f"Clip #{clip_id} not found")

        meta = db.query(ClipMetadata).filter(ClipMetadata.clip_id == clip_id).first()
        duration = clip.duration or 30.0
        title = meta.title if meta and meta.title else (clip.title or "GTA 6 Short")
        hook = meta.hook if meta and meta.hook else "High intensity gameplay moment"
        tags = meta.hashtags if meta and meta.hashtags else "#GTA6 #ViceCity"

        txt_lines = [
            f"=== GTA 6 YOUTUBE SHORT #{clip_id} TRANSCRIPT ===",
            f"Title: {title}",
            f"Duration: {duration:.1f} seconds",
            f"Resolution: 1080x1920 (9:16 Vertical)",
            f"Preset: {clip.preset_name or 'BADASS CINEMATIC'}",
            f"Generated Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
            "",
            "--- SPOKEN HOOK & TIMECODES ---",
            f"[00:00 - 00:03.5] {hook}",
            f"[00:03.5 - {int(duration):02d}:00] High-energy gameplay climax with synchronized audio.",
            f"[{max(0, int(duration)-3):02d}:00 - {int(duration):02d}:00] Outro CTA & Channel Engagement.",
            "",
            "--- METADATA & HASHTAGS ---",
            f"Hashtags: {tags}",
            f"Description: {meta.description if meta else clip.description or ''}",
        ]
        txt_content = "\n".join(txt_lines)

        txt_file = self.exports_dir / f"short_{clip_id}_transcript.txt"
        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(txt_content)

        return txt_content

    def export_csv_metadata(self, db: Session, clip_ids: Optional[List[int]] = None) -> str:
        """Generate formatted CSV with publishing and performance metadata."""
        query = db.query(Clip)
        if clip_ids:
            query = query.filter(Clip.id.in_(clip_ids))
        clips = query.all()

        output = StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "clip_id",
            "recording_id",
            "title",
            "description",
            "hashtags",
            "hook",
            "thumbnail_text",
            "duration_sec",
            "resolution",
            "aspect_ratio",
            "preset_name",
            "render_mode",
            "excitement_score",
            "is_approved",
            "publishing_status",
            "planned_publish_date",
            "views_count",
            "likes_count",
            "comments_count",
            "video_file_path",
        ])

        for c in clips:
            meta = db.query(ClipMetadata).filter(ClipMetadata.clip_id == c.id).first()
            pub = db.query(PublishingItem).filter(PublishingItem.clip_id == c.id).first()

            title = pub.active_title if pub else (meta.title if meta else c.title or "")
            desc = pub.description if pub else (meta.description if meta else c.description or "")
            tags = pub.hashtags if pub else (meta.hashtags if meta else "")
            hook = pub.hook if pub else (meta.hook if meta else "")
            thumb_txt = pub.thumbnail_text if pub else (meta.thumbnail_text if meta else "")
            status = pub.status if pub else ("approved" if c.is_approved else c.status)
            planned_date = pub.planned_publish_date.isoformat() if pub and pub.planned_publish_date else ""
            views = pub.views_count if pub else 0
            likes = pub.likes_count if pub else 0
            comments = pub.comments_count if pub else 0

            writer.writerow([
                c.id,
                c.recording_id,
                title,
                desc,
                tags,
                hook,
                thumb_txt,
                f"{c.duration:.1f}" if c.duration else "",
                c.resolution,
                c.aspect_ratio,
                c.preset_name or "",
                c.render_mode,
                c.excitement_score or 0,
                1 if c.is_approved else 0,
                status,
                planned_date,
                views,
                likes,
                comments,
                c.clip_path or "",
            ])

        csv_text = output.getvalue()
        csv_path = self.exports_dir / "GTA6_SHORTS_METADATA.csv"
        with open(csv_path, "w", encoding="utf-8", newline="") as f:
            f.write(csv_text)

        return csv_text

    def generate_copyright_report(self, db: Session, recording_id: int) -> Dict[str, Any]:
        """Generate structured JSON and Markdown copyright and legal compliance report."""
        rec = db.query(Recording).filter(Recording.id == recording_id).first()
        if not rec:
            raise ValueError(f"Recording #{recording_id} not found")

        perm = copyright_risk_service.assess_recording_risk(db, recording_id)
        policies = copyright_risk_service.get_official_policies()

        raw_checks = []
        if perm.risk_checks_json:
            try:
                raw_checks = json.loads(perm.risk_checks_json)
            except Exception:
                raw_checks = []

        now_utc = datetime.now(timezone.utc)
        is_expired = False
        if perm.permission_expiry_date:
            exp = perm.permission_expiry_date
            if exp.tzinfo is None:
                exp = exp.replace(tzinfo=timezone.utc)
            is_expired = exp < now_utc

        report_data = {
            "report_id": f"CR-REC-{recording_id}-{int(now_utc.timestamp())}",
            "generated_at": now_utc.isoformat(),
            "recording_id": recording_id,
            "filename": rec.original_filename,
            "duration_seconds": rec.duration_seconds,
            "permission_management": {
                "original_creator": perm.original_creator or "Unspecified",
                "source_url": perm.source_url or "None",
                "written_permission_evidence": perm.written_permission_evidence or "None documented",
                "permission_status": perm.permission_status,
                "editing_permission_granted": perm.editing_permission,
                "redistribution_permission_granted": perm.redistribution_permission,
                "commercial_monetization_granted": perm.commercial_monetization_permission,
                "expiry_date": perm.permission_expiry_date.isoformat() if perm.permission_expiry_date else "Perpetual / No Expiry",
                "is_expired": is_expired or (perm.permission_status == "Expired"),
            },
            "risk_assessment": {
                "overall_risk_level": perm.overall_risk_level,
                "can_export": perm.can_export,
                "export_block_reason": perm.export_block_reason,
                "manual_review_status": perm.manual_review_status,
                "manual_review_notes": perm.manual_review_notes,
                "reviewer_name": perm.reviewer_name,
                "reviewed_at": perm.reviewed_at.isoformat() if perm.reviewed_at else None,
            },
            "risk_checks": raw_checks,
            "official_policy_baselines": [p.dict() for p in policies],
            "legal_notice": "GTA CLIPFORGE AI risk classifications are educational and advisory only and do not constitute formal legal counsel. Take-Two and YouTube retain unilateral enforcement authority."
        }

        # Save JSON Report
        json_path = self.reports_dir / f"copyright_report_rec_{recording_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(report_data, f, indent=2)

        # Build Markdown Report
        md_lines = [
            f"# GTA CLIPFORGE AI — Copyright & Monetization Compliance Report",
            f"**Report ID**: `{report_data['report_id']}`  ",
            f"**Generated**: {report_data['generated_at']}  ",
            f"**Recording**: #{recording_id} (`{rec.original_filename}`)  ",
            f"**Overall Risk Classification**: **{perm.overall_risk_level}**  ",
            f"**Export Status**: **{'AUTHORIZED FOR EXPORT' if perm.can_export else 'EXPORT BLOCKED'}**  ",
            "",
            "## 1. Creator Permission Record",
            f"- **Original Creator**: {report_data['permission_management']['original_creator']}",
            f"- **Source URL**: {report_data['permission_management']['source_url']}",
            f"- **Status**: {perm.permission_status}",
            f"- **Editing Permission**: {'YES' if perm.editing_permission else 'NO'}",
            f"- **Redistribution Permission**: {'YES' if perm.redistribution_permission else 'NO'}",
            f"- **Commercial Monetization**: {'YES' if perm.commercial_monetization_permission else 'NO'}",
            f"- **Written Evidence**: *\"{report_data['permission_management']['written_permission_evidence']}\"*",
            "",
            "## 2. 9-Point Risk Checks Matrix",
        ]

        for c in raw_checks:
            md_lines.append(f"### Check #{c.get('number', '?')}: {c.get('title', 'Check')}")
            md_lines.append(f"- **Risk Level**: `{c.get('risk_level', 'UNKNOWN')}` | **Category**: `{c.get('category')}`")
            md_lines.append(f"- **Summary**: {c.get('summary')}")
            md_lines.append(f"- **Details**: {c.get('details')}")
            md_lines.append(f"- **Recommendation**: {c.get('recommendation')}")
            md_lines.append("")

        md_lines.extend([
            "## 3. Human Manual Review Override",
            f"- **Status**: `{perm.manual_review_status}`",
            f"- **Reviewer**: {perm.reviewer_name or 'None'}",
            f"- **Notes**: {perm.manual_review_notes or 'None'}",
            "",
            "## 4. Legal Advisory Disclaimer",
            "> This report is generated algorithmically for internal workflow compliance. It does NOT constitute legal advice. Take-Two Interactive and YouTube retain unilateral authority to enforce terms of service.",
        ])

        md_content = "\n".join(md_lines)
        md_path = self.reports_dir / f"copyright_report_rec_{recording_id}.md"
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return {
            "json_path": str(json_path),
            "markdown_path": str(md_path),
            "can_export": perm.can_export,
            "overall_risk_level": perm.overall_risk_level,
            "report_id": report_data["report_id"],
        }

    def export_best_moments(self, db: Session, recording_id: int) -> List[Dict[str, Any]]:
        """Extract horizontal / raw high-excitement best moments into GTA6_BEST_MOMENTS."""
        rec = db.query(Recording).filter(Recording.id == recording_id).first()
        if not rec or not os.path.isfile(rec.file_path):
            raise ValueError(f"Recording #{recording_id} file not found on disk")

        moments = db.query(DetectedMoment).filter(
            DetectedMoment.recording_id == recording_id
        ).order_by(DetectedMoment.confidence_score.desc()).limit(5).all()

        exported = []
        for m in moments:
            event_type = m.event_type or "moment"
            out_name = f"best_moment_rec{recording_id}_moment{m.id}_{event_type}.mp4"
            out_path = self.best_moments_dir / out_name
            dur = max(5.0, (m.end_time or 15.0) - (m.start_time or 0.0))

            cmd = [
                settings.FFMPEG_PATH,
                "-y",
                "-ss", f"{m.start_time:.3f}",
                "-i", rec.file_path,
                "-t", f"{dur:.3f}",
                "-c", "copy",
                "-movflags", "+faststart",
                str(out_path)
            ]

            try:
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=30, check=True)
                exported.append({
                    "moment_id": m.id,
                    "event_type": event_type,
                    "confidence_score": m.confidence_score,
                    "duration": dur,
                    "file_path": str(out_path),
                })
            except Exception as e:
                print(f"Error exporting best moment #{m.id}: {e}")

        return exported

    def create_export_zip(
        self,
        db: Session,
        clip_ids: Optional[List[int]] = None,
        include_subtitles: bool = True,
        include_transcripts: bool = True,
        include_metadata: bool = True,
        include_copyright_reports: bool = True,
        package_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Create a complete production ZIP archive containing Shorts, SRTs, transcripts, CSV, and reports."""
        query = db.query(Clip)
        if clip_ids:
            query = query.filter(Clip.id.in_(clip_ids))
        clips = query.all()

        if not clips:
            raise ValueError("No clips found to export")

        timestamp = int(datetime.now(timezone.utc).timestamp())
        base_name = package_name.strip() if package_name else f"GTA6_SHORTS_EXPORT_{timestamp}"
        zip_path = self.exports_dir / f"{base_name}.zip"

        files_included = []

        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
            # 1. Shorts MP4 files
            for c in clips:
                if c.clip_path and os.path.isfile(c.clip_path):
                    arc_name = f"shorts/short_{c.id}_{Path(c.clip_path).name}"
                    zipf.write(c.clip_path, arc_name)
                    files_included.append(arc_name)

                # Thumbnail
                if c.thumbnail_path and os.path.isfile(c.thumbnail_path):
                    t_arc = f"thumbnails/short_{c.id}_thumb.jpg"
                    zipf.write(c.thumbnail_path, t_arc)
                    files_included.append(t_arc)

                # Subtitles SRT
                if include_subtitles:
                    try:
                        srt_text = self.generate_srt_subtitles(db, c.id)
                        srt_arc = f"subtitles/short_{c.id}.srt"
                        zipf.writestr(srt_arc, srt_text)
                        files_included.append(srt_arc)
                    except Exception as e:
                        print(f"SRT generation failed for #{c.id}: {e}")

                # Transcripts TXT
                if include_transcripts:
                    try:
                        txt_text = self.generate_txt_transcript(db, c.id)
                        txt_arc = f"transcripts/short_{c.id}_transcript.txt"
                        zipf.writestr(txt_arc, txt_text)
                        files_included.append(txt_arc)
                    except Exception as e:
                        print(f"TXT transcript failed for #{c.id}: {e}")

            # 2. Metadata CSV
            if include_metadata:
                csv_text = self.export_csv_metadata(db, [c.id for c in clips])
                zipf.writestr("metadata.csv", csv_text)
                files_included.append("metadata.csv")

            # 3. Copyright Reports
            if include_copyright_reports:
                rec_ids = list({c.recording_id for c in clips})
                for rid in rec_ids:
                    try:
                        rep = self.generate_copyright_report(db, rid)
                        if os.path.isfile(rep["markdown_path"]):
                            rep_arc = f"reports/{Path(rep['markdown_path']).name}"
                            zipf.write(rep["markdown_path"], rep_arc)
                            files_included.append(rep_arc)
                    except Exception as e:
                        print(f"Report export failed for Recording #{rid}: {e}")

            # 4. Manifest JSON
            manifest = {
                "package_name": base_name,
                "exported_at": datetime.now(timezone.utc).isoformat(),
                "total_clips": len(clips),
                "clip_ids": [c.id for c in clips],
                "files_count": len(files_included),
                "target_platform": "YouTube Shorts (1080x1920 9:16)",
            }
            zipf.writestr("manifest.json", json.dumps(manifest, indent=2))
            files_included.append("manifest.json")

        zip_size = os.path.getsize(zip_path)

        return {
            "status": "success",
            "zip_filename": f"{base_name}.zip",
            "zip_path": str(zip_path),
            "zip_size_bytes": zip_size,
            "zip_download_url": f"/api/exports/download/{base_name}.zip",
            "clips_exported_count": len(clips),
            "files_included": files_included,
        }

export_service = ExportService()
