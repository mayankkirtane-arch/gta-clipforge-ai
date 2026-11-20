import os
import sys
import json
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import SessionLocal, engine, migrate_database_schema
from app.models.recording import Recording
from app.models.clip import Clip, ClipStatus, MomentType
from app.models.clip_metadata import ClipMetadata
from app.services.metadata_generator import metadata_generator, METADATA_PRESETS

def test_phase8():
    print("=" * 80)
    print("🤖 STARTING PHASE 8 AI YOUTUBE SHORTS METADATA GENERATOR TEST SUITE")
    print("=" * 80)

    # 1. Database Schema & Migration Check
    print("\n--- 1. Checking Database Migration & clip_metadata Table ---")
    migrate_database_schema(engine)
    db = SessionLocal()

    # Ensure we have at least one test clip to work with
    clips = db.query(Clip).all()
    print(f"Found {len(clips)} clips in database.")
    if len(clips) == 0:
        # Create a mock clip for testing if none exist
        rec = db.query(Recording).first()
        rec_id = rec.id if rec else 1
        clip = Clip(
            recording_id=rec_id,
            title="GTA 6 High Speed Chase",
            preset_name="POLICE CHASE",
            moment_type=MomentType.CHASE,
            duration=15.0,
            status=ClipStatus.GENERATED,
        )
        db.add(clip)
        db.commit()
        db.refresh(clip)
        clips = [clip]

    test_clip = clips[0]
    print(f"✅ Using Test Clip #{test_clip.id}: '{test_clip.title}' (Preset: {test_clip.preset_name})")

    # 2. Test AI Metadata Generation for Test Clip
    print("\n--- 2. Testing AI Metadata Generation ---")
    meta = metadata_generator.generate_metadata_for_clip(
        db=db,
        clip_id=test_clip.id,
        tone="viral",
        overwrite=True
    )
    assert meta is not None, "Metadata object should be generated and returned"
    assert meta.clip_id == test_clip.id

    title_sugg = json.loads(meta.title_suggestions)
    hook_sugg = json.loads(meta.hook_suggestions)
    thumb_sugg = json.loads(meta.thumbnail_text_suggestions)
    pinned_sugg = json.loads(meta.pinned_comment_suggestions)
    hash_sugg = json.loads(meta.hashtag_suggestions)

    print(f"Active Title: '{meta.title}' ({len(meta.title)} chars)")
    print(f"Active Hook: '{meta.hook}'")
    print(f"Active Hashtags: '{meta.hashtags}'")
    print(f"Thumbnail Text: '{meta.thumbnail_text}'")
    print(f"Pinned Comment: '{meta.pinned_comment}'")

    # Verify Requirements
    print("\n--- 3. Verifying Prompt Requirements ---")
    # A) 5 title suggestions
    assert len(title_sugg) == 5, f"Expected exactly 5 title suggestions, got {len(title_sugg)}"
    print(f"✅ Verified 5 Title Suggestions:")
    for idx, t in enumerate(title_sugg, 1):
        print(f"   [{idx}] {t} ({len(t)} chars)")
        assert len(t) <= 100, f"Title exceeds 100 chars: {t}"
        assert len(t) > 5, "Title is too short"

    # B) 3 opening hook suggestions
    assert len(hook_sugg) == 3, f"Expected exactly 3 hook suggestions, got {len(hook_sugg)}"
    print(f"\n✅ Verified 3 Opening Hook Suggestions:")
    for idx, h in enumerate(hook_sugg, 1):
        print(f"   [{idx}] \"{h}\"")

    # C) Description with credits, CTA, and hashtags
    assert len(meta.description) > 30, "Description must be detailed"
    assert "GTA" in meta.description
    assert "#" in meta.description
    print(f"\n✅ Verified YouTube Shorts Description ({len(meta.description)} chars)")

    # D) Relevant hashtags (avoid excessive hashtags: <= 6 tags)
    tag_count = len(meta.hashtags.split())
    assert 3 <= tag_count <= 6, f"Expected 3-6 relevant hashtags, got {tag_count}"
    print(f"✅ Verified Curated Hashtags ({tag_count} tags): {meta.hashtags}")

    # E) Thumbnail text suggestions (punchy 2-4 words)
    assert len(thumb_sugg) >= 3, "Expected at least 3 thumbnail text suggestions"
    print(f"✅ Verified Thumbnail Text Overlays: {thumb_sugg}")

    # F) Pinned comment suggestions
    assert len(pinned_sugg) >= 3, "Expected at least 3 pinned comment suggestions"
    print(f"✅ Verified Pinned Comments: {pinned_sugg}")

    # 4. Verify Specific Categories & Footage Matching
    print("\n--- 4. Verifying Category Coverage & Footage Matching ---")
    categories_to_check = [
        ("police_chase", "GTA 6 Police Chase Went CRAZY 💀"),
        ("vice_city", "Vice City Looks INSANE at Night 🔥"),
        ("funny_npc", "That NPC Really Did That?! 😂"),
        ("car_stunt", "Craziest GTA 6 Car Stunt!"),
        ("explosion", "This GTA 6 Explosion Was PURE CHAOS 💥"),
    ]
    for cat_key, example_expected in categories_to_check:
        cat_data = METADATA_PRESETS.get(cat_key)
        assert cat_data is not None, f"Category '{cat_key}' missing from METADATA_PRESETS"
        titles = cat_data["titles"]
        assert any(example_expected in t for t in titles), f"Expected title '{example_expected}' in {titles}"
        print(f"  ✓ Category '{cat_key}' matches example: '{example_expected}'")

    # 5. Testing Manual Metadata Editing & SQLite Persistence
    print("\n--- 5. Testing Manual Metadata Editing in SQLite ---")
    custom_title = "GTA 6 INSANE Getaway Driver Moment! 🏎️💨"
    custom_desc = "Custom edited description by user for testing.\n#GTA6 #Gaming"
    custom_pinned = "Who else loves Vice City pursuits? Let me know below! 👇"

    updated_meta = metadata_generator.update_metadata(
        db=db,
        clip_id=test_clip.id,
        title=custom_title,
        description=custom_desc,
        pinned_comment=custom_pinned,
    )
    assert updated_meta.is_user_edited is True
    assert updated_meta.title == custom_title
    assert updated_meta.description == custom_desc
    assert updated_meta.pinned_comment == custom_pinned

    # Re-fetch from database to verify persistence
    db.expire_all()
    db_meta = db.query(ClipMetadata).filter(ClipMetadata.clip_id == test_clip.id).first()
    assert db_meta.title == custom_title
    assert db_meta.is_user_edited is True
    print("✅ Manual edits successfully persisted to SQLite.")

    # 6. Testing YouTube Data API v3 Publish Payload Generation
    print("\n--- 6. Testing YouTube Publish Payload & Validation ---")
    payload = metadata_generator.build_youtube_publish_payload(db, test_clip.id)
    assert payload["clip_id"] == test_clip.id
    assert payload["category_id"] == "20"  # Gaming
    assert payload["made_for_kids"] is False
    assert payload["is_valid_for_youtube"] is True
    assert payload["char_count_title"] <= 100
    assert payload["char_count_description"] <= 5000
    assert isinstance(payload["tags"], list)
    assert len(payload["tags"]) >= 2
    print(f"✅ YouTube Publish Payload: Title='{payload['title']}', Tags={payload['tags']}, Valid={payload['is_valid_for_youtube']}")

    # 7. Testing Batch Metadata Generation
    print("\n--- 7. Testing Batch Metadata Generation ---")
    if len(clips) > 1:
        batch_ids = [c.id for c in clips[:5]]
        for cid in batch_ids:
            metadata_generator.generate_metadata_for_clip(db, cid, overwrite=True)
        count_in_db = db.query(ClipMetadata).filter(ClipMetadata.clip_id.in_(batch_ids)).count()
        assert count_in_db == len(batch_ids)
        print(f"✅ Batch generated metadata for {count_in_db} clips successfully.")

    db.close()
    print("\n" + "=" * 80)
    print("🏆 ALL PHASE 8 AI YOUTUBE SHORTS METADATA TESTS PASSED!")
    print("=" * 80)

if __name__ == "__main__":
    test_phase8()
