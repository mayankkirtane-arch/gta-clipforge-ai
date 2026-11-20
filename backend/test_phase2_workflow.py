import os
import sys
import time
import shutil
import subprocess
from pathlib import Path

# Add backend directory to path
backend_dir = Path("D:/GTA_CLIPFORGE_AI/backend").resolve()
sys.path.insert(0, str(backend_dir))

from app.config import settings
from app.database import engine, Base, SessionLocal
from app.models.recording import Recording, RecordingStatus
from app.models.job import Job, JobStatus, JobType
from app.services.video_service import (
    validate_video,
    calculate_file_hash,
    wait_until_file_ready,
    get_ffprobe_path,
    get_ffmpeg_path,
)
from app.services.watcher_service import folder_watcher
from app.services.job_worker import job_worker
from app.services.settings_service import get_watcher_settings, update_watcher_settings

def print_banner(msg):
    print("\n" + "=" * 65)
    print(f"  {msg}")
    print("=" * 65)

def generate_test_video(output_path: str, duration: int = 4, ext: str = ".mp4"):
    """Generate a clean synthetic video using FFmpeg for testing."""
    ffmpeg = get_ffmpeg_path()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    cmd = [
        ffmpeg,
        "-y",
        "-f", "lavfi",
        "-i", f"testsrc=size=1920x1080:rate=60:duration={duration}",
        "-f", "lavfi",
        "-i", f"sine=frequency=1000:duration={duration}",
        "-c:v", "libx264" if ext in [".mp4", ".mov", ".mkv"] else "libvpx-vp9",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac" if ext in [".mp4", ".mov", ".mkv"] else "libopus",
        str(path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg failed: {res.stderr[:200]}")
    return str(path)

def test_formats():
    print_banner("TEST 1: FORMAT COMPATIBILITY & FFPROBE VALIDATION (MP4, MKV, MOV, WebM)")
    test_dir = Path("D:/GTA_CLIPFORGE_AI/temp/format_tests")
    test_dir.mkdir(parents=True, exist_ok=True)

    formats = [".mp4", ".mkv", ".mov", ".webm"]
    for ext in formats:
        test_file = test_dir / f"test_gameplay{ext}"
        print(f"-> Generating synthetic {ext} file...")
        generate_test_video(str(test_file), duration=3, ext=ext)

        meta = validate_video(str(test_file))
        file_hash = calculate_file_hash(str(test_file))
        print(f"   [SUCCESS] Format: {ext}")
        print(f"   Resolution: {meta['resolution']}, FPS: {meta['fps']}, Duration: {meta['duration_seconds']}s")
        print(f"   Size: {meta['file_size_bytes']} bytes, Codec: {meta['video_codec']}")
        print(f"   SHA-256: {file_hash[:16]}...")
        assert meta["resolution"] == "1920x1080", "Resolution mismatch"
        assert meta["fps"] == 60.0 or meta["fps"] == 59.94, "FPS mismatch"
        assert meta["duration_seconds"] is not None, "Duration missing"
        assert len(file_hash) == 64, "Invalid hash length"

def test_watcher_8_steps():
    print_banner("TEST 2: AUTOMATIC FOLDER WATCHER 8-STEP WORKFLOW")
    watch_folder = Path(settings.WATCH_DIR)
    watch_folder.mkdir(parents=True, exist_ok=True)

    # Clean existing test files in watch folder
    for f in watch_folder.glob("watcher_test_*"):
        try:
            f.unlink()
        except Exception:
            pass

    # Ensure worker and watcher are active
    job_worker.start()
    folder_watcher.start()
    folder_watcher.resume()

    # Create video in temp first, then copy to watch folder (simulating external recording copy)
    temp_source = Path("D:/GTA_CLIPFORGE_AI/temp/source_copy_test.mp4")
    print(f"-> Generating complete recording source file in temp: {temp_source.name}...")
    generate_test_video(str(temp_source), duration=4, ext=".mp4")

    dest_file = watch_folder / "watcher_test_gta6_mission.mp4"
    print(f"-> Copying recording into {watch_folder.name} to trigger watchdog: {dest_file.name}...")
    shutil.copy2(temp_source, dest_file)

    # Wait for watcher to execute 8 steps
    print("-> Waiting for automatic watcher 8-step pipeline to execute...")
    rec = None
    db = SessionLocal()
    try:
        for i in range(25):
            time.sleep(1.0)
            rec = db.query(Recording).filter(Recording.filename == dest_file.name).first()
            if rec:
                break
            print(f"   Waiting for detection... ({i+1}s)")

        assert rec is not None, "Watcher failed to add recording to SQLite within timeout!"
        print(f"   [Step 1-7 SUCCESS] Recording added to SQLite: ID={rec.id}, name={rec.filename}")
        print(f"   Resolution: {rec.resolution}, FPS: {rec.fps}, Duration: {rec.duration_seconds}s")
        print(f"   File Hash: {rec.file_hash}")

        # Check Step 8: Job enqueued
        job = db.query(Job).filter(Job.recording_id == rec.id).first()
        assert job is not None, "Watcher failed to enqueue Job into processing queue!"
        print(f"   [Step 8 SUCCESS] Job enqueued: ID={job.id}, Type={job.job_type}, Status={job.status}")

        # Wait for JobWorker to process job
        print("-> Waiting for JobWorker to execute analysis job...")
        for _ in range(35):
            time.sleep(1.0)
            db.commit()  # Flush identity map cache to see updates from worker thread
            job = db.query(Job).filter(Job.id == job.id).first()
            if job.status == JobStatus.COMPLETED:
                break
            print(f"   Job #{job.id} progress: {job.progress}% - {job.message}")

        db.commit()
        rec = db.query(Recording).filter(Recording.id == rec.id).first()
        job = db.query(Job).filter(Job.id == job.id).first()
        assert job.status == JobStatus.COMPLETED, f"Job did not complete: {job.status}"
        assert rec.status == RecordingStatus.ANALYZED, f"Recording not marked analyzed: {rec.status}"
        print(f"   [JOB PIPELINE SUCCESS] Analysis completed at 100%! Recording status: {rec.status}")

    finally:
        db.close()

def test_manual_import_and_management():
    print_banner("TEST 3: MANUAL VIDEO IMPORT & RECORDING MANAGEMENT (FEATURE 1 & 5)")
    db = SessionLocal()
    try:
        from app.routers.recordings import import_local_recording, reprocess_recording, delete_recording
        from app.schemas.recording import RecordingLocalImport

        # Test Manual Local Import on D: Drive
        temp_rec = Path("D:/GTA_CLIPFORGE_AI/temp/manual_import_gameplay.mp4")
        generate_test_video(str(temp_rec), duration=5, ext=".mp4")

        payload = RecordingLocalImport(
            file_path=str(temp_rec),
            notes="Manual import test of long GTA 6 gameplay recording"
        )
        print("-> Executing manual local file import...")
        rec = import_local_recording(payload, db)
        assert rec.id is not None, "Manual import failed to create recording"
        assert rec.resolution == "1920x1080", "Resolution error on manual import"
        print(f"   [SUCCESS] Manually imported ID={rec.id}, resolution={rec.resolution}, duration={rec.duration_seconds}s")

        # Test Search
        from app.routers.recordings import list_recordings
        search_res = list_recordings(page=1, page_size=10, q="manual_import", db=db)
        assert search_res.total >= 1, "Search query failed to find recording"
        print(f"   [SUCCESS] Search returned {search_res.total} result(s)")

        # Test Reprocess
        print(f"-> Testing Reprocess for Recording ID={rec.id}...")
        reprocessed = reprocess_recording(rec.id, db)
        assert reprocessed.status == RecordingStatus.PENDING, "Reprocess did not reset status to PENDING"
        print(f"   [SUCCESS] Reprocess queued job for Recording ID={rec.id}")

        # Test Delete
        print(f"-> Testing Delete for Recording ID={rec.id}...")
        del_res = delete_recording(rec.id, delete_file=False, db=db)
        assert del_res["status"] == "deleted", "Delete failed"
        assert db.query(Recording).filter(Recording.id == rec.id).first() is None, "Recording still in DB"
        print(f"   [SUCCESS] Recording ID={rec.id} deleted successfully from database")

    finally:
        db.close()

def test_duplicate_prevention():
    print_banner("TEST 4: DUPLICATE DETECTION PREVENTING REDUNDANT ENTRIES")
    watch_folder = Path(settings.WATCH_DIR)
    test_video_path = watch_folder / "watcher_test_gta6_mission.mp4"

    db = SessionLocal()
    try:
        initial_count = db.query(Recording).count()
        print(f"Initial recordings count: {initial_count}")

        # Re-triggering process on same file
        res = folder_watcher._process_detected_file(str(test_video_path))
        new_count = db.query(Recording).count()
        print(f"Recordings count after duplicate submission: {new_count}")
        assert new_count == initial_count, "Duplicate file was erroneously re-inserted into database!"
        print("   [SUCCESS] Duplicate correctly detected and prevented!")
    finally:
        db.close()

def test_job_retry_and_cancellation():
    print_banner("TEST 5: JOB MANAGEMENT (RETRY FAILED, REAL PROGRESS, CANCELLATION)")
    db = SessionLocal()
    try:
        job = Job(
            job_type=JobType.ANALYSIS,
            status=JobStatus.FAILED,
            progress=40.0,
            message="Simulated GPU OOM Error",
            error="CUDA out of memory during keyframe inference",
        )
        db.add(job)
        db.commit()
        db.refresh(job)
        print(f"Created failed job #{job.id}: {job.error}")

        # Test Retry
        from app.routers.jobs import retry_job
        retried = retry_job(job.id, db)
        assert retried["status"] == JobStatus.PENDING, "Job was not reset to PENDING"
        assert retried["progress"] == 0.0, "Progress was not reset to 0"
        assert retried["error"] is None, "Error was not cleared"
        print(f"   [SUCCESS] Job #{job.id} retried successfully: status={retried['status']}")

        # Test Cancel
        from app.routers.jobs import cancel_job
        cancelled = cancel_job(job.id, db)
        assert cancelled["status"] == JobStatus.CANCELLED, "Job was not marked CANCELLED"
        print(f"   [SUCCESS] Job #{job.id} cancelled successfully: status={cancelled['status']}")

    finally:
        db.close()

def test_monitoring_controls():
    print_banner("TEST 6: AUTOMATIC PROCESSING SETTINGS & MONITORING CONTROLS")
    # Test Pause
    folder_watcher.pause()
    assert folder_watcher.is_paused() is True, "Watcher did not pause"
    settings_dict = get_watcher_settings()
    assert settings_dict["monitoring_paused"] is True, "Setting not persisted"
    print("   [SUCCESS] Pause monitoring control works and persists in SQLite")

    # Test Resume
    folder_watcher.resume()
    assert folder_watcher.is_paused() is False, "Watcher did not resume"
    settings_dict = get_watcher_settings()
    assert settings_dict["monitoring_paused"] is False, "Setting not persisted"
    print("   [SUCCESS] Resume monitoring control works and persists in SQLite")

    # Test Settings Update
    updated = update_watcher_settings({
        "enable_auto_mode": True,
        "auto_analyze": True,
        "auto_generate_clips": False,
        "require_approval": True,
    })
    assert updated["auto_generate_clips"] is False, "Setting auto_generate_clips update failed"
    print("   [SUCCESS] Auto Mode, Auto Analyze, Auto Generate Clips, and Require Approval settings saved and loaded")

def main():
    print_banner("STARTING GTA CLIPFORGE AI PHASE 2 COMPREHENSIVE TESTS")
    # Clean reset DB tables for reliable test run
    db = SessionLocal()
    try:
        db.query(Job).delete()
        db.query(Recording).delete()
        db.commit()
    finally:
        db.close()

    test_formats()
    test_watcher_8_steps()
    test_manual_import_and_management()
    test_duplicate_prevention()
    test_job_retry_and_cancellation()
    test_monitoring_controls()

    print_banner("ALL PHASE 2 TESTS COMPLETED SUCCESSFULLY! 100% PASS")
    folder_watcher.stop()
    job_worker.stop()

if __name__ == "__main__":
    main()
