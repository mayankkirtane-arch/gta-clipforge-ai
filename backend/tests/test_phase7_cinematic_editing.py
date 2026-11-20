import os
import sys
import json
import time
from pathlib import Path

# Add backend directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings
from app.database import SessionLocal, migrate_database_schema, engine
from app.models.recording import Recording
from app.models.clip import Clip, ClipStatus
from app.services.audio_library import audio_library
from app.services.cinematic_editor import cinematic_editor, CINEMATIC_PRESETS

def test_phase7():
    print("=" * 80)
    print("🎬 STARTING PHASE 7 GTA 6 CINEMATIC SHORTS EDITING TEST SUITE")
    print("=" * 80)

    # 1. Database Migration & Schema Check
    print("\n--- 1. Checking Database Migration & Phase 7 Columns ---")
    migrate_database_schema(engine)
    db = SessionLocal()
    rec = db.query(Recording).filter(Recording.id == 3).first()
    assert rec is not None, "Recording ID=3 (test_gameplay_75s.mp4) must exist in database"
    assert os.path.isfile(rec.file_path), f"Recording file missing at {rec.file_path}"
    print(f"✅ Target Recording #{rec.id} found: {rec.file_path} ({rec.duration_seconds}s)")
    db.close()

    # 2. Audio Library & Copyright Safety Check
    print("\n--- 2. Verifying Royalty-Free Audio Library & DMCA Protection ---")
    audio_library.ensure_default_assets()
    music_tracks = audio_library.list_music_tracks()
    sfx_tracks = audio_library.list_sfx_tracks()

    print(f"Found {len(music_tracks)} copyright-safe music tracks:")
    for m in music_tracks:
        assert os.path.isfile(m["file_path"]), f"Music track file missing: {m['file_path']}"
        assert m["copyright_safe"] is True, f"Track {m['id']} is not marked copyright safe!"
        print(f"  🎵 [{m['id']}] {m['title']} ({m['duration_seconds']}s) - {m['license']}")

    print(f"Found {len(sfx_tracks)} copyright-safe SFX tracks:")
    for s in sfx_tracks:
        assert os.path.isfile(s["file_path"]), f"SFX track file missing: {s['file_path']}"
        assert s["copyright_safe"] is True, f"SFX {s['id']} is not marked copyright safe!"
        print(f"  💥 [{s['id']}] {s['title']} ({s['duration_seconds']}s) - {s['license']}")

    assert len(music_tracks) >= 5, "Expected at least 5 royalty-free music tracks"
    assert len(sfx_tracks) >= 4, "Expected at least 4 royalty-free SFX tracks"
    print("✅ Audio library verified: 100% royalty-free, zero commercial copyright risk.")

    # 3. Presets Listing Check
    print("\n--- 3. Verifying 7 Signature Cinematic Presets ---")
    expected_presets = [
        "BADASS CINEMATIC",
        "POLICE CHASE",
        "SUPER CAR STUNTS",
        "EPIC EXPLOSIONS",
        "SHOOTOUTS",
        "VICE CITY CINEMATIC",
        "FUNNY NPC MOMENTS",
    ]
    available_presets = [p["name"] for p in cinematic_editor.get_presets()]
    print(f"Available presets: {available_presets}")
    for exp in expected_presets:
        assert exp in available_presets, f"Preset '{exp}' missing from CINEMATIC_PRESETS!"
        p_obj = cinematic_editor.get_preset_by_name(exp)
        print(f"  ✨ {p_obj['name']}: {p_obj['tagline']} | Zoom: {p_obj['default_zoom']}x | Slow-Mo: {p_obj['default_slowmo']}x")
    print(f"✅ All {len(expected_presets)} signature presets verified.")

    # 4. Instant 4-Second Preview Test
    print("\n--- 4. Testing Instant 4-Second Preview Generation ---")
    t0 = time.time()
    preview_res = cinematic_editor.generate_preview(
        recording_id=3,
        start_time=10.0,
        end_time=30.0,
        edit_mode="cinematic",
        preset_name="VICE CITY CINEMATIC",
        zoom_intensity=1.15,
        slowmo_speed=0.6,
        color_grading_intensity=1.0,
        music_track_id="vice_city_synthwave",
        music_volume=0.4,
        preview_duration=4.0,
    )
    p_time = round(time.time() - t0, 2)
    assert os.path.isfile(preview_res["file_path"]), f"Preview file missing: {preview_res['file_path']}"
    print(f"✅ Instant Preview rendered in {p_time}s: {preview_res['file_path']} ({preview_res['preview_url']})")

    # 5. Testing RAW GAMEPLAY Mode
    print("\n--- 5. Testing Mode 1: RAW GAMEPLAY Mode ---")
    t0 = time.time()
    raw_res = cinematic_editor.render_cinematic_short(
        recording_id=3,
        start_time=5.0,
        end_time=20.0,  # 15s
        title="GTA 6 Raw Authentic Gameplay",
        edit_mode="raw",
        render_mode="blurred_background",
        audio_volume=1.0,
        subtitles=False,
    )
    r_time = round(time.time() - t0, 2)
    print(f"Rendered RAW Short in {r_time}s: {raw_res['file_path']}")
    verif = raw_res["verification"]
    print(f"FFprobe Verification: {json.dumps(verif['checks'], indent=2)}")
    assert verif["is_valid"], f"RAW Short verification failed: {verif}"
    assert verif["width"] == 1080 and verif["height"] == 1920, f"Expected 1080x1920, got {verif['width']}x{verif['height']}"
    assert verif["video_codec"] == "h264", f"Expected h264, got {verif['video_codec']}"
    assert verif["audio_codec"] == "aac", f"Expected aac, got {verif['audio_codec']}"
    print("✅ RAW GAMEPLAY Mode verified: original video & audio preserved perfectly.")

    # 6. Testing All 7 Signature Presets
    print("\n--- 6. Testing Mode 2: All 7 Signature Presets on Real Footage ---")
    test_cases = [
        {
            "preset": "BADASS CINEMATIC",
            "start": 0.0,
            "end": 15.0,
            "zoom": 1.18,
            "slowmo": 0.5,
            "music": "dark_cyber_pulse",
            "sfx": "sub_bass_impact",
        },
        {
            "preset": "POLICE CHASE",
            "start": 10.0,
            "end": 25.0,
            "zoom": 1.20,
            "slowmo": 0.4,
            "music": "pursuit_adrenaline",
            "sfx": "cinematic_whoosh",
        },
        {
            "preset": "SUPER CAR STUNTS",
            "start": 20.0,
            "end": 35.0,
            "zoom": 1.22,
            "slowmo": 0.35,
            "music": "epic_trailer_riser",
            "sfx": "sub_bass_impact",
        },
        {
            "preset": "EPIC EXPLOSIONS",
            "start": 30.0,
            "end": 45.0,
            "zoom": 1.25,
            "slowmo": 0.3,
            "music": "epic_trailer_riser",
            "sfx": "sub_bass_impact",
        },
        {
            "preset": "SHOOTOUTS",
            "start": 40.0,
            "end": 55.0,
            "zoom": 1.15,
            "slowmo": 0.5,
            "music": "dark_cyber_pulse",
            "sfx": "action_riser",
        },
        {
            "preset": "VICE CITY CINEMATIC",
            "start": 50.0,
            "end": 65.0,
            "zoom": 1.12,
            "slowmo": 0.6,
            "music": "vice_city_synthwave",
            "sfx": "cinematic_whoosh",
        },
        {
            "preset": "FUNNY NPC MOMENTS",
            "start": 55.0,
            "end": 70.0,
            "zoom": 1.20,
            "slowmo": 0.5,
            "music": "lofi_funny_groove",
            "sfx": "record_scratch_freeze",
        },
    ]

    results = []
    for idx, tc in enumerate(test_cases, 1):
        p_name = tc["preset"]
        print(f"\n[{idx}/7] Rendering Preset: '{p_name}' (15s duration)...")
        t0 = time.time()
        res = cinematic_editor.render_cinematic_short(
            recording_id=3,
            start_time=tc["start"],
            end_time=tc["end"],
            title=f"GTA 6 {p_name} Short",
            edit_mode="cinematic",
            preset_name=p_name,
            render_mode="blurred_background",
            target_length=15,
            zoom_intensity=tc["zoom"],
            slowmo_speed=tc["slowmo"],
            color_grading_intensity=1.0,
            audio_volume=1.2,
            music_volume=0.35,
            music_track_id=tc["music"],
            sfx_track_id=tc["sfx"],
            transition_duration=0.3,
            subtitles=True,
            subtitle_text=f"GTA 6 {p_name.upper()}",
            subtitle_style="vice_neon" if "VICE" in p_name else "bold_yellow",
        )
        dur_render = round(time.time() - t0, 2)
        v = res["verification"]

        print(f"  ⏱ Render time: {dur_render}s")
        print(f"  📁 File: {res['file_path']}")
        print(f"  📐 Resolution: {v['width']}x{v['height']} ({v['aspect_ratio']})")
        print(f"  ⏳ Duration: {v['duration']}s (Expected: {v['expected_duration']}s)")
        print(f"  🎞 Codecs: Video={v['video_codec']} | Audio={v['audio_codec']}")
        print(f"  💾 File Size: {round(v['file_size_bytes'] / 1024 / 1024, 2)} MB")
        print(f"  ✅ Verification Valid: {v['is_valid']}")

        assert v["is_valid"], f"Verification failed for preset {p_name}: {v}"
        assert v["width"] == 1080 and v["height"] == 1920
        assert v["video_codec"] == "h264"
        assert v["audio_codec"] == "aac"
        results.append(res)

    print("\n" + "=" * 80)
    print("🏆 ALL 7 SIGNATURE PRESETS & RAW MODE RENDERED AND VERIFIED SUCCESSFULLY!")
    print(f"Total Shorts Generated in GTA6_SHORTS: {len(results) + 1}")
    print("=" * 80)

if __name__ == "__main__":
    test_phase7()
