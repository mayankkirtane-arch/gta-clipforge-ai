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
from ..models.detected_moment import DetectedMoment
from ..models.clip import Clip, ClipStatus, MomentType
from ..services.video_service import get_ffmpeg_path, get_ffprobe_path

class ShortsGenerator:
    r"""
    GTA CLIPFORGE AI — Phase 6 Automatic YouTube Shorts Generator
    - Converts 16:9 GTA gameplay recordings into professional 9:16 (1080x1920) vertical YouTube Shorts.
    - Preserves action & original gameplay sound with zero distortion or stretching.
    - Blurred background fill or smart action focal cropping.
    - Avoids abrupt cuts with smooth video & audio crossfades.
    - Optional gamer hook titles / subtitles.
    - Saves all generated Shorts into D:\GTA_CLIPFORGE_AI\GTA6_SHORTS.
    - Runs FFprobe verification on all generated video outputs.
    """

    def __init__(self):
        self.ffmpeg = get_ffmpeg_path()
        self.ffprobe = get_ffprobe_path()
        self.shorts_dir = Path(settings.SHORTS_DIR)
        self.thumbs_dir = Path(settings.SHORTS_THUMBNAILS_DIR)
        self.shorts_dir.mkdir(parents=True, exist_ok=True)
        self.thumbs_dir.mkdir(parents=True, exist_ok=True)

    def extract_source_info(self, video_path: str) -> Dict[str, Any]:
        """Extract resolution, fps, duration, and audio properties using FFprobe."""
        cmd = [
            self.ffprobe,
            "-v", "error",
            "-show_entries", "stream=width,height,r_frame_rate,duration,codec_name,codec_type,channels,sample_rate",
            "-show_entries", "format=duration,size",
            "-of", "json",
            str(video_path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        if res.returncode != 0:
            raise ValueError(f"FFprobe metadata probe failed: {res.stderr}")
        
        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        if not v_stream:
            raise ValueError("No video stream found in source.")

        width = int(v_stream.get("width", 1920))
        height = int(v_stream.get("height", 1080))

        fps = 60.0
        r_fr = v_stream.get("r_frame_rate", "60/1")
        if "/" in r_fr:
            try:
                num, den = map(float, r_fr.split("/"))
                if den > 0:
                    fps = round(num / den, 2)
            except Exception:
                fps = 60.0

        # Output target fps: 60 if source >= 45, otherwise 30
        target_fps = 60 if fps >= 45.0 else 30

        total_dur = 0.0
        fmt_dur = data.get("format", {}).get("duration")
        if fmt_dur:
            try:
                total_dur = float(fmt_dur)
            except Exception:
                pass

        return {
            "width": width,
            "height": height,
            "source_fps": fps,
            "target_fps": target_fps,
            "total_duration": total_dur,
            "has_audio": a_stream is not None,
            "audio_codec": a_stream.get("codec_name") if a_stream else None,
        }

    def _clean_filename(self, text: str) -> str:
        """Sanitize text for safe filesystem usage."""
        text = re.sub(r'[\\/*?:"<>|]', "", text)
        text = text.replace(" ", "_").strip()
        return text[:50] or "short"

    def _escape_drawtext(self, text: str) -> str:
        """Escape text for FFmpeg drawtext filter."""
        text = text.replace("\\", "\\\\").replace("'", "\'").replace(":", "\\:").replace("%", "\\%")
        return text

    def build_filter_complex(
        self,
        render_mode: str,
        duration: float,
        src_width: int,
        src_height: int,
        focal_x: float = 0.5,
        subtitles: bool = False,
        subtitle_text: Optional[str] = None,
        subtitle_style: str = "vice_neon",
        has_audio: bool = True,
    ) -> str:
        """
        Build exact 9:16 (1080x1920) FFmpeg filter complex without stretching.
        Applies smooth video fade-in (0.35s) and fade-out (0.5s) to eliminate abrupt cuts.
        Also configures stereo AAC audio fade-in (0.3s) and fade-out (0.5s) into [a].
        """
        fade_out_start = max(0.5, round(duration - 0.5, 2))
        v_filters = []

        if render_mode == "smart_crop":
            # Smart vertical crop centered on action focal point
            crop_w = int(src_height * 9 / 16)
            crop_w = crop_w - (crop_w % 2)  # Ensure even
            max_x = max(0, src_width - crop_w)
            center_x = int(focal_x * src_width - crop_w / 2)
            crop_x = max(0, min(center_x, max_x))
            crop_x = crop_x - (crop_x % 2)

            v_filters.append(
                f"[0:v]crop={crop_w}:{src_height}:{crop_x}:0,scale=1080:1920,setsar=1,"
                f"fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out_start}:d=0.5[base]"
            )

        elif render_mode == "action_hybrid":
            # Hybrid: ambient background fill + 1.25x action zoom foreground
            v_filters.append(
                f"[0:v]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,"
                f"boxblur=8:2,scale=1080:1920:flags=bicubic,eq=brightness=-0.12:saturation=1.2[bg];"
                f"[0:v]scale=1280:-2,setsar=1[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                f"fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out_start}:d=0.5[base]"
            )

        else:
            # Standard & recommended: "blurred_background" (100% action preservation, zero stretch)
            # Ultra-fast high quality bokeh: scale down -> boxblur -> scale up to 1080x1920
            v_filters.append(
                f"[0:v]scale=270:480:force_original_aspect_ratio=increase,crop=270:480,"
                f"boxblur=8:2,scale=1080:1920:flags=bicubic,eq=brightness=-0.12:saturation=1.25[bg];"
                f"[0:v]scale=1080:-2,setsar=1[fg];"
                f"[bg][fg]overlay=(W-w)/2:(H-h)/2,"
                f"fade=t=in:st=0:d=0.35,fade=t=out:st={fade_out_start}:d=0.5[base]"
            )

        # Optional Title/Hook Subtitle overlay
        if subtitles and subtitle_text:
            safe_text = self._escape_drawtext(subtitle_text.upper())
            # Vice City neon cyan/pink box or bold yellow
            if subtitle_style == "bold_yellow":
                font_color = "0xFFE600"
                box_color = "0x111111@0.75"
            elif subtitle_style == "clean_white":
                font_color = "0xFFFFFF"
                box_color = "0x000000@0.7"
            else:
                # Default "vice_neon": Vice City gaming neon
                font_color = "0x00F0FF"
                box_color = "0x1A0033@0.8"

            # Draw hook caption in upper third with box padding
            drawtext_str = (
                f"[base]drawtext=text='{safe_text}':fontcolor={font_color}:fontsize=44:"
                f"x=(w-text_w)/2:y=200:box=1:boxcolor={box_color}:boxborderw=14:"
                f"enable='between(t,0,{min(5.0, duration)})'[v]"
            )
            v_filters.append(drawtext_str)
        else:
            # Map base to [v]
            v_filters[-1] = v_filters[-1].replace("[base]", "[v]")

        # Audio filter: smooth 0.3s fade-in and 0.5s fade-out, preserve gameplay sound
        fade_out_audio = max(0.5, round(duration - 0.5, 2))
        if has_audio:
            v_filters.append(
                f"[0:a]aformat=channel_layouts=stereo:sample_rates=48000,"
                f"afade=t=in:st=0:d=0.3,afade=t=out:st={fade_out_audio}:d=0.5[a]"
            )

        return ";".join(v_filters)

    def generate_single_short(
        self,
        recording_id: int,
        start_time: float,
        end_time: float,
        title: Optional[str] = None,
        candidate_clip_id: Optional[int] = None,
        detected_moment_id: Optional[int] = None,
        target_length: int = 30,
        render_mode: str = "blurred_background",
        subtitles: bool = False,
        subtitle_text: Optional[str] = None,
        subtitle_style: str = "vice_neon",
        fps: Optional[int] = None,
        use_gpu: bool = True,
        clip_id_override: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Generate a single 9:16 YouTube Short clip using real FFmpeg processing.
        """
        db = SessionLocal()
        try:
            recording = db.query(Recording).filter(Recording.id == recording_id).first()
            if not recording or not os.path.isfile(recording.file_path):
                raise FileNotFoundError(f"Recording file not found on disk: {recording.file_path if recording else recording_id}")

            src_path = Path(recording.file_path)
            src_info = self.extract_source_info(str(src_path))
            target_fps = fps or src_info["target_fps"]

            # Validate & clamp timing boundaries
            actual_duration = round(end_time - start_time, 2)
            if actual_duration <= 0:
                raise ValueError(f"Invalid duration: {actual_duration}s (start={start_time}, end={end_time})")

            # Determine Title & MomentType
            candidate = None
            if candidate_clip_id:
                candidate = db.query(CandidateClip).filter(CandidateClip.id == candidate_clip_id).first()
                if candidate and not title:
                    title = candidate.title
                if candidate and not subtitle_text:
                    subtitle_text = candidate.category_label

            if not title:
                title = f"GTA 6 Action Highlight #{int(start_time)}s"

            clean_name = self._clean_filename(title)
            timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Get or create Clip record
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
                    fps=target_fps,
                    video_codec="h264",
                    audio_codec="aac",
                    render_mode=render_mode,
                    has_subtitles=subtitles,
                    subtitle_text=subtitle_text,
                    subtitle_style=subtitle_style,
                    status=ClipStatus.GENERATING,
                )
                db.add(clip)
                db.commit()
                db.refresh(clip)

            out_filename = f"short_{clip.id}_{clean_name}_{target_length}s.mp4"
            out_path = self.shorts_dir / out_filename
            thumb_filename = f"short_{clip.id}_{clean_name}.jpg"
            thumb_path = self.thumbs_dir / thumb_filename

            # Build filter complex
            filter_complex = self.build_filter_complex(
                render_mode=render_mode,
                duration=actual_duration,
                src_width=src_info["width"],
                src_height=src_info["height"],
                focal_x=0.5,
                subtitles=subtitles,
                subtitle_text=subtitle_text or title,
                subtitle_style=subtitle_style,
                has_audio=src_info["has_audio"],
            )

            # Check GPU NVENC first if requested
            used_gpu = False
            encode_success = False

            if use_gpu and settings.GPU_ACCELERATION:
                cmd_gpu = [
                    self.ffmpeg,
                    "-y",
                    "-ss", str(start_time),
                    "-t", str(actual_duration),
                    "-i", str(src_path),
                ]
                if not src_info["has_audio"]:
                    cmd_gpu.extend(["-f", "lavfi", "-t", str(actual_duration), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"])

                cmd_gpu.extend([
                    "-filter_complex", filter_complex,
                    "-map", "[v]",
                ])
                if src_info["has_audio"]:
                    cmd_gpu.extend(["-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"])
                else:
                    cmd_gpu.extend(["-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"])

                cmd_gpu.extend([
                    "-c:v", "h264_nvenc",
                    "-preset", "p4",
                    "-cq", "23",
                    "-pix_fmt", "yuv420p",
                    "-r", str(target_fps),
                    "-movflags", "+faststart",
                    str(out_path)
                ])

                try:
                    res_gpu = subprocess.run(cmd_gpu, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=180)
                    if res_gpu.returncode == 0 and out_path.exists() and out_path.stat().st_size > 5000:
                        used_gpu = True
                        encode_success = True
                except Exception:
                    pass

            # CPU fallback with libx264
            if not encode_success:
                cmd_cpu = [
                    self.ffmpeg,
                    "-y",
                    "-ss", str(start_time),
                    "-t", str(actual_duration),
                    "-i", str(src_path),
                ]
                if not src_info["has_audio"]:
                    cmd_cpu.extend(["-f", "lavfi", "-t", str(actual_duration), "-i", "anullsrc=channel_layout=stereo:sample_rate=48000"])

                cmd_cpu.extend([
                    "-filter_complex", filter_complex,
                    "-map", "[v]",
                ])
                if src_info["has_audio"]:
                    cmd_cpu.extend(["-map", "[a]", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"])
                else:
                    cmd_cpu.extend(["-map", "1:a", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2"])

                cmd_cpu.extend([
                    "-c:v", "libx264",
                    "-preset", "veryfast",
                    "-crf", "22",
                    "-pix_fmt", "yuv420p",
                    "-r", str(target_fps),
                    "-movflags", "+faststart",
                    str(out_path)
                ])

                res_cpu = subprocess.run(cmd_cpu, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=240)
                if res_cpu.returncode != 0:
                    raise RuntimeError(f"FFmpeg render failed (Code {res_cpu.returncode}): {res_cpu.stderr[-1000:]}")
                encode_success = True

            # Extract 9:16 Representative Thumbnail at ~40% into the short
            thumb_ts = min(actual_duration * 0.4, 2.0)
            cmd_thumb = [
                self.ffmpeg,
                "-y",
                "-ss", str(thumb_ts),
                "-i", str(out_path),
                "-vframes", "1",
                "-q:v", "2",
                str(thumb_path)
            ]
            subprocess.run(cmd_thumb, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)

            # Run FFprobe Verification on the generated file
            verification = self.verify_short_file(str(out_path), expected_duration=actual_duration)

            # Update Clip in database
            file_size = out_path.stat().st_size if out_path.exists() else 0
            clip.clip_path = str(out_path.resolve())
            clip.stream_url = f"/api/clips/{clip.id}/stream"
            clip.thumbnail_path = str(thumb_path.resolve()) if thumb_path.exists() else None
            clip.thumbnail_url = f"/api/clips/{clip.id}/thumbnail" if thumb_path.exists() else None
            clip.file_size_bytes = file_size
            clip.status = ClipStatus.GENERATED
            clip.error_message = None
            db.commit()
            db.refresh(clip)

            return {
                "clip_id": clip.id,
                "title": clip.title,
                "file_path": str(out_path.resolve()),
                "thumbnail_path": str(thumb_path.resolve()) if thumb_path.exists() else None,
                "stream_url": clip.stream_url,
                "thumbnail_url": clip.thumbnail_url,
                "resolution": "1080x1920",
                "aspect_ratio": "9:16",
                "duration": actual_duration,
                "fps": target_fps,
                "gpu_accelerated": used_gpu,
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

    def generate_shorts_batch(
        self,
        recording_id: int,
        candidate_clip_ids: Optional[List[int]] = None,
        select_top_n: Optional[int] = None,
        target_length: Optional[int] = None,
        render_mode: str = "blurred_background",
        subtitles: bool = False,
        subtitle_style: str = "vice_neon",
        use_gpu: bool = True,
        progress_cb: Optional[Callable[[float, str], None]] = None,
        cancel_event: Optional[threading.Event] = None,
    ) -> List[Dict[str, Any]]:
        """
        Batch generate up to 20 candidate clips into YouTube Shorts (1080x1920, 9:16).
        Shows real progress and error messages per clip.
        """
        db = SessionLocal()
        try:
            recording = db.query(Recording).filter(Recording.id == recording_id).first()
            if not recording:
                raise ValueError(f"Recording #{recording_id} not found.")

            # Query candidate clips
            query = db.query(CandidateClip).filter(CandidateClip.recording_id == recording_id)
            if candidate_clip_ids:
                query = query.filter(CandidateClip.id.in_(candidate_clip_ids))
            else:
                # Use selected candidates, or top ranked candidates
                selected = query.filter(CandidateClip.is_selected == True).all()
                if not selected:
                    # Select top candidates up to select_top_n or 20
                    limit_n = select_top_n or 20
                    selected = (
                        db.query(CandidateClip)
                        .filter(CandidateClip.recording_id == recording_id)
                        .order_by(CandidateClip.ai_score.desc())
                        .limit(limit_n)
                        .all()
                    )
                query_items = selected
            
            candidates = query_items if 'query_items' in locals() else query.all()
            if not candidates:
                # Automatically rank candidates on the fly if not yet ranked
                try:
                    from .clip_ranker import clip_ranker
                    clip_ranker.generate_ranked_candidates(recording_id)
                    candidates = (
                        db.query(CandidateClip)
                        .filter(CandidateClip.recording_id == recording_id)
                        .order_by(CandidateClip.ai_score.desc())
                        .limit(select_top_n or 20)
                        .all()
                    )
                except Exception as ex:
                    print(f"Auto-ranking on batch generate fallback failed: {ex}")

            if not candidates:
                raise ValueError("No candidate clips found. Please wait for video analysis or run AI Clip Ranking first.")

            # Limit to maximum 20 candidate clips per recording
            candidates = candidates[:20]
            total_count = len(candidates)

            if progress_cb:
                progress_cb(5.0, f"Starting YouTube Shorts batch generation for {total_count} candidate clips...")

            results = []
            for idx, c in enumerate(candidates, 1):
                if cancel_event and cancel_event.is_set():
                    break

                pct = round(5.0 + (idx - 1) / total_count * 90.0, 1)
                if progress_cb:
                    progress_cb(pct, f"Generating Short {idx} of {total_count}: '{c.title}' (1080x1920 9:16)...")

                dur = c.duration
                # Optional target length override
                s_time = c.start_time
                e_time = c.end_time
                t_len = target_length or c.target_length

                try:
                    existing_clip = db.query(Clip).filter(Clip.candidate_clip_id == c.id, Clip.status == ClipStatus.GENERATING).first()
                    clip_override = existing_clip.id if existing_clip else None

                    res = self.generate_single_short(
                        recording_id=recording_id,
                        start_time=s_time,
                        end_time=e_time,
                        title=c.title,
                        candidate_clip_id=c.id,
                        detected_moment_id=c.detected_moment_id,
                        target_length=t_len,
                        render_mode=render_mode,
                        subtitles=subtitles,
                        subtitle_text=c.category_label or c.title,
                        subtitle_style=subtitle_style,
                        use_gpu=use_gpu,
                        clip_id_override=clip_override,
                    )
                    c.status = "exported"
                    db.commit()
                    results.append(res)
                except Exception as clip_err:
                    print(f"Error generating short for candidate #{c.id}: {clip_err}")
                    results.append({
                        "candidate_clip_id": c.id,
                        "title": c.title,
                        "status": "failed",
                        "error": str(clip_err),
                    })

            if progress_cb:
                progress_cb(100.0, f"Completed YouTube Shorts generation! {len(results)}/{total_count} processed.")

            return results

        finally:
            db.close()

    def verify_short_file(self, file_path: str, expected_duration: float, tolerance: float = 1.0) -> Dict[str, Any]:
        """
        Run FFprobe verification on a generated YouTube Short file.
        Checks:
        - width == 1080
        - height == 1920 (9:16 aspect ratio)
        - duration within [expected_duration - tolerance, expected_duration + tolerance]
        - video codec == h264
        - audio codec == aac
        - file_size > 0
        """
        path = Path(file_path)
        if not path.is_file():
            return {
                "is_valid": False,
                "file_path": file_path,
                "error": "File does not exist on disk",
                "checks": {},
            }

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
            return {
                "is_valid": False,
                "file_path": file_path,
                "error": f"FFprobe error: {res.stderr}",
                "checks": {},
            }

        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        v_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        a_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        width = v_stream.get("width", 0) if v_stream else 0
        height = v_stream.get("height", 0) if v_stream else 0
        v_codec = v_stream.get("codec_name", "") if v_stream else ""
        a_codec = a_stream.get("codec_name", "") if a_stream else ""

        # Duration
        fmt_dur = float(data.get("format", {}).get("duration", 0.0))
        file_size = int(data.get("format", {}).get("size", 0))

        fps = 30.0
        if v_stream and "/" in v_stream.get("r_frame_rate", ""):
            try:
                num, den = map(float, v_stream["r_frame_rate"].split("/"))
                if den > 0:
                    fps = round(num / den, 2)
            except Exception:
                pass

        # Verification checks
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

shorts_generator = ShortsGenerator()
