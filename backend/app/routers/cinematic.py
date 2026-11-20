import os
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from ..database import get_db
from ..models.clip import Clip, ClipStatus
from ..models.candidate_clip import CandidateClip
from ..models.recording import Recording
from ..schemas.clip import (
    CinematicEditRequest,
    CinematicPreviewRequest,
    CinematicPresetInfo,
    AudioTrackInfo,
    ClipResponse,
)
from ..services.cinematic_editor import cinematic_editor
from ..services.audio_library import audio_library
from ..config import settings

router = APIRouter(prefix="/api/cinematic", tags=["cinematic"])

@router.get("/presets", response_model=List[CinematicPresetInfo])
def list_presets():
    """List all 7 signature GTA 6 cinematic editing presets."""
    presets = cinematic_editor.get_presets()
    result = []
    for p in presets:
        result.append(CinematicPresetInfo(
            id=p["id"],
            name=p["name"],
            description=p["description"],
            tagline=p.get("tagline", ""),
            icon=p.get("icon", "Film"),
            color=p.get("color", "from-purple-500 to-pink-500"),
            default_zoom=p.get("default_zoom", 1.15),
            default_slowmo=p.get("default_slowmo", 0.5),
            color_grade_desc=f"Contrast {p['color_grade']['contrast']}x, Saturation {p['color_grade']['saturation']}x, Vignette {p['color_grade']['vignette']}",
            audio_profile=f"Game Vol {p['audio']['game_volume']}x, Music Vol {p['audio']['music_volume']}x",
            suggested_music=p["audio"]["suggested_music"],
            suggested_sfx=p["audio"]["suggested_sfx"],
        ))
    return result

@router.get("/audio/music", response_model=List[AudioTrackInfo])
def list_music_tracks():
    """List 100% royalty-free, copyright-safe background music tracks."""
    tracks = audio_library.list_music_tracks()
    return [
        AudioTrackInfo(
            id=t["id"],
            title=t["title"],
            category=t["category"],
            genre=t["genre"],
            duration_seconds=t["duration_seconds"],
            license=t["license"],
            copyright_safe=t["copyright_safe"],
            stream_url=f"/api/cinematic/audio/{t['id']}/stream",
        )
        for t in tracks
    ]

@router.get("/audio/sfx", response_model=List[AudioTrackInfo])
def list_sfx_tracks():
    """List copyright-safe cinematic sound effects."""
    tracks = audio_library.list_sfx_tracks()
    return [
        AudioTrackInfo(
            id=t["id"],
            title=t["title"],
            category=t["category"],
            genre=t["genre"],
            duration_seconds=t["duration_seconds"],
            license=t["license"],
            copyright_safe=t["copyright_safe"],
            stream_url=f"/api/cinematic/audio/{t['id']}/stream",
        )
        for t in tracks
    ]

@router.get("/audio/{track_id}/stream")
def stream_audio_track(track_id: str):
    """Stream a royalty-free audio file."""
    track = audio_library.get_track(track_id)
    if not track:
        raise HTTPException(status_code=404, detail="Audio track not found")

    file_path = Path(track["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio asset file missing on disk")

    return FileResponse(
        path=str(file_path),
        media_type="audio/aac",
        filename=file_path.name
    )

@router.post("/preview")
def generate_preview(req: CinematicPreviewRequest):
    """Generate an ultra-fast 4-second preview clip with applied cinematic effects."""
    try:
        preview_data = cinematic_editor.generate_preview(
            recording_id=req.recording_id,
            start_time=req.start_time,
            end_time=req.end_time,
            edit_mode=req.edit_mode,
            preset_name=req.preset_name,
            render_mode=req.render_mode,
            zoom_intensity=req.zoom_intensity or 1.0,
            slowmo_speed=req.slowmo_speed or 1.0,
            color_grading_intensity=req.color_grading_intensity or 1.0,
            audio_volume=req.audio_volume or 1.0,
            music_volume=req.music_volume or 0.0,
            music_track_id=req.music_track_id,
            sfx_track_id=req.sfx_track_id,
            preview_duration=req.preview_duration or 4.0,
        )
        return preview_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Preview generation failed: {str(e)}")

@router.get("/previews/{filename}")
def serve_preview(filename: str):
    """Stream preview video MP4."""
    preview_file = cinematic_editor.previews_dir / filename
    if not preview_file.exists():
        raise HTTPException(status_code=404, detail="Preview file not found or expired")

    return FileResponse(
        path=str(preview_file),
        media_type="video/mp4",
        filename=filename,
    )

@router.post("/render")
def render_cinematic_short(req: CinematicEditRequest, db: Session = Depends(get_db)):
    """
    Renders production-quality 9:16 vertical short with cinematic preset or raw gameplay.
    Verifies 1080x1920, duration, and H.264/AAC output using FFprobe.
    """
    recording_id = req.recording_id
    start_time = req.start_time
    end_time = req.end_time
    title = req.title

    # If clip_id or candidate_clip_id was supplied, resolve missing timestamps
    if req.clip_id:
        existing_clip = db.query(Clip).filter(Clip.id == req.clip_id).first()
        if existing_clip:
            recording_id = existing_clip.recording_id
            if start_time is None:
                start_time = existing_clip.start_time
            if end_time is None:
                end_time = existing_clip.end_time
            if not title:
                title = existing_clip.title

    elif req.candidate_clip_id:
        cand = db.query(CandidateClip).filter(CandidateClip.id == req.candidate_clip_id).first()
        if cand:
            recording_id = cand.recording_id
            if start_time is None:
                start_time = cand.start_time
            if end_time is None:
                end_time = cand.end_time
            if not title:
                title = cand.title

    if start_time is None or end_time is None:
        raise HTTPException(status_code=400, detail="Start time and end time are required.")

    if end_time <= start_time:
        raise HTTPException(status_code=400, detail=f"Invalid timeframe: end_time ({end_time}) <= start_time ({start_time})")

    try:
        render_result = cinematic_editor.render_cinematic_short(
            recording_id=recording_id,
            start_time=start_time,
            end_time=end_time,
            title=title,
            candidate_clip_id=req.candidate_clip_id,
            edit_mode=req.edit_mode,
            preset_name=req.preset_name,
            render_mode=req.render_mode,
            target_length=req.target_length or int(end_time - start_time),
            zoom_intensity=req.zoom_intensity or 1.0,
            slowmo_speed=req.slowmo_speed or 1.0,
            color_grading_intensity=req.color_grading_intensity or 1.0,
            audio_volume=req.audio_volume or 1.0,
            music_volume=req.music_volume or 0.0,
            music_track_id=req.music_track_id,
            sfx_track_id=req.sfx_track_id,
            transition_duration=req.transition_duration or 0.35,
            subtitles=req.subtitles or False,
            subtitle_text=req.subtitle_text,
            subtitle_style=req.subtitle_style or "vice_neon",
            fps=req.fps,
            use_gpu=req.use_gpu if req.use_gpu is not None else True,
            clip_id_override=req.clip_id,
        )

        return {
            "success": True,
            "clip": render_result,
            "verification": render_result.get("verification"),
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cinematic rendering failed: {str(e)}")
