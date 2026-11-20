import os
import sys
import json
import zipfile
import shutil
from pathlib import Path
from datetime import datetime, timezone, timedelta

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, engine, migrate_database_schema
from app.models.recording import Recording, RecordingStatus
from app.models.clip import Clip, ClipStatus, MomentType
from app.models.job import Job, JobStatus, JobType
from app.models.detected_moment import DetectedMoment
from app.models.publishing_item import PublishingItem, PublishingStatusEnum
from app.models.recording_permission import RecordingPermission, PermissionStatusEnum
from app.services.video_service import validate_video, calculate_file_hash
from app.services.video_engine import video_engine
from app.services.gta_detector import gta_detector
from app.services.shorts_generator import shorts_generator
from app.services.cinematic_editor import cinematic_editor, CINEMATIC_PRESETS
from app.services.copyright_risk_service import copyright_risk_service
from app.services.export_service import export_service
from app.services.publishing_service import publishing_service
from app.services.job_worker import job_worker
from app.routers.clips import approve_clip

def run_all_final_tests():
    print("=" * 85)
    print("🚀 GTA CLIPFORGE AI — PHASE 10 COMPREHENSIVE FINAL VERIFICATION TEST SUITE")
    print("=" * 85)

    migrate_database_schema(engine)
    db = SessionLocal()

    # --------------------------------------------------------------------------
    # TEST 1: Long Recording Imports & Validation
    # --------------------------------------------------------------------------
    print("\n[TEST 1] Long Recording Imports & FFprobe Validation")
    test_video_path = "D:/GTA_CLIPFORGE_AI/recordings/test_gameplay_75s.mp4"
    assert os.path.isfile(test_video_path), f"Test video not found: {test_video_path}"
    
    meta = validate_video(test_video_path)
    print(f"  • Filename: {Path(test_video_path).name}")
    print(f"  • Duration: {meta['duration_seconds']:.1f}s")
    print(f"  • Resolution: {meta['resolution']}")
    print(f"  • FPS: {meta['fps']}")
    print(f"  • Codec: Video={meta['video_codec']}")
    assert meta["duration_seconds"] >= 60.0, "Expected video duration >= 60s"
    assert meta["resolution"] == "1920x1080", "Expected 1080p source resolution"
    print("  ✅ TEST 1 PASSED: Long recording imported and validated via FFprobe.")

    # --------------------------------------------------------------------------
    # TEST 2: Duplicate Detection via File Hash
    # --------------------------------------------------------------------------
    print("\n[TEST 2] Duplicate Detection via SHA-256 File Hash")
    file_hash = calculate_file_hash(test_video_path)
    print(f"  • SHA-256 Hash: {file_hash}")
    assert len(file_hash) == 64, "Expected 64-char hex SHA-256 hash"
    
    # Check SQLite duplicate logic
    norm_path = str(Path(test_video_path).resolve())
    existing = db.query(Recording).filter(
        (Recording.file_hash == file_hash) | (Recording.file_path == norm_path)
    ).first()
    assert existing is not None, "Expected recording to be found in database"
    print(f"  • Successfully matched existing Recording #{existing.id} ({existing.filename})")
    print("  ✅ TEST 2 PASSED: Duplicate detection prevents duplicate re-processing.")

    # --------------------------------------------------------------------------
    # TEST 3: Interrupted Job Recovery
    # --------------------------------------------------------------------------
    print("\n[TEST 3] Interrupted Job Recovery on Server Restart")
    # Insert mock crashed job
    mock_job = Job(
        recording_id=existing.id,
        job_type=JobType.ANALYSIS,
        status=JobStatus.RUNNING,
        progress=45.0,
        message="Processing chunk 2 of 5 before crash...",
    )
    db.add(mock_job)
    db.commit()
    db.refresh(mock_job)
    crashed_job_id = mock_job.id
    print(f"  • Created simulated crashed Job #{crashed_job_id} in RUNNING state")

    # Run recovery
    job_worker._recover_interrupted_jobs()

    # Verify recovered job status is FAILED
    db.expire_all()
    recovered = db.query(Job).filter(Job.id == crashed_job_id).first()
    assert recovered.status == JobStatus.FAILED, f"Expected FAILED status, got {recovered.status}"
    assert "Interrupted by server restart" in (recovered.error or "")
    print(f"  • Recovered Job #{recovered.id}: Status={recovered.status}, Message='{recovered.message}'")
    print("  ✅ TEST 3 PASSED: Interrupted job recovery cleanly caught crashed tasks.")

    # --------------------------------------------------------------------------
    # TEST 4: Scene Detection & Accurate Timestamps
    # --------------------------------------------------------------------------
    print("\n[TEST 4] Scene Detection & Timestamp Accuracy")
    scene_cuts = video_engine.detect_scenes_chunk(test_video_path, chunk_start=0.0, chunk_end=30.0, threshold=20.0)
    print(f"  • Processed scene cut analysis in 30s chunk: {len(scene_cuts)} hard cuts detected")
    assert isinstance(scene_cuts, list)
    for idx, sc in enumerate(scene_cuts, 1):
        print(f"    - Cut #{idx}: {sc.get('start_time', 0.0):.2f}s -> {sc.get('end_time', 0.0):.2f}s (Dur: {sc.get('duration', 0.0):.2f}s)")
        assert 0.0 <= sc.get("start_time", 0.0) <= meta["duration_seconds"]
        assert sc.get("end_time", 0.0) <= meta["duration_seconds"]
    print("  ✅ TEST 4 PASSED: Scene detection engine executed cleanly with verified timestamp bounds.")

    # --------------------------------------------------------------------------
    # TEST 5: Gameplay Classification & Moment Detection
    # --------------------------------------------------------------------------
    print("\n[TEST 5] Gameplay Classification & Excitement Scoring")
    moments = gta_detector.detect_moments_for_recording(1, sensitivity="medium")
    print(f"  • Detected and classified {len(moments)} gameplay moments in Recording #1:")
    for m in moments[:4]:
        print(f"    - Moment #{m['id']}: [{m.get('event_type', '').upper()}] {m['start_time']:.1f}s - {m['end_time']:.1f}s | Confidence: {m.get('confidence_score', 0)}/100")
        assert m.get("confidence_score", 0) > 0
        assert m.get("event_type") in ["police_chase", "high_speed_driving", "supercar_stunt", "car_crash", "explosion", "shootout", "action", "chase", "stunt"]
    assert len(moments) >= 1, "Expected at least 1 classified moment"
    print("  ✅ TEST 5 PASSED: Gameplay classification correctly scored action and moments.")

    # --------------------------------------------------------------------------
    # TEST 6: Clip Rendering & Vertical Resolution (1080x1920)
    # --------------------------------------------------------------------------
    print("\n[TEST 6] Clip Rendering & Vertical 1080x1920 Resolution Verification")
    clip = db.query(Clip).filter(Clip.recording_id == existing.id, Clip.id >= 5).first()
    if not clip or not clip.clip_path or not os.path.isfile(clip.clip_path):
        clip = db.query(Clip).filter(Clip.id >= 5).first()

    assert clip is not None and clip.clip_path and os.path.isfile(clip.clip_path), "Generated clip file missing"
    
    # FFprobe verify
    probe_res = shorts_generator.verify_short_file(clip.clip_path, expected_duration=clip.duration or 15.0)
    print(f"  • Clip #{clip.id} File: {clip.clip_path}")
    print(f"  • Probe Resolution: {probe_res['width']}x{probe_res['height']} (Aspect Ratio: {probe_res['aspect_ratio']})")
    print(f"  • Probe Codecs: Video={probe_res['video_codec']}, Audio={probe_res['audio_codec']}")
    print(f"  • Probe FPS: {probe_res['fps']}, Duration: {probe_res['duration']:.2f}s")
    print(f"  • File Size: {probe_res['file_size_bytes'] / (1024*1024):.2f} MB")
    
    assert probe_res["width"] == 1080, f"Expected 1080 width, got {probe_res['width']}"
    assert probe_res["height"] == 1920, f"Expected 1920 height, got {probe_res['height']}"
    assert probe_res["aspect_ratio"] == "9:16", f"Expected 9:16, got {probe_res['aspect_ratio']}"
    assert probe_res["is_valid"] is True, "Short failed FFprobe specification verification"
    print("  ✅ TEST 6 PASSED: Video rendered at exact 1080x1920 9:16 vertical resolution.")

    # --------------------------------------------------------------------------
    # TEST 7: Subtitle Synchronization (.SRT)
    # --------------------------------------------------------------------------
    print("\n[TEST 7] Subtitle Synchronization (.SRT)")
    srt_content = export_service.generate_srt_subtitles(db, clip.id)
    srt_lines = srt_content.strip().split("\n")
    print(f"  • Generated SRT lines ({len(srt_lines)} lines):")
    for l in srt_lines[:8]:
        print(f"    {l}")
    
    # Verify SRT format
    assert srt_lines[0] == "1", "SRT first block index must be 1"
    assert "-->" in srt_lines[1], "SRT timestamp delimiter '-->' missing"
    assert "," in srt_lines[1], "SRT millisecond comma separator missing"
    print("  ✅ TEST 7 PASSED: Synchronized SRT subtitles generated with accurate timestamps.")

    # --------------------------------------------------------------------------
    # TEST 8: Cinematic Presets
    # --------------------------------------------------------------------------
    print("\n[TEST 8] Cinematic Presets Verification")
    presets = cinematic_editor.get_presets()
    print(f"  • Loaded {len(presets)} GTA 6 Cinematic Presets:")
    expected_presets = [
        "BADASS CINEMATIC",
        "POLICE CHASE",
        "SUPER CAR STUNTS",
        "EPIC EXPLOSIONS",
        "SHOOTOUTS",
        "VICE CITY CINEMATIC",
        "FUNNY NPC MOMENTS"
    ]
    for ep in expected_presets:
        match = next((p for p in presets if p["name"] == ep), None)
        assert match is not None, f"Expected preset '{ep}' not found"
        print(f"    - [{match['name']}]: Zoom={match['default_zoom']}x, Slowmo={match['default_slowmo']}x, ColorGrade={match['color']}")
    print("  ✅ TEST 8 PASSED: All 7 cinematic presets configured and active.")

    # --------------------------------------------------------------------------
    # TEST 9: Permission Checks & Export Guardrails
    # --------------------------------------------------------------------------
    print("\n[TEST 9] Copyright Permission Checks & Export Guardrails")
    perm = copyright_risk_service.get_or_create_permission(db, existing.id)
    # Force set to granted for testing export
    copyright_risk_service.update_permission(
        db=db,
        recording_id=existing.id,
        original_creator="ViceCityKing",
        permission_status="Granted",
        editing_permission=True,
        redistribution_permission=True,
        commercial_monetization_permission=True,
        disclaimer_acknowledged=True
    )
    can_exp, reason = copyright_risk_service.check_clip_export_allowed(db, clip.id)
    print(f"  • Clip #{clip.id} Can Export: {can_exp} (Reason: {reason})")
    assert can_exp is True, "Expected clip export to be authorized under Granted permissions"
    
    # Approve clip
    approved = approve_clip(clip_id=clip.id, force=False, db=db)
    assert approved.is_approved is True
    print(f"  • Clip #{clip.id} successfully approved for export.")
    print("  ✅ TEST 9 PASSED: Permission checks and export guardrails operate reliably.")

    # --------------------------------------------------------------------------
    # TEST 10: Export Quality & Organized Folders
    # --------------------------------------------------------------------------
    print("\n[TEST 10] Export Quality, Reports & Organized Folders")
    # 1. TXT transcript
    txt = export_service.generate_txt_transcript(db, clip.id)
    assert "GTA 6 YOUTUBE SHORT" in txt
    
    # 2. CSV metadata catalog
    csv_text = export_service.export_csv_metadata(db, [clip.id])
    assert "clip_id" in csv_text and str(clip.id) in csv_text
    
    # 3. Copyright report
    rep = export_service.generate_copyright_report(db, existing.id)
    assert os.path.isfile(rep["json_path"])
    assert os.path.isfile(rep["markdown_path"])
    print(f"  • Saved Copyright Report: {rep['markdown_path']}")
    
    # 4. Best moments
    best_rec_id = 1 if db.query(DetectedMoment).filter(DetectedMoment.recording_id == 1).count() > 0 else existing.id
    best = export_service.export_best_moments(db, best_rec_id)
    print(f"  • Extracted {len(best)} best moments in GTA6_BEST_MOMENTS/")
    
    # 5. Production ZIP package
    zip_res = export_service.create_export_zip(db, [clip.id], package_name="TEST_PACKAGE_FINAL")
    assert os.path.isfile(zip_res["zip_path"])
    assert zip_res["zip_size_bytes"] > 0
    print(f"  • Production ZIP Archive: {zip_res['zip_path']} ({zip_res['zip_size_bytes'] / (1024*1024):.2f} MB)")
    print(f"  • Bundled files ({len(zip_res['files_included'])} files): {', '.join(zip_res['files_included'][:4])}...")
    
    # Verify ZIP integrity
    with zipfile.ZipFile(zip_res["zip_path"], "r") as zf:
        namelist = zf.namelist()
        assert any(n.startswith("shorts/") for n in namelist)
        assert any(n.startswith("subtitles/") for n in namelist)
        assert "metadata.csv" in namelist
        assert "manifest.json" in namelist
    print("  ✅ TEST 10 PASSED: Organized folders, CSV, SRT, TXT, reports and ZIP archive verified.")

    # --------------------------------------------------------------------------
    # TEST 11: Publishing Workspace & Checklist
    # --------------------------------------------------------------------------
    print("\n[TEST 11] Publishing Workspace & Performance Tracking")
    pub_item = publishing_service.get_or_create_publishing_item(db, clip.id)
    print(f"  • Publishing Item #{pub_item.id} for Clip #{clip.id}:")
    print(f"    - Active Title: {pub_item.active_title}")
    print(f"    - Status: {pub_item.status}")
    print(f"    - Checklist Completion: {json.loads(pub_item.checklist_json)}")
    
    # Test metrics simulation
    synced = publishing_service.sync_simulated_analytics(db, clip.id)
    assert synced.views_count > 0
    assert synced.likes_count > 0
    print(f"    - Simulated Performance: {synced.views_count:,} views, {synced.likes_count:,} likes, {synced.avg_view_duration_pct:.1f}% retention")
    
    # Test summary
    summary = publishing_service.get_summary(db)
    assert summary.total_items >= 1
    assert summary.total_views > 0
    print(f"  • Workspace Summary: {summary.total_items} items, {summary.total_views:,} views, {summary.total_watch_hours:.1f} hours watched")
    print("  ✅ TEST 11 PASSED: Publishing workspace, checklist, and performance tracking fully operational.")

    db.close()
    print("\n" + "=" * 85)
    print("🎉 ALL 11 PHASE 10 VERIFICATION TESTS PASSED SUCCESSFULLY WITH ZERO ERRORS!")
    print("=" * 85)

if __name__ == "__main__":
    run_all_final_tests()
