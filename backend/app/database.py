from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from pathlib import Path
from .config import settings

db_path = Path(settings.DATABASE_URL.replace("sqlite:///", ""))
db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

class Base(DeclarativeBase):
    pass

def migrate_database_schema(engine):
    """Safely and idempotently add any new Phase 6 columns to SQLite tables."""
    try:
        with engine.connect() as conn:
            # Check existing columns in 'clips'
            res = conn.execute(text("PRAGMA table_info(clips)"))
            existing_cols = {row[1] for row in res.fetchall()}
            
            new_clip_cols = [
                ("candidate_clip_id", "INTEGER"),
                ("detected_moment_id", "INTEGER"),
                ("resolution", "VARCHAR(50) DEFAULT '1080x1920'"),
                ("aspect_ratio", "VARCHAR(20) DEFAULT '9:16'"),
                ("fps", "INTEGER DEFAULT 60"),
                ("video_codec", "VARCHAR(50) DEFAULT 'h264'"),
                ("audio_codec", "VARCHAR(50) DEFAULT 'aac'"),
                ("render_mode", "VARCHAR(50) DEFAULT 'blurred_background'"),
                ("has_subtitles", "BOOLEAN DEFAULT 0"),
                ("subtitle_text", "VARCHAR(500)"),
                ("subtitle_style", "VARCHAR(50) DEFAULT 'vice_neon'"),
                ("stream_url", "VARCHAR(1000)"),
                ("thumbnail_url", "VARCHAR(1000)"),
                ("file_size_bytes", "BIGINT"),
                ("error_message", "TEXT"),
                ("edit_mode", "VARCHAR(50) DEFAULT 'raw'"),
                ("preset_name", "VARCHAR(100)"),
                ("zoom_intensity", "FLOAT DEFAULT 1.0"),
                ("slowmo_speed", "FLOAT DEFAULT 1.0"),
                ("color_grading_intensity", "FLOAT DEFAULT 1.0"),
                ("audio_volume", "FLOAT DEFAULT 1.0"),
                ("music_volume", "FLOAT DEFAULT 0.0"),
                ("music_track_id", "VARCHAR(100)"),
                ("sfx_track_id", "VARCHAR(100)"),
                ("transition_duration", "FLOAT DEFAULT 0.35"),
                ("effects_applied", "TEXT"),
            ]
            for col_name, col_type in new_clip_cols:
                if col_name not in existing_cols:
                    conn.execute(text(f"ALTER TABLE clips ADD COLUMN {col_name} {col_type}"))
            
            # Ensure clip_metadata table exists
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS clip_metadata (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clip_id INTEGER NOT NULL UNIQUE,
                    title VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL,
                    hook VARCHAR(500),
                    hashtags TEXT NOT NULL,
                    thumbnail_text VARCHAR(100),
                    pinned_comment TEXT,
                    title_suggestions TEXT NOT NULL,
                    hook_suggestions TEXT NOT NULL,
                    hashtag_suggestions TEXT NOT NULL,
                    thumbnail_text_suggestions TEXT NOT NULL,
                    pinned_comment_suggestions TEXT NOT NULL,
                    generation_context TEXT,
                    is_user_edited BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(clip_id) REFERENCES clips(id) ON DELETE CASCADE
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_clip_metadata_clip_id ON clip_metadata(clip_id)"))
            
            # Ensure recording_permissions table exists
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS recording_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recording_id INTEGER NOT NULL UNIQUE,
                    original_creator VARCHAR(255),
                    source_url VARCHAR(1000),
                    written_permission_evidence TEXT,
                    permission_status VARCHAR(50) DEFAULT 'Not Requested',
                    editing_permission BOOLEAN DEFAULT 0,
                    redistribution_permission BOOLEAN DEFAULT 0,
                    commercial_monetization_permission BOOLEAN DEFAULT 0,
                    permission_expiry_date TIMESTAMP,
                    overall_risk_level VARCHAR(50) DEFAULT 'UNKNOWN',
                    can_export BOOLEAN DEFAULT 0,
                    export_block_reason TEXT,
                    risk_checks_json TEXT,
                    manual_review_status VARCHAR(50) DEFAULT 'pending_review',
                    manual_review_notes TEXT,
                    reviewer_name VARCHAR(100),
                    reviewed_at TIMESTAMP,
                    disclaimer_acknowledged BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(recording_id) REFERENCES recordings(id) ON DELETE CASCADE
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_recording_permissions_recording_id ON recording_permissions(recording_id)"))

            # Ensure publishing_items table exists
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS publishing_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    clip_id INTEGER NOT NULL UNIQUE,
                    active_title VARCHAR(200) NOT NULL,
                    description TEXT NOT NULL,
                    hashtags TEXT NOT NULL,
                    hook VARCHAR(500),
                    thumbnail_text VARCHAR(100),
                    pinned_comment TEXT,
                    draft_titles_json TEXT,
                    status VARCHAR(50) DEFAULT 'draft',
                    planned_publish_date TIMESTAMP,
                    published_at TIMESTAMP,
                    youtube_video_id VARCHAR(100),
                    youtube_video_url VARCHAR(255),
                    checklist_json TEXT,
                    views_count INTEGER DEFAULT 0,
                    likes_count INTEGER DEFAULT 0,
                    comments_count INTEGER DEFAULT 0,
                    shares_count INTEGER DEFAULT 0,
                    watch_time_hours REAL DEFAULT 0.0,
                    avg_view_duration_pct REAL DEFAULT 0.0,
                    analytics_source VARCHAR(50) DEFAULT 'manual',
                    last_analytics_sync TIMESTAMP,
                    notes TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(clip_id) REFERENCES clips(id) ON DELETE CASCADE
                )
            """))
            conn.execute(text("CREATE INDEX IF NOT EXISTS ix_publishing_items_clip_id ON publishing_items(clip_id)"))
            conn.commit()
    except Exception as e:
        print(f"Database migration notice: {e}")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
