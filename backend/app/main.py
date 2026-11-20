from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .config import settings
from .database import engine, Base
from .models import recording, clip, job, setting, analysis as analysis_model, detected_moment, candidate_clip, clip_metadata, recording_permission, publishing_item
from .routers import health, recordings, clips, jobs, stats, analysis, detected_moments, candidate_clips, cinematic, metadata, copyright as copyright_router, exports as exports_router, publishing as publishing_router, youtube as youtube_router
from .routers import settings as settings_router
from .services.file_service import ensure_directories
from .services.audio_library import audio_library
from .services.watcher_service import folder_watcher
from .services.job_worker import job_worker

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Initialize SQLite Database Schema & Run Migrations
    Base.metadata.create_all(bind=engine)
    from .database import migrate_database_schema
    migrate_database_schema(engine)
    
    # 2. Ensure all storage folders on D: drive exist
    ensure_directories()
    
    # 2b. Ensure default copyright-safe music & SFX exist
    audio_library.ensure_default_assets()
    
    # 3. Start Background Job Worker & Queue Manager
    job_worker.start()
    
    # 4. Start Watchdog Automatic Folder Watcher for GTA6_RECORDINGS
    folder_watcher.start()
    
    print(f"✅ {settings.APP_NAME} v{settings.APP_VERSION} started")
    print(f"📁 Database: {settings.DATABASE_URL}")
    print(f"📁 Recordings: {settings.RECORDINGS_DIR}")
    print(f"📁 Watch Folder: {folder_watcher.watch_path}")
    print(f"📁 Exports: {settings.EXPORTS_DIR}")
    
    yield
    
    print("🛑 Shutting down services...")
    folder_watcher.stop()
    job_worker.stop()
    print("🛑 Shutdown complete.")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Local AI-powered GTA gameplay to YouTube Shorts converter",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(stats.router)
app.include_router(recordings.router)
app.include_router(clips.router)
app.include_router(jobs.router)
app.include_router(analysis.router)
app.include_router(detected_moments.router)
app.include_router(candidate_clips.router)
app.include_router(cinematic.router)
app.include_router(metadata.router)
app.include_router(copyright_router.router)
app.include_router(exports_router.router)
app.include_router(publishing_router.router)
app.include_router(youtube_router.router)
app.include_router(settings_router.router)
