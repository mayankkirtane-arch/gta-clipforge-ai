import threading
import time
import traceback
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import or_
from ..database import SessionLocal
from ..models.job import Job, JobStatus, JobType
from ..models.recording import Recording, RecordingStatus
from .settings_service import get_watcher_settings

class JobWorker:
    def __init__(self):
        self._stop_event = threading.Event()
        self._thread = None
        self._current_job_id = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._recover_interrupted_jobs()
        self._thread = threading.Thread(target=self._run_loop, daemon=True, name="JobWorkerThread")
        self._thread.start()
        print("🚀 Background Job Worker started")

    def stop(self):
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=3.0)
        print("🛑 Background Job Worker stopped")

    def _recover_interrupted_jobs(self):
        """Recover jobs left in RUNNING/PROCESSING state from a prior crash or server restart."""
        db = SessionLocal()
        try:
            interrupted = db.query(Job).filter(
                or_(Job.status == JobStatus.RUNNING, Job.status == JobStatus.PROCESSING)
            ).all()
            for job in interrupted:
                job.status = JobStatus.FAILED
                job.error = "Interrupted by server restart"
                job.message = "Job failed due to server restart. Click Retry to reprocess."
                if job.recording_id:
                    rec = db.query(Recording).filter(Recording.id == job.recording_id).first()
                    if rec and rec.status == RecordingStatus.ANALYZING:
                        rec.status = RecordingStatus.FAILED
            db.commit()
            if interrupted:
                print(f"⚠️ Recovered {len(interrupted)} interrupted jobs from prior session.")
        except Exception as e:
            print(f"Error during job recovery: {e}")
            db.rollback()
        finally:
            db.close()

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                job_id = self._fetch_next_job_id()
                if job_id:
                    self._process_job(job_id)
                else:
                    time.sleep(1.0)
            except Exception as e:
                print(f"Error in job worker loop: {e}")
                time.sleep(2.0)

    def _fetch_next_job_id(self):
        db = SessionLocal()
        try:
            job = db.query(Job).filter(
                or_(Job.status == JobStatus.PENDING, Job.status == JobStatus.QUEUED)
            ).order_by(Job.created_at.asc()).first()
            return job.id if job else None
        finally:
            db.close()

    def _update_job_progress(self, job_id: int, progress: float, message: str, status: JobStatus = None):
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                return False
            # Check if user cancelled while running
            if job.status == JobStatus.CANCELLED:
                return False
            job.progress = round(progress, 1)
            job.message = message
            if status:
                job.status = status
            db.commit()
            return True
        finally:
            db.close()

    def _process_job(self, job_id: int):
        self._current_job_id = job_id
        db = SessionLocal()
        job = None
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job or job.status == JobStatus.CANCELLED:
                return

            # Check if auto mode is disabled and job is queued
            app_settings = get_watcher_settings(db)
            if not app_settings.get("enable_auto_mode", True) and not app_settings.get("auto_analyze", True):
                # Auto analyze is turned off, leave in pending until manually triggered
                return

            job.status = JobStatus.PROCESSING
            job.started_at = datetime.utcnow()
            job.progress = 5.0
            job.message = "Initializing job processing..."
            db.commit()

            recording = None
            if job.recording_id:
                recording = db.query(Recording).filter(Recording.id == job.recording_id).first()

            # Execute based on job type
            if job.job_type == JobType.ANALYSIS:
                if recording:
                    recording.status = RecordingStatus.ANALYZING
                    db.commit()
                self._execute_analysis_job(job_id, recording)
            elif job.job_type == JobType.MOMENT_DETECTION:
                self._execute_moment_detection_job(job_id, recording)
            elif job.job_type == JobType.CLIP_RANKING:
                self._execute_clip_ranking_job(job_id, recording)
            elif job.job_type == JobType.CLIP_GENERATION:
                self._execute_clip_generation_job(job_id, recording)
            else:
                self._execute_generic_job(job_id)

        except Exception as e:
            traceback.print_exc()
            self._handle_job_failure(job_id, str(e))
        finally:
            self._current_job_id = None
            db.close()

    def _execute_analysis_job(self, job_id: int, recording: Recording):
        from .video_engine import video_engine

        def progress_cb(pct: float, msg: str):
            self._update_job_progress(job_id, pct, msg)

        if recording:
            # Execute real chunk-based professional video engine pipeline
            res = video_engine.process_recording(
                recording.id,
                progress_callback=progress_cb,
                cancel_event=self._stop_event
            )
            if res.get("status") == "cancelled":
                print(f"Job {job_id} cancelled during video engine processing.")
                return

        # Mark completed
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and job.status != JobStatus.CANCELLED:
                job.status = JobStatus.COMPLETED
                job.progress = 100.0
                job.completed_at = datetime.utcnow()
                job.message = "Analysis completed successfully"

                if job.recording_id:
                    rec = db.query(Recording).filter(Recording.id == job.recording_id).first()
                    if rec:
                        rec.status = RecordingStatus.ANALYZED
                        print(f"🎉 [Worker] Recording #{rec.id} marked as ANALYZED")

                # Automatically queue specialized moment detection for clean gameplay
                app_settings = get_watcher_settings(db)
                if app_settings.get("auto_detect_moments", True):
                    next_job = Job(
                        recording_id=job.recording_id,
                        job_type=JobType.MOMENT_DETECTION,
                        status=JobStatus.PENDING,
                        progress=0.0,
                        message="Queued for GTA 6 specialized moment detection",
                    )
                    db.add(next_job)
                db.commit()
        finally:
            db.close()

    def _execute_moment_detection_job(self, job_id: int, recording: Recording):
        from .gta_detector import gta_detector

        def progress_cb(pct: float, msg: str):
            self._update_job_progress(job_id, pct, msg)

        if recording:
            results = gta_detector.detect_moments_for_recording(
                recording_id=recording.id,
                sensitivity="medium",
                progress_cb=progress_cb,
            )

        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and job.status != JobStatus.CANCELLED:
                job.status = JobStatus.COMPLETED
                job.progress = 100.0
                job.completed_at = datetime.utcnow()
                count = len(results) if recording else 0
                job.message = f"Detected {count} GTA 6 gameplay moments."
                
                # Auto queue AI Clip Ranking & Selection
                if recording:
                    rank_job = Job(
                        recording_id=recording.id,
                        job_type=JobType.CLIP_RANKING,
                        status=JobStatus.PENDING,
                        progress=0.0,
                        message="Queued for AI clip ranking and intelligent boundary selection",
                    )
                    db.add(rank_job)
                db.commit()
        finally:
            db.close()

    def _execute_clip_ranking_job(self, job_id: int, recording: Recording):
        from .clip_ranker import clip_ranker

        def progress_cb(pct: float, msg: str):
            self._update_job_progress(job_id, pct, msg)

        results = []
        if recording:
            results = clip_ranker.generate_ranked_candidates(
                recording_id=recording.id,
                progress_cb=progress_cb,
            )

        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and job.status != JobStatus.CANCELLED:
                job.status = JobStatus.COMPLETED
                job.progress = 100.0
                job.completed_at = datetime.utcnow()
                top_score = results[0]["ai_score"] if results else 0
                job.message = f"Ranked {len(results)} candidate clips (Top Score: {top_score}/100)."

                # Auto Mode Step 7: Queue Shorts generation for ranked candidates
                app_settings = get_watcher_settings(db)
                if recording and app_settings.get("auto_generate_clips", True) and len(results) > 0:
                    gen_job = Job(
                        recording_id=recording.id,
                        job_type=JobType.CLIP_GENERATION,
                        status=JobStatus.PENDING,
                        progress=0.0,
                        message=f"Auto Mode: Queued Shorts generation for {len(results)} ranked moments",
                    )
                    db.add(gen_job)
                db.commit()
        finally:
            db.close()

    def _execute_clip_generation_job(self, job_id: int, recording: Recording):
        from .shorts_generator import shorts_generator

        def progress_cb(pct: float, msg: str):
            self._update_job_progress(job_id, pct, msg)

        results = []
        if recording:
            results = shorts_generator.generate_shorts_batch(
                recording_id=recording.id,
                render_mode="blurred_background",
                progress_cb=progress_cb,
                cancel_event=self._stop_event,
            )

        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and job.status != JobStatus.CANCELLED:
                job.status = JobStatus.COMPLETED
                job.progress = 100.0
                job.completed_at = datetime.utcnow()
                success_count = sum(1 for r in results if r.get("clip_id"))
                job.message = f"Successfully generated {success_count} YouTube Shorts in GTA6_SHORTS."

                if recording and success_count > 0:
                    from .metadata_generator import metadata_generator
                    from .publishing_service import publishing_service
                    from .export_service import export_service

                    # Auto Mode Steps 8, 9, 10:
                    # 8. Prepare editing and metadata for each generated clip
                    # 9. Create copyright report in GTA6_REPORTS
                    # 10. Send clips for approval (status remains GENERATED / unapproved, requiring user approval)
                    for r in results:
                        cid = r.get("clip_id")
                        if cid:
                            try:
                                metadata_generator.generate_metadata_for_clip(cid, db)
                                publishing_service.get_or_create_publishing_item(db, cid)
                            except Exception as ex:
                                print(f"Auto metadata prep failed for clip #{cid}: {ex}")

                    try:
                        export_service.generate_copyright_report(db, recording.id)
                    except Exception as rep_err:
                        print(f"Auto copyright report failed for Recording #{recording.id}: {rep_err}")

                db.commit()
        finally:
            db.close()

    def _execute_generic_job(self, job_id: int):
        for pct in [25.0, 50.0, 75.0, 100.0]:
            time.sleep(0.5)
            self._update_job_progress(job_id, pct, f"Processing... {int(pct)}%")
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job and job.status != JobStatus.CANCELLED:
                job.status = JobStatus.COMPLETED
                job.completed_at = datetime.utcnow()
                db.commit()
        finally:
            db.close()

    def _handle_job_failure(self, job_id: int, error_msg: str):
        db = SessionLocal()
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if job:
                job.status = JobStatus.FAILED
                job.error = error_msg
                job.message = f"Failed: {error_msg}"
                if job.recording_id:
                    rec = db.query(Recording).filter(Recording.id == job.recording_id).first()
                    if rec:
                        rec.status = RecordingStatus.FAILED
                db.commit()
        finally:
            db.close()

job_worker = JobWorker()
