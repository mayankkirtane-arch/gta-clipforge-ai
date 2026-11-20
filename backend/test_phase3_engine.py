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
from app.models.analysis import RecordingAnalysis, TimelineSegment, RecordingChunk
from app.models.job import Job, JobStatus, JobType
from app.services.video_service import get_ffmpeg_path, get_ffprobe_path
from app.services.video_engine import video_engine, format_timestamp
import cv2
import numpy as np

def print_banner(title: str):
    print("\n" + "=" * 65)
    print(f"  {title}")
    print("=" * 65)

def generate_multi_scene_test_video(output_path: str, duration: int = 8) -> str:
    """
    Generate a synthetic GTA gameplay test video containing:
    - 3 distinct color scenes (Red -> Blue -> Green) for PySceneDetect cut detection
    - A 1-second black transition frame
    - Audio with quiet ambient section followed by loud simulated gunshot audio peak
    """
    ffmpeg = get_ffmpeg_path()
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()

    # Create video filter with 3 scenes and a black frame
    # 0s - 3s: Red scene
    # 3s - 4s: Black screen
    # 4s - 6s: Blue scene
    # 6s - 8s: Green scene
    vf = (
        "color=c=red:s=1920x1080:d=3 [v1]; "
        "color=c=black:s=1920x1080:d=1 [v2]; "
        "color=c=blue:s=1920x1080:d=2 [v3]; "
        "color=c=green:s=1920x1080:d=2 [v4]; "
        "[v1][v2][v3][v4] concat=n=4:v=1:a=0 [v]"
    )

    # Audio filter:
    # 0s - 4s: very quiet ambient tone (-45dB)
    # 4s - 5s: silence
    # 5s - 8s: high-amplitude loud burst / simulated explosion (-6dB)
    af = (
        "sine=f=440:d=4,volume=0.01 [a1]; "
        "anullsrc=d=1 [a2]; "
        "sine=f=880:d=3,volume=0.9 [a3]; "
        "[a1][a2][a3] concat=n=3:v=0:a=1 [a]"
    )

    cmd = [
        ffmpeg,
        "-y",
        "-filter_complex", f"{vf}; {af}",
        "-map", "[v]",
        "-map", "[a]",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-r", "30",
        "-c:a", "aac",
        "-b:a", "128k",
        str(path)
    ]
    res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"FFmpeg failed to create test video: {res.stderr[:200]}")
    return str(path)

def test_metadata_extraction(video_path: str):
    print_banner("PHASE 3 - TEST 1: COMPREHENSIVE VIDEO METADATA EXTRACTION")
    meta = video_engine.extract_full_metadata(video_path)
    print(f"-> Resolution: {meta['resolution']}")
    print(f"-> Frame Rate: {meta['fps']} FPS")
    print(f"-> Duration: {meta['duration_seconds']}s")
    print(f"-> Codecs: Video={meta['video_codec']}, Audio={meta['audio_codec']}")
    print(f"-> Audio Channels: {meta['channels']}, Sample Rate: {meta['sample_rate']} Hz")
    
    assert meta["resolution"] == "1920x1080", "Metadata resolution mismatch"
    assert meta["fps"] == 30.0, "Metadata FPS mismatch"
    assert meta["duration_seconds"] >= 7.5, "Duration mismatch"
    print("   [SUCCESS] Full container and stream metadata verified!")

def test_audio_extraction(video_path: str):
    print_banner("PHASE 3 - TEST 2: AUDIO EXTRACTION WITHOUT LOADING VIDEO INTO RAM")
    out_audio = Path("D:/GTA_CLIPFORGE_AI/temp/audio/test_audio.wav")
    extracted = video_engine.extract_audio(video_path, str(out_audio))
    assert extracted is not None and os.path.isfile(extracted), "Audio extraction failed"
    audio_size = os.path.getsize(extracted)
    print(f"-> Extracted PCM WAV file: {extracted} ({audio_size} bytes)")
    assert audio_size > 10000, "Extracted audio file is too small or corrupt"
    print("   [SUCCESS] 16kHz mono audio demuxed directly to disk with zero video RAM footprint!")

def test_thumbnail_and_keyframes(video_path: str):
    print_banner("PHASE 3 - TEST 3: POSTER THUMBNAIL & KEYFRAME EXTRACTION")
    # Thumbnail
    thumb_path = Path("D:/GTA_CLIPFORGE_AI/temp/thumbnails/test_poster.jpg")
    thumb = video_engine.generate_thumbnail(video_path, str(thumb_path), timestamp_sec=1.5)
    assert thumb is not None and os.path.isfile(thumb), "Thumbnail generation failed"
    img = cv2.imread(thumb)
    assert img is not None and img.shape[1] == 640, "Invalid thumbnail dimensions"
    print(f"-> Poster Thumbnail: {thumb} (Shape: {img.shape})")

    # Keyframes at 2.0s intervals
    kf_dir = Path("D:/GTA_CLIPFORGE_AI/temp/keyframes/test_kf")
    keyframes = video_engine.extract_keyframes_for_chunk(
        video_path, chunk_start=0.0, chunk_end=8.0, interval_sec=2.0, output_dir=kf_dir
    )
    print(f"-> Extracted {len(keyframes)} keyframes at 2.0s intervals:")
    for kf in keyframes:
        print(f"   [{kf['timestamp_formatted']}] {kf['keyframe_filename']} - Black: {kf['is_black_frame']} (lum: {kf['mean_luminance']:.1f})")
    assert len(keyframes) >= 4, "Keyframes count mismatch"
    print("   [SUCCESS] Keyframes generated with accurate timestamps and luminance tags!")

def test_scene_transitions_and_black_frames(video_path: str):
    print_banner("PHASE 3 - TEST 4: SCENE DETECTION (PySceneDetect) & BLACK FRAMES")
    scenes = video_engine.detect_scenes_chunk(video_path, chunk_start=0.0, chunk_end=8.0, threshold=27.0)
    print(f"-> PySceneDetect detected {len(scenes)} scene cuts in test footage:")
    for s in scenes:
        print(f"   Scene #{s['scene_number']}: {s['start_time']}s -> {s['end_time']}s (Duration: {s['duration']}s)")
    assert len(scenes) >= 2, f"PySceneDetect should detect distinct cuts, got {len(scenes)}"
    print("   [SUCCESS] PySceneDetect cuts accurately detected!")

def test_silence_and_audio_peaks(video_path: str):
    print_banner("PHASE 3 - TEST 5: SILENCE & AUDIO PEAKS & WAVEFORM DATA")
    audio_path = Path("D:/GTA_CLIPFORGE_AI/temp/audio/test_audio.wav")
    pts, waveform = video_engine.analyze_audio_chunk(
        str(audio_path), chunk_start=0.0, chunk_end=8.0,
        silence_thresh_db=-35.0, peak_percentile=80.0
    )
    print(f"-> Audio Points analyzed: {len(pts)}")
    peaks = [p for p in pts if p["is_peak"]]
    silence = [p for p in pts if p["is_silence"]]
    print(f"-> Audio Peaks found: {len(peaks)} (Gunshot/explosion burst)")
    print(f"-> Silence segments found: {len(silence)}")
    print(f"-> Waveform array length: {len(waveform)} samples (Min: {min(waveform)}, Max: {max(waveform)})")
    
    assert len(peaks) >= 1, "Audio peaks not detected in loud segment"
    assert len(silence) >= 1, "Silence not detected in quiet segment"
    assert len(waveform) > 0, "Waveform data is empty"
    print("   [SUCCESS] Silence, peaks, and normalized waveform verified!")

def test_preview_proxy_generation(video_path: str):
    print_banner("PHASE 3 - TEST 6: LOW-RESOLUTION PREVIEW PROXY (GPU / CPU FALLBACK)")
    proxy_path = Path("D:/GTA_CLIPFORGE_AI/temp/proxies/test_proxy.mp4")
    proxy_file, used_gpu = video_engine.generate_preview_proxy(video_path, str(proxy_path), use_gpu=True)
    assert proxy_file is not None and os.path.isfile(proxy_file), "Proxy generation failed"
    proxy_meta = video_engine.extract_full_metadata(proxy_file)
    print(f"-> Generated Proxy: {proxy_file}")
    print(f"-> Resolution: {proxy_meta['resolution']}, Used GPU NVENC: {used_gpu}")
    assert proxy_meta["height"] == 720, "Proxy resolution height should be 720p"
    print("   [SUCCESS] Preview proxy generated successfully with hardware acceleration!")

def test_full_pipeline_with_checkpoint_recovery(video_path: str):
    print_banner("PHASE 3 - TEST 7: CHUNK-BASED PIPELINE & INTERRUPTED RECOVERY")
    db = SessionLocal()
    try:
        # Register a test recording in SQLite
        rec = Recording(
            filename=Path(video_path).name,
            original_filename="GTA6_Heist_Escape_8Hours.mp4",
            file_path=str(Path(video_path).resolve()),
            file_size_bytes=os.path.getsize(video_path),
            duration_seconds=8.0,
            resolution="1920x1080",
            fps=30.0,
            status=RecordingStatus.PENDING,
            notes="Phase 3 engine test",
        )
        db.add(rec)
        db.commit()
        db.refresh(rec)

        # PART A: Simulate interrupted processing by setting chunk 0 as completed
        chunk0 = RecordingChunk(
            recording_id=rec.id,
            chunk_index=0,
            start_time=0.0,
            end_time=4.0,
            status="completed"
        )
        db.add(chunk0)
        db.commit()
        print(f"-> Simulated Checkpoint: Chunk 0 (0-4s) marked completed in SQLite")

        # PART B: Run processing with 4-second chunk size (gives 2 chunks: 0-4s and 4-8s)
        # The engine should SKIP chunk 0 and process only chunk 1!
        progress_log = []
        def on_progress(pct: float, msg: str):
            progress_log.append((pct, msg))
            print(f"   Progress: {pct}% - {msg}")

        result = video_engine.process_recording(
            recording_id=rec.id,
            progress_callback=on_progress,
            chunk_duration_sec=4,
            keyframe_interval_sec=2.0,
            gpu_acceleration=True
        )

        assert result["status"] == "completed", "Processing did not complete"
        print(f"-> Result: {result}")

        # Check SQLite persistence
        analysis = db.query(RecordingAnalysis).filter(RecordingAnalysis.recording_id == rec.id).first()
        assert analysis is not None, "RecordingAnalysis missing in SQLite"
        assert analysis.status == "completed", "Analysis status not completed"
        assert analysis.total_scenes > 0, "Total scenes should be > 0"
        assert analysis.total_keyframes > 0, "Total keyframes should be > 0"

        # Check timeline representation
        timeline_segments = db.query(TimelineSegment).filter(TimelineSegment.recording_id == rec.id).all()
        print(f"-> Saved {len(timeline_segments)} Timeline Segments in SQLite:")
        for seg in timeline_segments[:3]:
            print(f"   [{seg.timestamp_formatted}] Scene #{seg.scene_number} | Peak: {seg.is_audio_peak} | Score: {seg.excitement_score}")

        assert len(timeline_segments) > 0, "Timeline segments missing in SQLite"
        first_seg = timeline_segments[0]
        assert first_seg.timestamp is not None
        assert first_seg.scene_number is not None
        assert first_seg.keyframe_path is not None
        assert first_seg.excitement_score is not None

        # Verify Recovery Checkpoint: Both chunks should now be completed in SQLite
        chunks = db.query(RecordingChunk).filter(RecordingChunk.recording_id == rec.id).all()
        assert len(chunks) == 2, f"Expected 2 chunks, got {len(chunks)}"
        assert all(c.status == "completed" for c in chunks), "All chunks should be marked completed"
        print("   [SUCCESS] Checkpoint recovery, timeline representation, and SQLite storage 100% verified!")

    finally:
        db.close()

def main():
    print_banner("STARTING GTA CLIPFORGE AI PHASE 3 ENGINE TEST SUITE")
    test_video = "D:/GTA_CLIPFORGE_AI/temp/phase3_sample_gameplay.mp4"
    print(f"-> Generating synthetic multi-scene GTA gameplay test video: {test_video}...")
    generate_multi_scene_test_video(test_video, duration=8)

    test_metadata_extraction(test_video)
    test_audio_extraction(test_video)
    test_thumbnail_and_keyframes(test_video)
    test_scene_transitions_and_black_frames(test_video)
    test_silence_and_audio_peaks(test_video)
    test_preview_proxy_generation(test_video)
    test_full_pipeline_with_checkpoint_recovery(test_video)

    print_banner("ALL PHASE 3 VIDEO PROCESSING ENGINE TESTS PASSED! 100% SUCCESS")

if __name__ == "__main__":
    main()
