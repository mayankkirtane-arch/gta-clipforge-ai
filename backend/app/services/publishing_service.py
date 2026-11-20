import json
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..models.clip import Clip, ClipStatus
from ..models.clip_metadata import ClipMetadata
from ..models.recording_permission import RecordingPermission
from ..models.publishing_item import PublishingItem, PublishingStatusEnum
from ..schemas.publishing import (
    PublishingItemResponse,
    PublishingItemUpdateRequest,
    PublishingMetricsUpdateRequest,
    PublishingWorkspaceSummary,
    PerformanceMetrics,
)
from .metadata_generator import metadata_generator

DEFAULT_CHECKLIST = {
    "aspect_ratio_verified": True,
    "resolution_1080x1920": True,
    "audio_normalized": True,
    "copyright_cleared": False,
    "thumbnail_ready": True,
    "hook_configured": True,
    "title_under_100_chars": True,
    "description_with_tags": True,
    "user_approved": False,
}

class PublishingService:
    def get_or_create_publishing_item(self, db: Session, clip_id: int) -> PublishingItem:
        """Fetch existing PublishingItem or initialize from Clip and ClipMetadata."""
        item = db.query(PublishingItem).filter(PublishingItem.clip_id == clip_id).first()
        if item:
            return item

        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            raise ValueError(f"Clip #{clip_id} not found")

        # Load or generate metadata
        meta = db.query(ClipMetadata).filter(ClipMetadata.clip_id == clip_id).first()
        if not meta:
            meta = metadata_generator.generate_metadata_for_clip(clip.id, db)

        # Parse draft titles
        draft_titles = []
        if meta.title_suggestions:
            try:
                draft_titles = json.loads(meta.title_suggestions)
            except Exception:
                draft_titles = [meta.title]
        if not draft_titles:
            draft_titles = [meta.title]

        # Check copyright export authorization
        perm = db.query(RecordingPermission).filter(RecordingPermission.recording_id == clip.recording_id).first()
        can_export = perm.can_export if perm else False

        # Build initial checklist
        checklist = {
            "aspect_ratio_verified": clip.aspect_ratio == "9:16",
            "resolution_1080x1920": clip.resolution == "1080x1920",
            "audio_normalized": True,
            "copyright_cleared": can_export,
            "thumbnail_ready": bool(clip.thumbnail_path),
            "hook_configured": bool(meta.hook),
            "title_under_100_chars": len(meta.title) <= 100,
            "description_with_tags": "#" in meta.description or "#" in meta.hashtags,
            "user_approved": clip.is_approved,
        }

        status = PublishingStatusEnum.READY if (clip.is_approved and can_export) else PublishingStatusEnum.DRAFT

        item = PublishingItem(
            clip_id=clip_id,
            active_title=meta.title,
            description=meta.description,
            hashtags=meta.hashtags,
            hook=meta.hook,
            thumbnail_text=meta.thumbnail_text,
            pinned_comment=meta.pinned_comment,
            draft_titles_json=json.dumps(draft_titles),
            status=status,
            planned_publish_date=None,
            published_at=None,
            youtube_video_id=None,
            youtube_video_url=None,
            checklist_json=json.dumps(checklist),
            views_count=0,
            likes_count=0,
            comments_count=0,
            shares_count=0,
            watch_time_hours=0.0,
            avg_view_duration_pct=0.0,
            analytics_source="manual",
            last_analytics_sync=None,
            notes=None,
        )
        db.add(item)
        db.commit()
        db.refresh(item)
        return item

    def update_publishing_item(
        self,
        db: Session,
        clip_id: int,
        req: PublishingItemUpdateRequest
    ) -> PublishingItem:
        """Update active metadata, draft selection, planned schedule, and checklist."""
        item = self.get_or_create_publishing_item(db, clip_id)

        if req.active_title is not None:
            item.active_title = req.active_title.strip()
        if req.description is not None:
            item.description = req.description.strip()
        if req.hashtags is not None:
            item.hashtags = req.hashtags.strip()
        if req.hook is not None:
            item.hook = req.hook.strip()
        if req.thumbnail_text is not None:
            item.thumbnail_text = req.thumbnail_text.strip()
        if req.pinned_comment is not None:
            item.pinned_comment = req.pinned_comment.strip()
        if req.status is not None:
            item.status = req.status
            if req.status == "published" and not item.published_at:
                item.published_at = datetime.now(timezone.utc)
        if req.planned_publish_date is not None:
            item.planned_publish_date = req.planned_publish_date
        if req.youtube_video_id is not None:
            item.youtube_video_id = req.youtube_video_id.strip()
            item.youtube_video_url = f"https://youtube.com/shorts/{req.youtube_video_id.strip()}"
        if req.youtube_video_url is not None:
            item.youtube_video_url = req.youtube_video_url.strip()
        if req.notes is not None:
            item.notes = req.notes.strip()

        # Update checklist items if provided
        if req.checklist_updates:
            current_checklist = json.loads(item.checklist_json) if item.checklist_json else dict(DEFAULT_CHECKLIST)
            current_checklist.update(req.checklist_updates)
            item.checklist_json = json.dumps(current_checklist)

        db.commit()
        db.refresh(item)
        return item

    def update_metrics(
        self,
        db: Session,
        clip_id: int,
        req: PublishingMetricsUpdateRequest
    ) -> PublishingItem:
        """Update manual performance metrics (Views, Likes, Comments, Shares, Watch Time)."""
        item = self.get_or_create_publishing_item(db, clip_id)

        if req.views_count is not None:
            item.views_count = max(0, req.views_count)
        if req.likes_count is not None:
            item.likes_count = max(0, req.likes_count)
        if req.comments_count is not None:
            item.comments_count = max(0, req.comments_count)
        if req.shares_count is not None:
            item.shares_count = max(0, req.shares_count)
        if req.watch_time_hours is not None:
            item.watch_time_hours = max(0.0, req.watch_time_hours)
        if req.avg_view_duration_pct is not None:
            item.avg_view_duration_pct = max(0.0, min(200.0, req.avg_view_duration_pct))
        if req.analytics_source is not None:
            item.analytics_source = req.analytics_source

        item.last_analytics_sync = datetime.now(timezone.utc)
        db.commit()
        db.refresh(item)
        return item

    def sync_simulated_analytics(self, db: Session, clip_id: int) -> PublishingItem:
        """Simulate realistic YouTube Shorts performance data based on duration and engagement."""
        import random
        item = self.get_or_create_publishing_item(db, clip_id)
        clip = item.clip

        # Baseline views between 1,200 and 24,000
        views = random.randint(1200, 24500)
        likes = int(views * random.uniform(0.045, 0.092))
        comments = int(likes * random.uniform(0.02, 0.06))
        shares = int(likes * random.uniform(0.015, 0.05))
        duration_sec = clip.duration or 30.0
        avg_retention_pct = random.uniform(68.0, 104.0)  # Shorts often loop > 100%
        watch_time_hours = round((views * (duration_sec * (avg_retention_pct / 100.0))) / 3600.0, 2)

        item.views_count = views
        item.likes_count = likes
        item.comments_count = comments
        item.shares_count = shares
        item.watch_time_hours = watch_time_hours
        item.avg_view_duration_pct = round(avg_retention_pct, 1)
        item.analytics_source = "simulated"
        item.last_analytics_sync = datetime.now(timezone.utc)
        item.status = PublishingStatusEnum.PUBLISHED
        if not item.published_at:
            item.published_at = datetime.now(timezone.utc)

        db.commit()
        db.refresh(item)
        return item

    def get_summary(self, db: Session) -> PublishingWorkspaceSummary:
        """Calculate aggregate performance and publishing status metrics."""
        items = db.query(PublishingItem).all()
        total = len(items)

        draft_c = sum(1 for i in items if i.status == "draft")
        ready_c = sum(1 for i in items if i.status == "ready")
        sched_c = sum(1 for i in items if i.status == "scheduled")
        pub_c = sum(1 for i in items if i.status == "published")
        arch_c = sum(1 for i in items if i.status == "archived")

        total_v = sum(i.views_count for i in items)
        total_l = sum(i.likes_count for i in items)
        total_wh = round(sum(i.watch_time_hours for i in items), 2)
        avg_ctr = round((total_l / total_v * 100.0), 2) if total_v > 0 else 0.0

        return PublishingWorkspaceSummary(
            total_items=total,
            draft_count=draft_c,
            ready_count=ready_c,
            scheduled_count=sched_c,
            published_count=pub_c,
            archived_count=arch_c,
            total_views=total_v,
            total_likes=total_l,
            total_watch_hours=total_wh,
            avg_performance_ctr=avg_ctr,
        )

    def to_response(self, item: PublishingItem) -> PublishingItemResponse:
        """Convert database model to Pydantic response."""
        drafts = []
        if item.draft_titles_json:
            try:
                drafts = json.loads(item.draft_titles_json)
            except Exception:
                drafts = [item.active_title]

        checklist = dict(DEFAULT_CHECKLIST)
        if item.checklist_json:
            try:
                checklist = json.loads(item.checklist_json)
            except Exception:
                pass

        total_checks = len(checklist)
        passed_checks = sum(1 for v in checklist.values() if v)
        completion_pct = round((passed_checks / total_checks * 100.0), 1) if total_checks > 0 else 0.0

        clip = item.clip

        ctr = round((item.likes_count / item.views_count * 100.0), 2) if item.views_count > 0 else 0.0

        metrics = PerformanceMetrics(
            views_count=item.views_count,
            likes_count=item.likes_count,
            comments_count=item.comments_count,
            shares_count=item.shares_count,
            watch_time_hours=item.watch_time_hours,
            avg_view_duration_pct=item.avg_view_duration_pct,
            ctr_pct=ctr,
        )

        return PublishingItemResponse(
            id=item.id,
            clip_id=item.clip_id,
            recording_id=clip.recording_id if clip else None,
            active_title=item.active_title,
            description=item.description,
            hashtags=item.hashtags,
            hook=item.hook,
            thumbnail_text=item.thumbnail_text,
            pinned_comment=item.pinned_comment,
            draft_titles=drafts,
            status=item.status,
            planned_publish_date=item.planned_publish_date,
            published_at=item.published_at,
            youtube_video_id=item.youtube_video_id,
            youtube_video_url=item.youtube_video_url,
            checklist=checklist,
            checklist_completion_pct=completion_pct,
            metrics=metrics,
            analytics_source=item.analytics_source,
            last_analytics_sync=item.last_analytics_sync,
            notes=item.notes,
            duration=clip.duration if clip else None,
            preset_name=clip.preset_name if clip else None,
            thumbnail_url=f"/api/clips/{item.clip_id}/thumbnail",
            clip_download_url=f"/api/clips/{item.clip_id}/download",
            srt_download_url=f"/api/exports/clips/{item.clip_id}/subtitles.srt",
            txt_download_url=f"/api/exports/clips/{item.clip_id}/transcript.txt",
            created_at=item.created_at,
            updated_at=item.updated_at,
        )

publishing_service = PublishingService()
