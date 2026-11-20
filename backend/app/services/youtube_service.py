import os
import re
import uuid
import time
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List
from datetime import datetime

import yt_dlp
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal
from ..models.recording import Recording, RecordingStatus
from ..models.job import Job, JobType, JobStatus
from ..models.recording_permission import RecordingPermission, PermissionStatusEnum, RiskLevelEnum
from ..services.video_service import validate_video, calculate_file_hash
from ..services.settings_service import get_watcher_settings

class YouTubeTask:
    def __init__(self, task_id: str, url: str, auto_generate_shorts: bool = True, notes: str = "", has_permission: bool = False, creator_name: Optional[str] = None):
        self.task_id = task_id
        self.url = url
        self.auto_generate_shorts = auto_generate_shorts
        self.notes = notes
        self.has_permission = has_permission
        self.creator_name = creator_name
        self.title: str = ""
        self.uploader: str = ""
        self.thumbnail: str = ""
        self.duration_seconds: float = 0.0
        self.status: str = "pending"  # pending, downloading, processing, analyzing, completed, failed, cancelled
        self.progress: float = 0.0
        self.downloaded_bytes: int = 0
        self.total_bytes: int = 0
        self.speed_str: str = ""
        self.eta_seconds: int = 0
        self.message: str = "Queued for download..."
        self.recording_id: Optional[int] = None
        self.job_id: Optional[int] = None
        self.error: Optional[str] = None
        self.created_at = datetime.utcnow()
        self.completed_at: Optional[datetime] = None
        self._cancelled = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "url": self.url,
            "title": self.title,
            "uploader": self.uploader,
            "thumbnail": self.thumbnail,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "progress": round(self.progress, 1),
            "downloaded_bytes": self.downloaded_bytes,
            "total_bytes": self.total_bytes,
            "speed_str": self.speed_str,
            "eta_seconds": self.eta_seconds,
            "message": self.message,
            "recording_id": self.recording_id,
            "job_id": self.job_id,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }

class YouTubeService:
    def __init__(self):
        self._tasks: Dict[str, YouTubeTask] = {}
        self._lock = threading.Lock()

    def _get_base_ydl_opts(self) -> Dict[str, Any]:
        """Base yt-dlp options configured with Mobile player clients to bypass datacenter bot checks."""
        import shutil
        opts: Dict[str, Any] = {
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'ios']
                }
            },
        }
        ffmpeg_bin = shutil.which("ffmpeg") or settings.FFMPEG_PATH
        if ffmpeg_bin and Path(ffmpeg_bin).exists():
            opts['ffmpeg_location'] = str(Path(ffmpeg_bin).parent)
        node_bin = shutil.which("node") or "C:/Program Files/nodejs/node.exe"
        if node_bin and Path(node_bin).exists():
            opts['js_runtimes'] = {'node': {'path': str(node_bin)}}
        return opts

    def is_valid_youtube_url(self, url: str) -> bool:
        """Validate if the string is a recognized YouTube URL format."""
        if not url or not isinstance(url, str):
            return False
        clean = url.strip()
        patterns = [
            r'^(https?://)?(www\.)?(youtube\.com/watch\?v=|youtu\.be/|youtube\.com/shorts/|youtube\.com/embed/|youtube\.com/live/)[A-Za-z0-9_-]+',
            r'^(https?://)?(m\.)?youtube\.com/watch\?v=[A-Za-z0-9_-]+',
            r'^(https?://)?(www\.)?youtube\.com/clip/[A-Za-z0-9_-]+',
        ]
        return any(re.match(pat, clean) for pat in patterns)

    def extract_info(self, url: str) -> Dict[str, Any]:
        """
        Extract video metadata without downloading the full video.
        Used for instant preview in the UI before download.
        """
        url = url.strip()
        ydl_opts = self._get_base_ydl_opts()
        ydl_opts['extract_flat'] = False
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                if not info:
                    raise ValueError("Could not extract video metadata from the provided URL.")
                
                duration = float(info.get('duration') or 0.0)
                minutes = int(duration // 60)
                seconds = int(duration % 60)
                hours = int(minutes // 60)
                if hours > 0:
                    minutes = int(minutes % 60)
                    duration_formatted = f"{hours}:{minutes:02d}:{seconds:02d}"
                else:
                    duration_formatted = f"{minutes}:{seconds:02d}"

                return {
                    "url": url,
                    "video_id": info.get('id', ''),
                    "title": info.get('title', 'Unknown Title'),
                    "uploader": info.get('uploader') or info.get('channel') or 'Unknown Creator',
                    "channel_url": info.get('channel_url') or info.get('uploader_url', ''),
                    "duration_seconds": duration,
                    "duration_formatted": duration_formatted,
                    "thumbnail": info.get('thumbnail', ''),
                    "view_count": info.get('view_count', 0),
                    "description": (info.get('description') or '')[:300],
                    "resolution": f"{info.get('width', 1920)}x{info.get('height', 1080)}",
                    "fps": info.get('fps', 60),
                }
        except Exception as e:
            raise RuntimeError(f"Failed to fetch YouTube video info: {str(e)}")

    def create_download_task(
        self,
        url: str,
        auto_generate_shorts: bool = True,
        notes: str = "",
        has_permission: bool = False,
        creator_name: Optional[str] = None
    ) -> YouTubeTask:
        """Create and queue a download task."""
        task_id = str(uuid.uuid4())
        task = YouTubeTask(
            task_id=task_id,
            url=url.strip(),
            auto_generate_shorts=auto_generate_shorts,
            notes=notes,
            has_permission=has_permission,
            creator_name=creator_name
        )
        with self._lock:
            self._tasks[task_id] = task

        thread = threading.Thread(
            target=self._run_download,
            args=(task,),
            daemon=True,
            name=f"YTDownload-{task_id[:8]}"
        )
        thread.start()
        return task

    def get_task(self, task_id: str) -> Optional[YouTubeTask]:
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            tasks = list(self._tasks.values())
        tasks.sort(key=lambda t: t.created_at, reverse=True)
        return [t.to_dict() for t in tasks[:limit]]

    def cancel_task(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return False
            if task.status in ["completed", "failed", "cancelled"]:
                return False
            task._cancelled = True
            task.status = "cancelled"
            task.message = "Download cancelled by user"
            return True

    def _run_download(self, task: YouTubeTask):
        """Worker thread to execute yt-dlp download, validation, database insertion, and pipeline triggering."""
        task.status = "downloading"
        task.message = "Connecting to YouTube and preparing stream..."
        recordings_dir = Path(settings.RECORDINGS_DIR).resolve()
        recordings_dir.mkdir(parents=True, exist_ok=True)

        downloaded_file_path: Optional[Path] = None

        def progress_hook(d: Dict[str, Any]):
            if task._cancelled:
                raise yt_dlp.utils.DownloadCancelled("Download cancelled by user")

            status = d.get('status')
            if status == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes') or 0
                speed = d.get('speed') or 0
                eta = d.get('eta') or 0

                task.total_bytes = total
                task.downloaded_bytes = downloaded
                task.eta_seconds = int(eta) if eta else 0

                if total > 0:
                    pct = (downloaded / total) * 100.0
                    task.progress = min(pct, 99.0)

                if speed:
                    mb_speed = speed / (1024 * 1024)
                    task.speed_str = f"{mb_speed:.1f} MB/s"
                else:
                    task.speed_str = "--"

                task.message = f"Downloading: {task.progress:.1f}% ({task.speed_str}) - {task.eta_seconds}s left"

            elif status == 'finished':
                task.progress = 99.0
                task.status = "processing"
                task.message = "Download finished. Merging high-quality audio and video streams..."
                fn = d.get('filename')
                if fn:
                    nonlocal downloaded_file_path
                    downloaded_file_path = Path(fn)

        ydl_opts = self._get_base_ydl_opts()
        ydl_opts.update({
            'format': '18/bestvideo*+bestaudio/best',
            'merge_output_format': 'mp4',
            'outtmpl': str(recordings_dir / 'yt_%(id)s.%(ext)s'),
            'restrictfilenames': True,
            'windowsfilenames': True,
            'retries': 10,
            'fragment_retries': 10,
            'continuedl': True,
            'progress_hooks': [progress_hook],
        })

        try:
            info = None
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(task.url, download=True)
            except Exception as e:
                task.message = "Retrying with mobile Android stream resolver..."
                ydl_opts['extractor_args'] = {'youtube': {'player_client': ['android']}}
                ydl_opts['format'] = '18/best'
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(task.url, download=True)

            if not info:
                raise RuntimeError("Failed to download video: No stream returned.")

            task.title = info.get('title', 'YouTube Video')
            task.uploader = task.creator_name or info.get('uploader') or info.get('channel') or 'YouTube Creator'
            task.thumbnail = info.get('thumbnail', '')
            task.duration_seconds = float(info.get('duration') or 0.0)

            # Determine final merged file path
            possible_path = ydl.prepare_filename(info)
            final_path = Path(possible_path)
            # If merged into mp4, extension might be .mp4
            if not final_path.exists():
                mp4_variant = final_path.with_suffix('.mp4')
                if mp4_variant.exists():
                    final_path = mp4_variant
                elif downloaded_file_path and downloaded_file_path.exists():
                    final_path = downloaded_file_path
                else:
                    # Find recently created file matching video id in recordings_dir
                    vid_id = info.get('id', '')
                    candidates = list(recordings_dir.glob(f"yt_{vid_id}*.*"))
                    if candidates:
                        final_path = candidates[0]
                    else:
                        raise FileNotFoundError(f"Downloaded output file not found at {final_path}")

            if task._cancelled:
                task.status = "cancelled"
                task.message = "Cancelled by user"
                return

            task.status = "processing"
            task.progress = 99.5
            task.message = "Validating video with FFprobe..."

            # 1. Validate video metadata with FFprobe
            meta = validate_video(str(final_path))

            # 2. Compute file hash
            file_hash = calculate_file_hash(str(final_path))

            # 3. Insert into Database
            db = SessionLocal()
            try:
                # Check duplicate
                existing = db.query(Recording).filter(
                    (Recording.file_hash == file_hash) | (Recording.file_path == str(final_path))
                ).first()

                if existing:
                    rec = existing
                    rec_notes = rec.notes or ""
                    if "Imported from YouTube" not in rec_notes:
                        rec.notes = f"{rec_notes} | Imported from YouTube: {task.url}".strip(" |")
                        db.commit()
                else:
                    rec = Recording(
                        filename=final_path.name,
                        original_filename=f"{task.title}.mp4",
                        file_path=str(final_path),
                        file_size_bytes=meta["file_size_bytes"],
                        duration_seconds=meta["duration_seconds"],
                        resolution=meta["resolution"],
                        fps=meta["fps"],
                        file_hash=file_hash,
                        video_codec=meta["video_codec"],
                        bitrate=meta["bitrate"],
                        status=RecordingStatus.PENDING,
                        notes=f"Imported from YouTube: {task.url} | Creator: {task.uploader}. {task.notes}".strip(),
                    )
                    db.add(rec)
                    db.commit()
                    db.refresh(rec)

                task.recording_id = rec.id

                # 4. Phase 9 Copyright & Permission Auto-linking
                perm = db.query(RecordingPermission).filter(RecordingPermission.recording_id == rec.id).first()
                if not perm:
                    perm_status = PermissionStatusEnum.GRANTED if task.has_permission else PermissionStatusEnum.PENDING
                    perm = RecordingPermission(
                        recording_id=rec.id,
                        original_creator=task.uploader,
                        source_url=task.url,
                        written_permission_evidence="Direct YouTube link import by user" if task.has_permission else None,
                        permission_status=perm_status,
                        editing_permission=True,
                        redistribution_permission=task.has_permission,
                        commercial_monetization_permission=False,
                        overall_risk_level=RiskLevelEnum.LOW if task.has_permission else RiskLevelEnum.MEDIUM,
                        can_export=True,
                    )
                    db.add(perm)
                    db.commit()

                # 5. Automatically kick off AI Pipeline for Short Generation
                if task.auto_generate_shorts:
                    task.status = "analyzing"
                    task.message = "Queuing AI moment detection and Shorts generator..."
                    
                    analysis_job = Job(
                        recording_id=rec.id,
                        job_type=JobType.ANALYSIS,
                        status=JobStatus.PENDING,
                        progress=0.0,
                        message="Auto Pipeline: AI moment detection & vertical Shorts generator",
                    )
                    db.add(analysis_job)
                    db.commit()
                    db.refresh(analysis_job)
                    task.job_id = analysis_job.id

                task.status = "completed"
                task.progress = 100.0
                task.completed_at = datetime.utcnow()
                task.message = f"Successfully downloaded and started Shorts pipeline for '{task.title}'!"

            except Exception as dbe:
                db.rollback()
                raise dbe
            finally:
                db.close()

        except yt_dlp.utils.DownloadCancelled:
            task.status = "cancelled"
            task.message = "Download cancelled by user"
        except Exception as e:
            task.status = "failed"
            task.error = str(e)
            task.message = f"Download failed: {str(e)}"
            print(f"❌ [YouTubeService] Error downloading {task.url}: {e}")

youtube_service = YouTubeService()
