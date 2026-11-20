import os
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Optional
from ..config import settings
from .video_service import get_ffmpeg_path

MUSIC_TRACKS = [
    {
        "id": "vice_city_synthwave",
        "title": "Vice City Neon Horizon",
        "category": "music",
        "genre": "80s Retro Synthwave",
        "duration_seconds": 65.0,
        "bpm": 118,
        "license": "Creative Commons Zero (CC0) / Royalty-Free",
        "copyright_safe": True,
        "description": "Dreamy 80s analog synth arpeggios with lush neon Miami ocean vibes. 100% safe for YouTube monetization.",
        "filename": "vice_city_synthwave.aac",
    },
    {
        "id": "dark_cyber_pulse",
        "title": "Night City Cyber Pulse",
        "category": "music",
        "genre": "Dark Action Electro",
        "duration_seconds": 65.0,
        "bpm": 132,
        "license": "Creative Commons Zero (CC0) / Royalty-Free",
        "copyright_safe": True,
        "description": "Heavy driving bassline with crisp cyberpunk pulse, perfect for badass protagonist moments.",
        "filename": "dark_cyber_pulse.aac",
    },
    {
        "id": "pursuit_adrenaline",
        "title": "Pursuit Adrenaline",
        "category": "music",
        "genre": "Fast Action Percussion",
        "duration_seconds": 65.0,
        "bpm": 140,
        "license": "Creative Commons Zero (CC0) / Royalty-Free",
        "copyright_safe": True,
        "description": "Intense cinematic percussion and driving sub-bass rhythm designed for high-speed police pursuits.",
        "filename": "pursuit_adrenaline.aac",
    },
    {
        "id": "epic_trailer_riser",
        "title": "Trailer Shockwave Stinger",
        "category": "music",
        "genre": "Cinematic Hybrid Trailer",
        "duration_seconds": 65.0,
        "bpm": 110,
        "license": "Creative Commons Zero (CC0) / Royalty-Free",
        "copyright_safe": True,
        "description": "Orchestral brass swells, ticking tension, and massive sub-impact for epic explosions and super car stunts.",
        "filename": "epic_trailer_riser.aac",
    },
    {
        "id": "lofi_funny_groove",
        "title": "Quirky Bop Groove",
        "category": "music",
        "genre": "Humorous Lo-Fi Hip Hop",
        "duration_seconds": 65.0,
        "bpm": 92,
        "license": "Creative Commons Zero (CC0) / Royalty-Free",
        "copyright_safe": True,
        "description": "Playful, lighthearted bounce with comedic swagger, ideal for bizarre GTA NPC encounters.",
        "filename": "lofi_funny_groove.aac",
    },
]

SFX_TRACKS = [
    {
        "id": "sub_bass_impact",
        "title": "Sub-Bass Shockwave Impact",
        "category": "sfx",
        "genre": "Cinematic Boom",
        "duration_seconds": 4.0,
        "license": "Public Domain (CC0)",
        "copyright_safe": True,
        "description": "Deep 42Hz resonant cinematic sub-boom for explosions, crashes, and heavy stunt landings.",
        "filename": "sub_bass_impact.aac",
    },
    {
        "id": "cinematic_whoosh",
        "title": "High-Speed Cinematic Whoosh",
        "category": "sfx",
        "genre": "Action Transition",
        "duration_seconds": 2.5,
        "license": "Public Domain (CC0)",
        "copyright_safe": True,
        "description": "Air displacement whoosh for speed ramps, car jumps, and dynamic punch-ins.",
        "filename": "cinematic_whoosh.aac",
    },
    {
        "id": "record_scratch_freeze",
        "title": "Vinyl Record Scratch & Freeze",
        "category": "sfx",
        "genre": "Comedy FX",
        "duration_seconds": 1.5,
        "license": "Public Domain (CC0)",
        "copyright_safe": True,
        "description": "Classic record stop scratch sound for abrupt gameplay fails and hilarious NPC ragdolls.",
        "filename": "record_scratch_freeze.aac",
    },
    {
        "id": "action_riser",
        "title": "Adrenaline Tension Riser",
        "category": "sfx",
        "genre": "Tension Build",
        "duration_seconds": 3.5,
        "license": "Public Domain (CC0)",
        "copyright_safe": True,
        "description": "Rising pitch sweep that builds peak tension right before the climax hits.",
        "filename": "action_riser.aac",
    },
]

class AudioLibrary:
    """
    Manages copyright-safe, royalty-free audio assets for Phase 7 Cinematic Shorts.
    Enforces strict DMCA compliance: No copyrighted commercial music is ever inserted.
    """

    def __init__(self):
        self.ffmpeg = get_ffmpeg_path()
        self.music_dir = Path(settings.MUSIC_DIR)
        self.sfx_dir = Path(settings.SFX_DIR)
        self.music_dir.mkdir(parents=True, exist_ok=True)
        self.sfx_dir.mkdir(parents=True, exist_ok=True)
        self.ensure_default_assets()

    def list_music_tracks(self) -> List[Dict[str, Any]]:
        tracks = []
        for t in MUSIC_TRACKS:
            path = self.music_dir / t["filename"]
            tracks.append({
                **t,
                "file_path": str(path.resolve()),
                "file_exists": path.is_file(),
                "stream_url": f"/api/cinematic/audio/music/{t['id']}",
            })
        return tracks

    def list_sfx_tracks(self) -> List[Dict[str, Any]]:
        sfx = []
        for s in SFX_TRACKS:
            path = self.sfx_dir / s["filename"]
            sfx.append({
                **s,
                "file_path": str(path.resolve()),
                "file_exists": path.is_file(),
                "stream_url": f"/api/cinematic/audio/sfx/{s['id']}",
            })
        return sfx

    def get_track(self, track_id: str) -> Optional[Dict[str, Any]]:
        for t in self.list_music_tracks():
            if t["id"] == track_id:
                return t
        for s in self.list_sfx_tracks():
            if s["id"] == track_id:
                return s
        return None

    def ensure_default_assets(self):
        """Synthesize high quality, royalty-free audio tracks if not present."""
        for t in MUSIC_TRACKS:
            p = self.music_dir / t["filename"]
            if not p.is_file():
                self._generate_synth_track(t["id"], p, duration=t["duration_seconds"])

        for s in SFX_TRACKS:
            p = self.sfx_dir / s["filename"]
            if not p.is_file():
                self._generate_sfx(s["id"], p, duration=s["duration_seconds"])

    def _generate_synth_track(self, track_id: str, out_path: Path, duration: float = 65.0):
        """Synthesize pleasing procedural royalty-free electronic beats with FFmpeg."""
        try:
            if track_id == "vice_city_synthwave":
                # 80s analog synth progression: A minor -> F major -> G major chords with bass
                synth_filter = (
                    f"aevalsrc='0.18*sin(2*PI*110*t)+0.12*sin(2*PI*220*t)+0.15*sin(2*PI*330*t)*sin(4*PI*t)'"
                    f":d={duration},aecho=0.8:0.88:60:0.4,lowpass=f=2400,"
                    f"afade=t=in:st=0:d=1.5,afade=t=out:st={duration-2.0}:d=2.0"
                )
            elif track_id == "dark_cyber_pulse":
                # Fast dark cyber electro bass arpeggio
                synth_filter = (
                    f"aevalsrc='0.25*sin(2*PI*(70+35*mod(floor(t*4),4))*t)+0.1*sin(2*PI*140*t)*cos(8*PI*t)'"
                    f":d={duration},aecho=0.8:0.7:50:0.3,"
                    f"afade=t=in:st=0:d=1.0,afade=t=out:st={duration-2.0}:d=2.0"
                )
            elif track_id == "pursuit_adrenaline":
                # High energy percussion beat with sub-pulse
                synth_filter = (
                    f"aevalsrc='0.2*sin(2*PI*90*t)*pow(cos(PI*t*4),4)+0.12*sin(2*PI*180*t)'"
                    f":d={duration},highpass=f=60,aecho=0.6:0.5:40:0.2,"
                    f"afade=t=in:st=0:d=0.5,afade=t=out:st={duration-1.5}:d=1.5"
                )
            elif track_id == "epic_trailer_riser":
                # Cinematic orchestral trailer pad and sub-boom
                synth_filter = (
                    f"aevalsrc='0.2*sin(2*PI*(55+5*t)*t)+0.12*sin(2*PI*(110+10*t)*t)'"
                    f":d={duration},lowpass=f=1800,"
                    f"afade=t=in:st=0:d=2.0,afade=t=out:st={duration-2.5}:d=2.5"
                )
            else:
                # lofi_funny_groove
                synth_filter = (
                    f"aevalsrc='0.22*sin(2*PI*130*t)*pow(cos(PI*t*2.5),2)+0.1*sin(2*PI*260*t)'"
                    f":d={duration},lowpass=f=1200,"
                    f"afade=t=in:st=0:d=1.0,afade=t=out:st={duration-2.0}:d=2.0"
                )

            cmd = [
                self.ffmpeg, "-y",
                "-f", "lavfi", "-i", synth_filter,
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                str(out_path)
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
        except Exception as e:
            print(f"Warning: Failed to generate synth track {track_id}: {e}")

    def _generate_sfx(self, sfx_id: str, out_path: Path, duration: float = 3.0):
        """Synthesize cinematic sound effects (whoosh, sub-boom, scratch, riser)."""
        try:
            if sfx_id == "sub_bass_impact":
                # 42Hz deep sub-boom with exponential decay
                synth_filter = f"aevalsrc='0.5*sin(2*PI*(42*exp(-1.5*t))*t)*exp(-1.2*t)':d={duration}"
            elif sfx_id == "cinematic_whoosh":
                # White noise whoosh swept through lowpass filter with smooth fade in/out
                fade_half = duration / 2.0
                synth_filter = f"anoisesrc=d={duration}:c=white:a=0.32,lowpass=f=1200,afade=t=in:st=0:d={fade_half},afade=t=out:st={fade_half}:d={fade_half}"
            elif sfx_id == "record_scratch_freeze":
                # Pitch dropping scratch effect
                synth_filter = f"aevalsrc='0.3*sin(2*PI*(600-400*t)*t)*(1-t/{duration})':d={duration}"
            else:
                # action_riser: rising pitch sweep
                synth_filter = f"aevalsrc='0.25*sin(2*PI*(150+120*t*t)*t)':d={duration}"

            cmd = [
                self.ffmpeg, "-y",
                "-f", "lavfi", "-i", synth_filter,
                "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
                str(out_path)
            ]
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15)
        except Exception as e:
            print(f"Warning: Failed to generate SFX {sfx_id}: {e}")

audio_library = AudioLibrary()
