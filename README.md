# GTA CLIPFORGE AI 🎮⚡

> **Local AI-Powered GTA 6 Gameplay → YouTube Shorts Production Pipeline**
> 
> *A self-hosted, local-first workstation application that analyzes long GTA 6 gameplay recordings, detects high-octane moments, applies cinematic editing presets, evaluates copyright & monetization risks, generates footage-faithful metadata, and packages ready-to-publish 1080x1920 (9:16) vertical YouTube Shorts.*

---

## 🌟 Full Feature Overview Across All 10 Phases

- **Phase 1: Foundation & Windows Local Setup**: FastAPI + SQLite (WAL mode), Next.js 14 Dark Gaming UI, FFprobe/FFmpeg binary validation, disk space monitors on `D:\GTA_CLIPFORGE_AI`.
- **Phase 2: Recording Ingestion & Watchdog Folder Watcher**: Automated 8-step intake pipeline watching `GTA6_RECORDINGS/` with streaming SHA-256 duplicate detection and copy stabilization.
- **Phase 3: Video Processing Engine**: 5-minute chunk-based parallel processing, PySceneDetect content detection, 10-second keyframes, RMS silence & peak audio analysis, and NVENC GPU hardware acceleration with CPU fallback.
- **Phase 4: GTA 6 Specialized AI Event Detection**: Multi-modal detection of 14 GTA 6 event types (police chases, 5-star sirens, supercar stunts, high-speed driving, explosions, shootouts, mission passes/fails, funny NPC moments).
- **Phase 5: Candidate Clips & AI Ranking**: Sliding window candidate selection (15s, 30s, 45s, 60s), AI ranking engine scoring Action, Audio, Visual Quality, and Narrative Pacing (0–100 score).
- **Phase 6: Automatic YouTube Shorts Generator**: Real FFmpeg vertical 1080x1920 (9:16) H.264 AAC rendering with ambient blurred background fill, zero stretching, and burnt-in Vice Neon subtitles.
- **Phase 7: GTA 6 Cinematic Shorts Editing**: 7 signature cinematic presets (*BADASS CINEMATIC, POLICE CHASE, SUPER CAR STUNTS, EPIC EXPLOSIONS, SHOOTOUTS, VICE CITY CINEMATIC, FUNNY NPC MOMENTS*) with dynamic zoom, speed ramping (0.25x–1.0x), cinematic color grading, and broadcast audio normalization (`dynaudnorm`).
- **Phase 8: AI YouTube Shorts Metadata Generator**: 5 title suggestions, 3 retention-optimized opening hooks, descriptions with game credits, curated non-spam hashtags, mobile thumbnail text overlays, and pinned comments with SQLite persistence.
- **Phase 9: Copyright & Monetization Risk Center**: External creator permission management system (original creator, source URL, written permission evidence, editing, redistribution, and commercial-use scopes, expiration dates), 9-point risk evaluation matrix (`LOW`, `MEDIUM`, `HIGH`, `UNKNOWN`), export approval guardrails, human manual review override, and Take-Two / YouTube policy baselines.
- **Phase 10: Export Center, Publishing Workspace & Production Pipeline**:
  - **Organized Production Folders**: `GTA6_SHORTS/`, `GTA6_BEST_MOMENTS/`, `GTA6_REPORTS/`, `GTA6_EXPORTS/`.
  - **Export Formats**: Individual MP4s, Bulk MP4s, Production ZIP Packages, Synchronized SRT Subtitles (`.srt`), Plain-Text Transcripts (`.txt`), CSV Metadata Catalog, and Copyright Reports (`.json` / `.md`).
  - **Publishing Workspace**: Draft title selection, descriptions, hashtags, interactive 9-point publishing checklist, planned publish scheduling, published status tracking, and manual performance metrics (Views, Likes, Comments, Shares, Watch Hours, Retention %).
  - **End-to-End Auto Mode Pipeline**: Automated 11-step pipeline from file detection to export packaging with strict requirement for human publishing approval.

---

## ⚡ Quick Start & Setup Instructions

### System Prerequisites
- **Operating System**: Windows 10 or Windows 11 (64-bit)
- **Storage Target**: `D:\` Drive (All video files, models, and databases reside under `D:\GTA_CLIPFORGE_AI\`)
- **Python**: Python 3.11+ (Python 3.12 / 3.14 verified)
- **Node.js**: Node.js 18+ (tested on Node v20/v24)
- **Media Tools**: `ffmpeg.exe` and `ffprobe.exe` installed in `D:\GTA_CLIPFORGE_AI\bin\` or added to system `PATH`.

---

### 1. Install & Configure Backend

```powershell
# Navigate to backend directory
cd D:\GTA_CLIPFORGE_AI\backend

# Install Python dependencies
pip install -r requirements.txt

# Verify environment file exists
# (Defaults point to D:\GTA_CLIPFORGE_AI\data\clipforge.db)
copy .env.example .env
```

Start the FastAPI backend server (Port **8000**):
```powershell
python run.py
# Or using the PowerShell runner:
.\start-backend.ps1
```
The backend initializes the SQLite schema, runs database migrations, creates all directories, ensures royalty-free audio assets, starts the background job worker, and begins monitoring `GTA6_RECORDINGS/`.

API Documentation is available locally at:
- **Swagger UI**: `http://localhost:8000/docs`
- **ReDoc**: `http://localhost:8000/redoc`

---

### 2. Install & Start Frontend

```powershell
# Navigate to frontend directory
cd D:\GTA_CLIPFORGE_AI\frontend

# Install dependencies
npm install

# Start development server
npm run dev
# Or build for production:
npm run build
npm start
```

The Next.js 14 web application is available at:
👉 **`http://localhost:3000`**

---

## 📁 Organized File System Structure

```
D:\GTA_CLIPFORGE_AI\
├── GTA6_RECORDINGS\           # Intake folder monitored by watchdog folder watcher
├── GTA6_SHORTS\               # Generated vertical 1080x1920 (9:16) H.264 AAC YouTube Shorts
├── GTA6_BEST_MOMENTS\          # Extracted horizontal raw climax gameplay segments
├── GTA6_REPORTS\              # Copyright compliance & risk assessment reports (.json / .md)
├── GTA6_EXPORTS\              # Production ZIP packages, SRT subtitles, transcripts, and CSV catalog
├── bin\                       # Local FFmpeg and FFprobe binaries (ffmpeg.exe, ffprobe.exe)
├── data\                      # SQLite database storage (clipforge.db in WAL mode)
├── assets\                    # Verified royalty-free music rhythms and sound effects
├── backend\                   # FastAPI application source code
└── frontend\                  # Next.js 14 App Router frontend
```

---

## 🤖 Auto Mode Pipeline (11 Automated Steps)

When a new recording is dropped into `GTA6_RECORDINGS/`:
1. **Detect It**: FileSystem watcher catches the file created/moved event.
2. **Validate the Recording**: Checks file size stability and validates container integrity via FFprobe.
3. **Check Creator Permission**: Initializes permission record and compliance evaluation.
4. **Analyze the Gameplay**: Chunks video into parallel slices, runs PySceneDetect, and extracts audio waveforms.
5. **Find Interesting Moments**: Evaluates optical flow, siren color profiles, and audio energies across 14 GTA 6 event types.
6. **Rank the Candidates**: Computes multi-attribute AI excitement scores (Action, Audio, Vision, Story).
7. **Generate Shorts**: Renders 1080x1920 9:16 vertical MP4s with ambient blurred fill.
8. **Prepare Editing & Metadata**: Applies cinematic preset grading and generates 5 AI title suggestions, hooks, and hashtags.
9. **Create Copyright Reports**: Writes structured JSON and Markdown compliance reports to `GTA6_REPORTS/`.
10. **Send Clips for Approval**: Enforces export guardrails; clips remain unapproved until reviewed.
11. **Export Approved Clips**: Exports approved Shorts, SRTs, TXTs, and CSV manifests to `GTA6_EXPORTS/`.

> **CRITICAL RULE**: The system **never automatically publishes** to YouTube without explicit human review and authorization.

---

## 🧪 Comprehensive Test Verification Suite

All core capabilities are verified with real automated tests against real media and database records.

Run the test suites with Python:
```powershell
cd D:\GTA_CLIPFORGE_AI

# Phase 8: AI YouTube Shorts Metadata Generator Tests
python backend/tests/test_phase8_metadata_generator.py

# Phase 9: Copyright & Monetization Risk Center Tests
python backend/tests/test_phase9_copyright_risk.py

# Phase 10: Final Verification & Export Test Suite
python backend/tests/test_phase10_final_testing.py
```

### Verified Test Results Summary:
- ✅ **TEST 1 (Long Recording Import)**: FFprobe verified 1080p 60fps H.264 container integrity.
- ✅ **TEST 2 (Duplicate Detection)**: Streaming SHA-256 hash matched existing recording without duplicate insertion.
- ✅ **TEST 3 (Interrupted Job Recovery)**: Simulated crashed task automatically recovered to `FAILED` with retry capability.
- ✅ **TEST 4 (Scene Detection)**: Bounded, non-overlapping timestamps within recording boundaries.
- ✅ **TEST 5 (Gameplay Classification)**: Multi-modal optical flow and acoustic detection scored action moments.
- ✅ **TEST 6 (Vertical Resolution)**: FFprobe verified exact 1080x1920 dimensions, 9:16 aspect ratio, H.264 video, and AAC audio.
- ✅ **TEST 7 (Subtitle Synchronization)**: Validated standard `.srt` format with millisecond timecodes (`00:00:00,000 --> 00:00:03,500`).
- ✅ **TEST 8 (Cinematic Presets)**: All 7 signature GTA 6 presets verified.
- ✅ **TEST 9 (Permission Checks & Guardrails)**: Export blocked with HTTP 403 when unpermitted; unlocked via user approval and manual review override.
- ✅ **TEST 10 (Export Quality & ZIP)**: Verified `.txt` transcripts, metadata `.csv`, `.md` copyright reports, raw climax cuts, and production ZIP archive integrity.
- ✅ **TEST 11 (Publishing Workspace)**: Verified draft titles, 9-point checklist completion, and simulated YouTube analytics synchronization.
- ✅ **Next.js Production Build**: All 13 static pages compiled and generated with zero errors.

---

## 📜 Legal Advisory Notice

GTA CLIPFORGE AI risk classifications, copyright checks, and policy evaluations are **educational and workflow tools only** and **do not constitute formal legal counsel**. Take-Two Interactive and YouTube retain unilateral authority to enforce terms of service and content policies. A creator's permission to use footage waives only their recording performance rights and **does not grant Take-Two or Rockstar's underlying commercial IP rights**.

---

## 🎮 Running the Local Workstation

1. Open PowerShell and start the backend:
   ```powershell
   cd D:\GTA_CLIPFORGE_AI\backend
   python run.py
   ```
2. Open a second PowerShell window and start the frontend:
   ```powershell
   cd D:\GTA_CLIPFORGE_AI\frontend
   npm run dev
   ```
3. Open your browser and navigate to **`http://localhost:3000`**.
