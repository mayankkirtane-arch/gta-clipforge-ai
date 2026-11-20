import os
import threading
import time
from pathlib import Path
from typing import Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileCreatedEvent, FileMovedEvent

from ..config import settings
from ..database import SessionLocal
from ..models.recording import Recording, RecordingStatus
from ..models.job import Job, JobType, JobStatus
from .video_service import (
    wait_until_file_ready,
    validate_video,
    calculate_file_hash,
)
from .settings_service import get_watcher_settings

class RecordingFileHandler(FileSystemEventHandler):
    def __init__(self, watcher):
        super().__init__()
        self.watcher = watcher

    def on_created(self, event):
        if not event.is_directory:
            self.watcher.handle_new_file(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self.watcher.handle_new_file(event.dest_path)


class FolderWatcherService:
    def __init__(self):
        self.observer: Optional[Observer] = None
        self.watch_path: str = settings.WATCH_DIR
        self.is_running: bool = False
        self._processing_files: Set[str] = set()
        self._lock = threading.Lock()

    def start(self, watch_path: Optional[str] = None):
        """Start the watchdog observer."""
        if self.is_running:
            return

        if watch_path:
            self.watch_path = str(Path(watch_path).resolve())
        else:
            app_settings = get_watcher_settings()
            self.watch_path = str(Path(app_settings.get("watch_folder_path", settings.WATCH_DIR)).resolve())

        # Ensure directory exists
        Path(self.watch_path).mkdir(parents=True, exist_ok=True)

        event_handler = RecordingFileHandler(self)
        self.observer = Observer()
        self.observer.schedule(event_handler, path=self.watch_path, recursive=False)
        self.observer.start()
        self.is_running = True
        print(f"👀 Watchdog folder observer started on: {self.watch_path}")

        # Auto scan existing recordings on start
        threading.Thread(target=self.scan_folder_now, daemon=True, name="InitialWatcherScan").start()

    def stop(self):
        """Stop the watchdog observer."""
        if self.observer and self.is_running:
            self.observer.stop()
            self.observer.join(timeout=3.0)
            self.is_running = False
            self.observer = None
            print("🛑 Watchdog folder observer stopped")

    def is_paused(self) -> bool:
        settings_dict = get_watcher_settings()
        return bool(settings_dict.get("monitoring_paused", False))

    def pause(self):
        from .settings_service import update_watcher_settings
        update_watcher_settings({"monitoring_paused": True})
        print("⏸️ Folder watcher monitoring paused")

    def resume(self):
        from .settings_service import update_watcher_settings
        update_watcher_settings({"monitoring_paused": False})
        print("▶️ Folder watcher monitoring resumed")

    def handle_new_file(self, file_path: str):
        """Invoked when a new file appears in the watch folder."""
        # 1. Detect the new file
        path = Path(file_path)
        ext = path.suffix.lower()

        # Filter supported extensions and ignore temp/hidden files
        if ext not in settings.ALLOWED_EXTENSIONS:
            return
        if path.name.startswith((".", "~", "tmp_")):
            return

        # Check if monitoring is paused
        if self.is_paused():
            print(f"⏸️ Watcher paused. Ignored new file: {path.name}")
            return

        # Run file processing in background thread
        thread = threading.Thread(
            target=self._process_detected_file,
            args=(str(path.resolve()),),
            daemon=True,
            name=f"ProcessFile-{path.name}"
        )
        thread.start()

    def _process_detected_file(self, file_path: str) -> Optional[Recording]:
        """
        Executes the 8-step workflow for a newly detected video:
        1. Detect the new file.
        2. Wait until the file has finished copying.
        3. Validate the video using FFprobe.
        4. Extract video metadata.
        5. Calculate a file hash.
        6. Check for duplicates.
        7. Add the recording to SQLite.
        8. Add a job to the processing queue.
        """
        with self._lock:
            if file_path in self._processing_files:
                return None
            self._processing_files.add(file_path)

        try:
            path = Path(file_path)
            print(f"[Watcher Step 1] Detected new file: {path.name}")

            # 2. Wait until the file has finished copying
            print(f"[Watcher Step 2] Waiting for file copy completion: {path.name}...")
            is_ready = wait_until_file_ready(file_path, timeout_seconds=60)
            if not is_ready:
                print(f"[Watcher Warning] File was not ready or locked: {path.name}")
                return None

            # 3 & 4. Validate video using FFprobe & Extract video metadata
            print(f"[Watcher Step 3 & 4] Validating video and extracting metadata via FFprobe...")
            meta = None
            for attempt in range(4):
                try:
                    meta = validate_video(file_path)
                    break
                except Exception as e:
                    err_str = str(e)
                    if attempt < 3 and ("moov atom" in err_str or "Invalid data" in err_str or "locked" in err_str):
                        time.sleep(1.5)
                        continue
                    print(f"[Watcher Error] FFprobe validation failed for {path.name}: {e}")
                    return None

            # 5. Calculate a file hash
            print(f"[Watcher Step 5] Calculating file hash...")
            file_hash = calculate_file_hash(file_path)

            # 6. Check for duplicates in SQLite
            print(f"[Watcher Step 6] Checking for duplicates (hash: {file_hash[:12]}...)...")
            db = SessionLocal()
            try:
                norm_path = str(Path(file_path).resolve())
                existing = db.query(Recording).filter(
                    (Recording.file_hash == file_hash) | (Recording.file_path == norm_path)
                ).first()

                if existing:
                    print(f"[Watcher Info] Duplicate detected: Recording ID {existing.id} already exists ({existing.filename}). Skipping.")
                    return existing

                # 7. Add the recording to SQLite
                print(f"[Watcher Step 7] Adding recording to SQLite...")
                recording = Recording(
                    filename=path.name,
                    original_filename=path.name,
                    file_path=norm_path,
                    file_size_bytes=meta["file_size_bytes"],
                    duration_seconds=meta["duration_seconds"],
                    resolution=meta["resolution"],
                    fps=meta["fps"],
                    file_hash=file_hash,
                    video_codec=meta["video_codec"],
                    bitrate=meta["bitrate"],
                    status=RecordingStatus.PENDING,
                    notes="Imported via GTA6_RECORDINGS automatic folder watcher",
                )
                db.add(recording)
                db.commit()
                db.refresh(recording)
                print(f"[Watcher Success] Recording #{recording.id} ({recording.filename}) added to database.")

                # Phase 9/10 Step: Initialize creator permission check & copyright compliance record
                try:
                    from .copyright_risk_service import copyright_risk_service
                    copyright_risk_service.get_or_create_permission(db, recording.id)
                except Exception as perm_ex:
                    print(f"[Watcher Warning] Failed to initialize permission for #{recording.id}: {perm_ex}")

                # 8. Add a job to the processing queue
                print(f"[Watcher Step 8] Adding analysis job to processing queue...")
                job = Job(
                    recording_id=recording.id,
                    job_type=JobType.ANALYSIS,
                    status=JobStatus.PENDING,
                    progress=0.0,
                    message="Queued for AI analysis by automatic folder watcher",
                )
                db.add(job)
                db.commit()
                db.refresh(job)
                print(f"[Watcher Success] Job #{job.id} enqueued for Recording #{recording.id}.")

                return recording

            finally:
                db.close()

        except Exception as e:
            print(f"[Watcher Error] Unexpected error processing {file_path}: {e}")
            return None
        finally:
            with self._lock:
                self._processing_files.discard(file_path)

    def scan_folder_now(self) -> int:
        """Manually trigger a scan of the watch directory for any unindexed videos."""
        folder = Path(self.watch_path)
        if not folder.exists() or not folder.is_dir():
            return 0

        found_count = 0
        for item in folder.iterdir():
            if item.is_file() and item.suffix.lower() in settings.ALLOWED_EXTENSIONS:
                if not item.name.startswith((".", "~", "tmp_")):
                    rec = self._process_detected_file(str(item.resolve()))
                    if rec:
                        found_count += 1
        return found_count


folder_watcher = FolderWatcherService()
