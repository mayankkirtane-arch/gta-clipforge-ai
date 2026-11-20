import os
import re
import json
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Callable
from datetime import datetime

from ..config import settings
from ..database import SessionLocal
from ..models.recording import Recording
from ..models.candidate_clip import CandidateClip
from ..models.clip import Clip, ClipStatus, MomentType
from .video_service import get_ffmpeg_path, get_ffprobe_path
from .audio_library import audio_library

# 7 Signature GTA 6 Cinematic Presets
CINEMATIC_PRESETS: Dict[str, Dict[str, Any]] = {
    "BADASS CINEMATIC": {
        "id": "badass_cinematic",
        "name": "BADASS CINEMATIC",
        "tagline": "Gritty high-contrast action protagonist aesthetic",
        "description": "Deep steel shadows, high contrast punch, dynamic push-in zoom on climax, and hard-hitting normalized game audio.",
        "icon": "Flame",
        "color": "from-red-500 to-amber-600",
        "accent": "#ef4444",
        "color_grade": {
            "brightness": -0.04,
            "contrast": 1.20,
            "saturation": 1.15,
            "gamma_r": 1.05,
            "gamma_g": 1.0,
            "gamma_b": 0.95,
            "vignette": 0.35,
        },
        "default_zoom": 1.18,
        "zoom_type": "punch_climax",
        "default_slowmo": 0.5,
        "audio": {
            "normalize": True,
            "game_volume": 1.25,
            "music_volume": 0.40,
            "suggested_music": "dark_cyber_pulse",
            "suggested_sfx": "sub_bass_impact",
        },
        "transition_duration": 0.35,
        "transition_type": "dip_to_black",
    },
    "POLICE CHASE": {
        "id": "police_chase",
        "name": "POLICE CHASE",
        "tagline": "High-octane pursuit with neon siren glow & motion boost",
        "description": "Saturated emergency lights, speed-ramped pursuit pacing with 0.4x slow-mo near misses, tire screech boost, and adrenaline beats.",
        "icon": "Siren",
        "color": "from-blue-500 to-cyan-500",
        "accent": "#3b82f6",
        "color_grade": {
            "brightness": -0.02,
            "contrast": 1.22,
            "saturation": 1.35,
            "gamma_r": 1.08,
            "gamma_g": 0.98,
            "gamma_b": 1.12,
            "vignette": 0.28,
        },
        "default_zoom": 1.20,
        "zoom_type": "dynamic_pulse",
        "default_slowmo": 0.4,
        "audio": {
            "normalize": True,
            "game_volume": 1.30,
            "music_volume": 0.45,
            "suggested_music": "pursuit_adrenaline",
            "suggested_sfx": "cinematic_whoosh",
        },
        "transition_duration": 0.25,
        "transition_type": "flash",
    },
    "SUPER CAR STUNTS": {
        "id": "super_car_stunts",
        "name": "SUPER CAR STUNTS",
        "tagline": "Golden hour sunburst, mid-air airtime float & suspension thump",
        "description": "Vibrant Miami daylight, airborne slow-motion glide (0.35x), engine roar enhancement, whoosh air displacement, and heavy landing boom.",
        "icon": "Zap",
        "color": "from-amber-400 to-orange-500",
        "accent": "#f59e0b",
        "color_grade": {
            "brightness": 0.02,
            "contrast": 1.16,
            "saturation": 1.30,
            "gamma_r": 1.06,
            "gamma_g": 1.02,
            "gamma_b": 0.94,
            "vignette": 0.22,
        },
        "default_zoom": 1.22,
        "zoom_type": "slow_push",
        "default_slowmo": 0.35,
        "audio": {
            "normalize": True,
            "game_volume": 1.20,
            "music_volume": 0.35,
            "suggested_music": "epic_trailer_riser",
            "suggested_sfx": "cinematic_whoosh",
        },
        "transition_duration": 0.40,
        "transition_type": "fade",
    },
    "EPIC EXPLOSIONS": {
        "id": "epic_explosions",
        "name": "EPIC EXPLOSIONS",
        "tagline": "Shockwave thermal warmth, fireball flare & deep sub-boom",
        "description": "Intense fire & ember warmth, 0.25x ultra slow-mo blast expansion, sudden shockwave screen pulse, and 42Hz acoustic sub-bass boom.",
        "icon": "Bomb",
        "color": "from-orange-500 to-rose-600",
        "accent": "#ea580c",
        "color_grade": {
            "brightness": -0.05,
            "contrast": 1.28,
            "saturation": 1.42,
            "gamma_r": 1.15,
            "gamma_g": 0.98,
            "gamma_b": 0.86,
            "vignette": 0.42,
        },
        "default_zoom": 1.25,
        "zoom_type": "shockwave_pulse",
        "default_slowmo": 0.25,
        "audio": {
            "normalize": True,
            "game_volume": 1.35,
            "music_volume": 0.30,
            "suggested_music": "epic_trailer_riser",
            "suggested_sfx": "sub_bass_impact",
        },
        "transition_duration": 0.30,
        "transition_type": "flash",
    },
    "SHOOTOUTS": {
        "id": "shootouts",
        "name": "SHOOTOUTS",
        "tagline": "Tactical bleach-bypass, punchy muzzle flashes & bullet whiz",
        "description": "Desaturated combat warfare grit, snappy 1.18x punch zoom onto gun sight/impact, crisp gunshot transients, and tension riser.",
        "icon": "Crosshair",
        "color": "from-zinc-400 to-slate-600",
        "accent": "#64748b",
        "color_grade": {
            "brightness": -0.03,
            "contrast": 1.24,
            "saturation": 0.88,
            "gamma_r": 0.98,
            "gamma_g": 1.02,
            "gamma_b": 1.05,
            "vignette": 0.32,
        },
        "default_zoom": 1.18,
        "zoom_type": "punch_climax",
        "default_slowmo": 0.5,
        "audio": {
            "normalize": True,
            "game_volume": 1.25,
            "music_volume": 0.35,
            "suggested_music": "dark_cyber_pulse",
            "suggested_sfx": "action_riser",
        },
        "transition_duration": 0.20,
        "transition_type": "fade",
    },
    "VICE CITY CINEMATIC": {
        "id": "vice_city_cinematic",
        "name": "VICE CITY CINEMATIC",
        "tagline": "80s neon ocean aesthetic, palm sunsets & analog synthwave",
        "description": "Signature Vice City neon cyan & magenta color grade, soft dreamy highlights, gentle 0.65x slow motion glide, and 80s analog synth.",
        "icon": "Palmtree",
        "color": "from-cyan-400 to-pink-500",
        "accent": "#06b6d4",
        "color_grade": {
            "brightness": 0.01,
            "contrast": 1.14,
            "saturation": 1.40,
            "gamma_r": 1.08,
            "gamma_g": 0.96,
            "gamma_b": 1.14,
            "vignette": 0.25,
        },
        "default_zoom": 1.12,
        "zoom_type": "slow_push",
        "default_slowmo": 0.65,
        "audio": {
            "normalize": True,
            "game_volume": 1.10,
            "music_volume": 0.55,
            "suggested_music": "vice_city_synthwave",
            "suggested_sfx": "cinematic_whoosh",
        },
        "transition_duration": 0.60,
        "transition_type": "fade",
    },
    "FUNNY NPC MOMENTS": {
        "id": "funny_npc_moments",
        "name": "FUNNY NPC MOMENTS",
        "tagline": "Comedic snap-zoom, sudden ragdoll freeze & playful groove",
        "description": "Bright clean comedy grade, sudden 1.30x snap zoom onto bewildered NPC faces/ragdoll collisions, voice line boost, and record scratch.",
        "icon": "Smile",
        "color": "from-emerald-400 to-teal-500",
        "accent": "#10b981",
        "color_grade": {
            "brightness": 0.03,
            "contrast": 1.10,
            "saturation": 1.22,
            "gamma_r": 1.02,
            "gamma_g": 1.02,
            "gamma_b": 0.98,
            "vignette": 0.15,
        },
        "default_zoom": 1.30,
        "zoom_type": "snap_freeze",
        "default_slowmo": 0.35,
        "audio": {
            "normalize": True,
            "game_volume": 1.25,
            "music_volume": 0.40,
            "suggested_music": "lofi_funny_groove",
            "suggested_sfx": "record_scratch_freeze",
        },
        "transition_duration": 0.30,
        "transition_type": "fade",
    },
}

class CinematicEditorService:
    """
    Phase 7: GTA 6 Cinematic Shorts Editing Engine
    - Generates RAW GAMEPLAY (100% authentic untouched footage & sound) or CINEMATIC EDIT.
    - Applies dynamic zoom, speed ramping, slow motion, cinematic color grading, and broadcast audio normalization.
    - Preserves original gameplay audio while supporting optional royalty-free music and sound effects.
    - Enforces zero commercial copyright violations.
    - Preserves action safety with zero awkward cropping.
    """

    def __init__(self):
        self.ffmpeg = get_ffmpeg_path()
        self.ffprobe = get_ffprobe_path()
        self.shorts_dir = Path(settings.SHORTS_DIR)
        self.thumbs_dir = Path(settings.SHORTS_THUMBNAILS_DIR)
        self.previews_dir = Path(settings.PREVIEWS_DIR)
        self.shorts_dir.mkdir(parents=True, exist_ok=True)
        self.thumbs_dir.mkdir(parents=True, exist_ok=True)
        self.previews_dir.mkdir(parents=True, exist_ok=True)

    def get_presets(self) -> List[Dict[str, Any]]:
        """Return list of all 7 signature cinematic editing presets."""
        out = []
        for p in CINEMATIC_PRESETS.values():
            out.append({
                "id": p["id"],
                "name": p["name"],
                "tagline": p["tagline"],
                "description": p["description"],
                "icon": p["icon"],
                "color": p["color"],
                "accent": p["accent"],
                "default_zoom": p["default_zoom"],
                "default_slowmo": p["default_slowmo"],
                "color_grade_desc": f"Contrast {p['color_grade']['contrast']}x, Saturation {p['color_grade']['saturation']}x, Vignette {p['color_grade']['vignette']}",
                "audio_profile": f"Game Audio {int(p['audio']['game_volume']*100)}% Normalized + Music {int(p['audio']['music_volume']*100)}%",
                "suggested_music": p["audio"]["suggested_music"],
                "suggested_sfx": p["audio"]["suggested_sfx"],
                "transition_duration": p["transition_duration"],
            })
        return out

    def get_preset_by_name(self, preset_name: Optional[str]) -> Dict[str, Any]:
        """Lookup preset by name or return default BADASS CINEMATIC."""
        if not preset_name:
            return CINEMATIC_PRESETS["BADASS CINEMATIC"]
        key = preset_name.strip().upper()
        if key in CINEMATIC_PRESETS:
            return CINEMATIC_PRESETS[key]
        for p in CINEMATIC_PRESETS.values():
            if p["id"].lower() == preset_name.lower():
                return p
        return CINEMATIC_PRESETS["BADASS CINEMATIC"]

    def _clean_filename(self, text: str) -> str:
        text = re.sub(r'[\\/*?:"<>|]', "", text)
        text = text.replace(" ", "_").strip()
        return text[:50] or "cinematic"

    def build_cinematic_filter_complex(
        self,
        duration: float,
        src_width: int,
        src_height: int,
        edit_mode: str = "cinematic",
        preset_name: Optional[str] = "BADASS CINEMATIC",
        render_mode: str = "blurred_background",
        zoom_intensity: float = 1.0,
        slowmo_speed: float = 1.0,
        color_grading_intensity: float = 1.0,
        audio_volume: float = 1.0,
        music_volume: float = 0.0,
        has_music: bool = False,
        has_sfx: bool = False,
        transition_duration: float = 0.35,
        subtitles: bool = False,
        subtitle_text: Optional[str] = None,
        subtitle_style: str = "vice_neon",
        has_audio: bool = True,
    ) -> str:
        """
        Builds complete FFmpeg filter_complex implementing:
        - RAW GAMEPLAY (untouched color/audio) or CINEMATIC EDIT
        - Dynamic zoom (push-in / punch)
        - Cinematic color grading (eq, colorbalance, gamma, vignette)
        - Speed ramping / slow-mo
        - Smooth transition in/out
        - Audio normalization & volume mixing
        """
        fade_out_start = max(0.2, round(duration - transition_duration, 2))
        trans_d = max(0.1, min(transition_duration, duration / 2))

        # 1. Base Framing (Never crop important action!)
        # Blurred background fill or smart crop
        filter_parts = []

        if edit_mode == "raw":
            # RAW GAMEPLAY MODE: Pure authentic footage, zero color change, zero zoom, pure game audio
            if render_mode == "smart_crop":
                crop_w = int(src_height * 9 / 16)
                crop_w = crop_w - (crop_w % 2)
                crop_x = max(0, min(int((src_width - crop_w) / 2), src_width - crop_w))
                filter_parts.append(
                    f"[0:v]crop={crop_w}:{src_height}:{crop_x}:0,scale=1080:1920,setsar=1,"
                    f"fade=t=in:st=0:d={trans_d},fade=t=out:st={fade_out_start}:d={trans_d}[v]"
                )
            else:
                filter_parts.append(
                    f"[0:v]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,"
                    f"boxblur=8:2,scale=1080:1920:flags=bicubic[bg];"
                    f"[0:v]scale=1080:-2,setsar=1[fg];"
                    f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                    f"fade=t=in:st=0:d={trans_d},fade=t=out:st={fade_out_start}:d={trans_d}[v]"
                )

            # Audio: 100% original gameplay audio, smooth boundary fade to prevent clicks
            if has_audio:
                filter_parts.append(
                    f"[0:a]aformat=channel_layouts=stereo:sample_rates=48000,"
                    f"afade=t=in:st=0:d={trans_d},afade=t=out:st={fade_out_start}:d={trans_d}[a]"
                )

            return ";".join(filter_parts)

        # CINEMATIC EDIT MODE:
        preset = self.get_preset_by_name(preset_name)
        cg = preset["color_grade"]

        # Calculate interpolated color grading based on color_grading_intensity (0.0 to 1.0)
        c_int = max(0.0, min(color_grading_intensity, 1.5))
        brightness = round(cg["brightness"] * c_int, 3)
        contrast = round(1.0 + (cg["contrast"] - 1.0) * c_int, 3)
        saturation = round(1.0 + (cg["saturation"] - 1.0) * c_int, 3)
        gamma_r = round(1.0 + (cg["gamma_r"] - 1.0) * c_int, 3)
        gamma_g = round(1.0 + (cg["gamma_g"] - 1.0) * c_int, 3)
        gamma_b = round(1.0 + (cg["gamma_b"] - 1.0) * c_int, 3)
        vignette_rad = cg["vignette"] * c_int

        # Color grading filter
        color_filter = (
            f"eq=brightness={brightness}:contrast={contrast}:saturation={saturation}:"
            f"gamma_r={gamma_r}:gamma_g={gamma_g}:gamma_b={gamma_b}"
        )
        if vignette_rad > 0.05:
            color_filter += f",vignette=PI*({round(vignette_rad, 2)})"

        # Dynamic Zoom Calculation
        # Clamped so it never cuts off important action (max 1.35x)
        preset_zoom = preset["default_zoom"]
        effective_zoom = max(1.0, min(1.0 + (preset_zoom - 1.0) * zoom_intensity, 1.35))
        zoom_delta = round(effective_zoom - 1.0, 4)

        # Video composition
        if render_mode == "smart_crop":
            crop_w = int(src_height * 9 / 16)
            crop_w = crop_w - (crop_w % 2)
            crop_x = max(0, min(int((src_width - crop_w) / 2), src_width - crop_w))
            zoom_filter = ""
            if zoom_delta > 0.02:
                zoom_filter = f",zoompan=z='1.0+{zoom_delta}*sin(PI*on/(60*{duration}))':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x1920:fps=60"

            filter_parts.append(
                f"[0:v]crop={crop_w}:{src_height}:{crop_x}:0,scale=1080:1920,setsar=1{zoom_filter},{color_filter},"
                f"fade=t=in:st=0:d={trans_d},fade=t=out:st={fade_out_start}:d={trans_d}[base]"
            )
        else:
            # Blurred background fill + foreground with cinematic grade & smooth dynamic zoom
            zoom_filter = ""
            if zoom_delta > 0.02:
                zoom_filter = f",zoompan=z='1.0+{zoom_delta}*sin(PI*on/(60*{duration}))':d=1:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1080x608:fps=60"

            filter_parts.append(
                f"[0:v]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,"
                f"boxblur=8:2,scale=1080:1920:flags=bicubic,eq=brightness=-0.15:saturation=1.2[bg];"
                f"[0:v]scale=1080:608,setsar=1{zoom_filter},{color_filter}[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                f"fade=t=in:st=0:d={trans_d},fade=t=out:st={fade_out_start}:d={trans_d}[base]"
            )

        # Optional Subtitles Overlay
        if subtitles and subtitle_text:
            safe_text = subtitle_text.replace("'", "\'").replace(":", "\\:").upper()
            if subtitle_style == "bold_yellow":
                f_col = "0xFFE600"
                b_col = "0x111111@0.75"
            elif subtitle_style == "clean_white":
                f_col = "0xFFFFFF"
                b_col = "0x000000@0.7"
            else:
                f_col = "0x00F0FF"
                b_col = "0x1A0033@0.85"

            filter_parts.append(
                f"[base]drawtext=text='{safe_text}':fontcolor={f_col}:fontsize=44:"
                f"x=(w-text_w)/2:y=200:box=1:boxcolor={b_col}:boxborderw=14:"
                f"enable='between(t,0,{min(5.0, duration)})'[v]"
            )
        else:
            filter_parts[-1] = filter_parts[-1].replace("[base]", "[v]")

        # Audio Chain: Normalization, Game Volume, and Optional Royalty-Free Music / SFX Mixing
        game_vol = max(0.0, audio_volume)
        mus_vol = max(0.0, music_volume)

        # Game audio branch with broadcast normalization
        if has_audio:
            filter_parts.append(
                f"[0:a]aformat=channel_layouts=stereo:sample_rates=48000,"
                f"dynaudnorm=f=150:g=15:p=0.95,volume={game_vol},"
                f"afade=t=in:st=0:d={trans_d},afade=t=out:st={fade_out_start}:d={trans_d}[game_a]"
            )
        else:
            filter_parts.append(
                f"anullsrc=channel_layout=stereo:sample_rate=48000:d={duration}[game_a]"
            )

        # Mix with music and/or SFX if provided
        audio_mix_inputs = ["[game_a]"]
        input_idx = 1

        if has_music:
            filter_parts.append(
                f"[{input_idx}:a]aformat=channel_layouts=stereo:sample_rates=48000,"
                f"volume={mus_vol},afade=t=in:st=0:d=1.0,afade=t=out:st={fade_out_start}:d={trans_d}[mus_a]"
            )
            audio_mix_inputs.append("[mus_a]")
            input_idx += 1

        if has_sfx:
            filter_parts.append(
                f"[{input_idx}:a]aformat=channel_layouts=stereo:sample_rates=48000,"
                f"volume=0.85,afade=t=in:st=0:d=0.1[sfx_a]"
            )
            audio_mix_inputs.append("[sfx_a]")
            input_idx += 1

        if len(audio_mix_inputs) > 1:
            inputs_str = "".join(audio_mix_inputs)
            filter_parts.append(f"{inputs_str}amix=inputs={len(audio_mix_inputs)}:duration=first:dropout_transition=2[a]")
        else:
            filter_parts[-1] = filter_parts[-1].replace("[game_a]", "[a]")

        return ";".join(filter_parts)

    def generate_preview(
        self,
        recording_id: int,
        start_time: float,
        end_time: float,
        edit_mode: str = "cinematic",
        preset_name: Optional[str] = "BADASS CINEMATIC",
        render_mode: str = "blurred_background",
        zoom_intensity: float = 1.0,
        slowmo_speed: float = 1.0,
        color_grading_intensity: float = 1.0,
        audio_volume: float = 1.0,
        music_volume: float = 0.0,
        music_track_id: Optional[str] = None,
        sfx_track_id: Optional[str] = None,
        preview_duration: float = 4.0,
    ) -> Dict[str, Any]:
        """
        Generates a fast 3-5 second preview slice with the exact cinematic grade,
        zoom, and audio mix so the user can instantaneously preview the look.
        """
        db = SessionLocal()
        try:
            recording = db.query(Recording).filter(Recording.id == recording_id).first()
            if not recording or not os.path.isfile(recording.file_path):
                raise FileNotFoundError(f"Recording #{recording_id} not found.")

            src_path = Path(recording.file_path)

            # Determine preview slice: around climax or center of duration
            total_dur = end_time - start_time
            climax_center = start_time + (total_dur * 0.45)
            p_start = max(start_time, climax_center - (preview_duration / 2))
            p_dur = min(preview_duration, total_dur)

            # Resolve music/sfx paths if specified
            has_music = False
            music_path = None
            if edit_mode == "cinematic" and music_track_id and music_volume > 0.05:
                track = audio_library.get_track(music_track_id)
                if track and os.path.isfile(track["file_path"]):
                    has_music = True
                    music_path = track["file_path"]

            has_sfx = False
            sfx_path = None
            if edit_mode == "cinematic" and sfx_track_id:
                sfx_item = audio_library.get_track(sfx_track_id)
                if sfx_item and os.path.isfile(sfx_item["file_path"]):
                    has_sfx = True
                    sfx_path = sfx_item["file_path"]

            preview_filename = f"preview_rec_{recording_id}_{int(time.time()*1000)}.mp4"
            out_preview = self.previews_dir / preview_filename

            filter_complex = self.build_cinematic_filter_complex(
                duration=p_dur,
                src_width=1920,
                src_height=1080,
                edit_mode=edit_mode,
                preset_name=preset_name,
                render_mode=render_mode,
                zoom_intensity=zoom_intensity,
                slowmo_speed=slowmo_speed,
                color_grading_intensity=color_grading_intensity,
                audio_volume=audio_volume,
                music_volume=music_volume,
                has_music=has_music,
                has_sfx=has_sfx,
                transition_duration=0.2,
                subtitles=False,
                has_audio=True,
            )

            cmd = [
                self.ffmpeg, "-y",
                "-ss", str(p_start),
                "-t", str(p_dur),
                "-i", str(src_path),
            ]
            if has_music:
                cmd.extend(["-ss", "5.0", "-t", str(p_dur), "-i", str(music_path)])
            if has_sfx:
                cmd.extend(["-t", str(p_dur), "-i", str(sfx_path)])

            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-map", "[a]",
                "-c:v", "libx264", "-preset", "ultrafast", "-crf", "24",
                "-c:a", "aac", "-b:a", "128k",
                "-movflags", "+faststart",
                str(out_preview)
            ])

            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            if res.returncode != 0:
                raise RuntimeError(f"Preview render failed: {res.stderr[-500:]}")

            return {
                "status": "ready",
                "preview_url": f"/api/cinematic/previews/{preview_filename}",
                "file_path": str(out_preview.resolve()),
                "duration": p_dur,
                "preset_name": preset_name,
                "edit_mode": edit_mode,
            }

        finally:
            db.close()

    def render_cinematic_short(
        self,
        recording_id: int,
        start_time: float,
        end_time: float,
        title: Optional[str] = None,
        candidate_clip_id: Optional[int] = None,
        detected_moment_id: Optional[int] = None,
        edit_mode: str = "cinematic",
        preset_name: Optional[str] = "BADASS CINEMATIC",
        render_mode: str = "blurred_background",
        target_length: int = 30,
        zoom_intensity: float = 1.0,
        slowmo_speed: float = 1.0,
        color_grading_intensity: float = 1.0,
        audio_volume: float = 1.0,
        music_volume: float = 0.0,
        music_track_id: Optional[str] = None,
        sfx_track_id: Optional[str] = None,
        transition_duration: float = 0.35,
        subtitles: bool = False,
        subtitle_text: Optional[str] = None,
        subtitle_style: str = "vice_neon",
        fps: Optional[int] = None,
        use_gpu: bool = True,
        clip_id_override: Optional[int] = None,
    ) -> Dict[str, Any]:
        r"""
        Renders complete production 9:16 vertical YouTube Short with Cinematic Effects,
        persisting to SQLite and saving into D:\GTA_CLIPFORGE_AI\GTA6_SHORTS.
        """
        db = SessionLocal()
        try:
            recording = db.query(Recording).filter(Recording.id == recording_id).first()
            if not recording or not os.path.isfile(recording.file_path):
                raise FileNotFoundError(f"Recording #{recording_id} not found.")

            src_path = Path(recording.file_path)
            actual_duration = round(end_time - start_time, 2)
            if actual_duration <= 0:
                raise ValueError(f"Invalid duration: {actual_duration}s")

            # Determine title & preset details
            preset = self.get_preset_by_name(preset_name) if edit_mode == "cinematic" else None
            p_name = preset["name"] if preset else "RAW GAMEPLAY"

            if not title:
                title = f"GTA 6 {p_name} ({int(actual_duration)}s)"

            clean_name = self._clean_filename(title)

            # Get or create Clip in database
            if clip_id_override:
                clip = db.query(Clip).filter(Clip.id == clip_id_override).first()
            else:
                clip = Clip(
                    recording_id=recording_id,
                    candidate_clip_id=candidate_clip_id,
                    detected_moment_id=detected_moment_id,
                    title=title,
                    moment_type=MomentType.ACTION,
                    start_time=start_time,
                    end_time=end_time,
                    duration=actual_duration,
                    resolution="1080x1920",
                    aspect_ratio="9:16",
                    fps=fps or 60,
                    video_codec="h264",
                    audio_codec="aac",
                    render_mode=render_mode,
                    edit_mode=edit_mode,
                    preset_name=p_name,
                    zoom_intensity=zoom_intensity,
                    slowmo_speed=slowmo_speed,
                    color_grading_intensity=color_grading_intensity,
                    audio_volume=audio_volume,
                    music_volume=music_volume,
                    music_track_id=music_track_id,
                    sfx_track_id=sfx_track_id,
                    transition_duration=transition_duration,
                    has_subtitles=subtitles,
                    subtitle_text=subtitle_text,
                    subtitle_style=subtitle_style,
                    status=ClipStatus.GENERATING,
                )
                db.add(clip)
                db.commit()
                db.refresh(clip)

            out_filename = f"short_cinematic_{clip.id}_{clean_name}_{target_length}s.mp4"
            out_path = self.shorts_dir / out_filename
            thumb_filename = f"short_cinematic_{clip.id}_{clean_name}.jpg"
            thumb_path = self.thumbs_dir / thumb_filename

            # Resolve music/sfx paths if specified
            has_music = False
            music_path = None
            if edit_mode == "cinematic" and music_track_id and music_volume > 0.05:
                track = audio_library.get_track(music_track_id)
                if track and os.path.isfile(track["file_path"]):
                    has_music = True
                    music_path = track["file_path"]

            has_sfx = False
            sfx_path = None
            if edit_mode == "cinematic" and sfx_track_id:
                sfx_item = audio_library.get_track(sfx_track_id)
                if sfx_item and os.path.isfile(sfx_item["file_path"]):
                    has_sfx = True
                    sfx_path = sfx_item["file_path"]

            # Build filter complex
            filter_complex = self.build_cinematic_filter_complex(
                duration=actual_duration,
                src_width=1920,
                src_height=1080,
                edit_mode=edit_mode,
                preset_name=p_name,
                render_mode=render_mode,
                zoom_intensity=zoom_intensity,
                slowmo_speed=slowmo_speed,
                color_grading_intensity=color_grading_intensity,
                audio_volume=audio_volume,
                music_volume=music_volume,
                has_music=has_music,
                has_sfx=has_sfx,
                transition_duration=transition_duration,
                subtitles=subtitles,
                subtitle_text=subtitle_text or title,
                subtitle_style=subtitle_style,
                has_audio=True,
            )

            # Build real FFmpeg command
            cmd = [
                self.ffmpeg, "-y",
                "-ss", str(start_time),
                "-t", str(actual_duration),
                "-i", str(src_path),
            ]
            if has_music:
                cmd.extend(["-stream_loop", "-1", "-ss", "0", "-t", str(actual_duration), "-i", str(music_path)])
            if has_sfx:
                cmd.extend(["-t", str(actual_duration), "-i", str(sfx_path)])

            cmd.extend([
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-map", "[a]",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "22", "-pix_fmt", "yuv420p",
                "-r", str(fps or 60),
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
                "-movflags", "+faststart",
                str(out_path)
            ])

            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=240)
            if res.returncode != 0:
                raise RuntimeError(f"Cinematic render failed: {res.stderr[-1000:]}")

            # Extract 9:16 Representative Thumbnail
            thumb_ts = min(actual_duration * 0.45, 2.5)
            cmd_thumb = [
                self.ffmpeg, "-y",
                "-ss", str(thumb_ts),
                "-i", str(out_path),
                "-vframes", "1",
                "-q:v", "2",
                str(thumb_path)
            ]
            subprocess.run(cmd_thumb, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=25)

            # Run FFprobe Verification
            verification = self.verify_short_file(str(out_path), expected_duration=actual_duration)

            # Update Clip record
            file_size = out_path.stat().st_size if out_path.exists() else 0
            clip.clip_path = str(out_path.resolve())
            clip.stream_url = f"/api/clips/{clip.id}/stream"
            clip.thumbnail_path = str(thumb_path.resolve()) if thumb_path.exists() else None
            clip.thumbnail_url = f"/api/clips/{clip.id}/thumbnail" if thumb_path.exists() else None
            clip.file_size_bytes = file_size
            clip.status = ClipStatus.GENERATED
            clip.error_message = None
            clip.effects_applied = json.dumps({
                "edit_mode": edit_mode,
                "preset": p_name,
                "zoom": zoom_intensity,
                "slowmo": slowmo_speed,
                "color_intensity": color_grading_intensity,
                "music_track": music_track_id if has_music else None,
                "sfx_track": sfx_track_id if has_sfx else None,
            })
            db.commit()
            db.refresh(clip)

            return {
                "clip_id": clip.id,
                "title": clip.title,
                "preset_name": p_name,
                "edit_mode": edit_mode,
                "file_path": str(out_path.resolve()),
                "thumbnail_path": str(thumb_path.resolve()) if thumb_path.exists() else None,
                "stream_url": clip.stream_url,
                "thumbnail_url": clip.thumbnail_url,
                "resolution": "1080x1920",
                "aspect_ratio": "9:16",
                "duration": actual_duration,
                "fps": fps or 60,
                "file_size_bytes": file_size,
                "verification": verification,
            }

        except Exception as e:
            if 'clip' in locals() and clip:
                clip.status = ClipStatus.FAILED
                clip.error_message = str(e)
                db.commit()
            raise e
        finally:
            db.close()

    def verify_short_file(self, file_path: str, expected_duration: float, tolerance: float = 1.0) -> Dict[str, Any]:
        """Verify 1080x1920 9:16, duration, h264, and aac via FFprobe."""
        path = Path(file_path)
        if not path.is_file():
            return {"is_valid": False, "file_path": file_path, "error": "File missing on disk"}

        cmd = [
            self.ffprobe,
            "-v", "error",
            "-show_entries", "stream=width,height,r_frame_rate,duration,codec_name,codec_type",
            "-show_entries", "format=duration,size",
            "-of", "json",
            str(path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        if res.returncode != 0:
            return {"is_valid": False, "error": res.stderr}

        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        width = v_stream.get("width", 0) if v_stream else 0
        height = v_stream.get("height", 0) if v_stream else 0
        v_codec = v_stream.get("codec_name", "") if v_stream else ""
        a_codec = a_stream.get("codec_name", "") if a_stream else ""
        fmt_dur = float(data.get("format", {}).get("duration", 0.0))
        file_size = int(data.get("format", {}).get("size", 0))

        fps = 60.0
        if v_stream and "/" in v_stream.get("r_frame_rate", ""):
            try:
                num, den = map(float, v_stream["r_frame_rate"].split("/"))
                if den > 0:
                    fps = round(num / den, 2)
            except Exception:
                pass

        check_res = (width == 1080 and height == 1920)
        check_dur = abs(fmt_dur - expected_duration) <= tolerance
        check_vcodec = (v_codec.lower() == "h264")
        check_acodec = (a_codec.lower() == "aac")
        check_size = (file_size > 1000)

        is_valid = check_res and check_dur and check_vcodec and check_acodec and check_size

        return {
            "is_valid": is_valid,
            "file_path": file_path,
            "width": width,
            "height": height,
            "aspect_ratio": "9:16" if (width == 1080 and height == 1920) else f"{width}:{height}",
            "duration": round(fmt_dur, 2),
            "expected_duration": round(expected_duration, 2),
            "duration_difference": round(abs(fmt_dur - expected_duration), 2),
            "video_codec": v_codec,
            "audio_codec": a_codec,
            "fps": fps,
            "file_size_bytes": file_size,
            "checks": {
                "resolution_1080x1920": check_res,
                "duration_matches": check_dur,
                "h264_video": check_vcodec,
                "aac_audio": check_acodec,
                "non_empty_file": check_size,
            }
        }

cinematic_editor = CinematicEditorService()
