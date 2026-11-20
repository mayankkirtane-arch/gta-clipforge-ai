import os
import json
import math
import wave
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np

from datetime import datetime
from sqlalchemy.sql import func
from scenedetect import SceneManager, open_video, ContentDetector

from ..config import settings
from ..database import SessionLocal
from ..models.recording import Recording, RecordingStatus
from ..models.analysis import RecordingAnalysis, TimelineSegment, RecordingChunk
from ..models.job import Job, JobStatus
from .video_service import get_ffprobe_path, get_ffmpeg_path

def format_timestamp(seconds: float) -> str:
    """Format seconds into HH:MM:SS or MM:SS."""
    if seconds < 0:
        seconds = 0
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"

class VideoProcessingEngine:
    """
    Professional Video Processing Engine for GTA CLIPFORGE AI.
    - Chunk-based processing designed for long recordings up to 8 hours
    - Never loads entire video into memory
    - PySceneDetect + OpenCV scene & keyframe analysis
    - Audio extraction, silence & peak detection, waveform generation
    - GPU acceleration (NVENC) with automatic CPU fallback
    - Checkpointed state for reliable recovery after interrupted processing
    """

    def __init__(self):
        self.ffprobe = get_ffprobe_path()
        self.ffmpeg = get_ffmpeg_path()

    def extract_full_metadata(self, video_path: str) -> Dict[str, Any]:
        """Extract comprehensive video & audio container metadata via FFprobe."""
        path = Path(video_path)
        if not path.is_file():
            raise FileNotFoundError(f"Video file not found: {video_path}")

        cmd = [
            self.ffprobe,
            "-v", "error",
            "-show_entries", "stream=width,height,r_frame_rate,duration,codec_name,codec_type,channels,sample_rate,pix_fmt",
            "-show_entries", "format=duration,size,bit_rate",
            "-of", "json",
            str(path)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
        if res.returncode != 0:
            raise ValueError(f"FFprobe metadata extraction failed: {res.stderr}")

        data = json.loads(res.stdout)
        streams = data.get("streams", [])
        format_info = data.get("format", {})

        video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
        audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

        if not video_stream:
            raise ValueError("No video stream found in container.")

        width = video_stream.get("width")
        height = video_stream.get("height")
        vcodec = video_stream.get("codec_name")
        pix_fmt = video_stream.get("pix_fmt")

        # Frame rate
        fps = 30.0
        r_frame_rate = video_stream.get("r_frame_rate", "30/1")
        if "/" in r_frame_rate:
            try:
                num, den = map(float, r_frame_rate.split("/"))
                if den > 0:
                    fps = round(num / den, 2)
            except Exception:
                pass

        # Duration
        duration = 0.0
        if "duration" in video_stream and video_stream["duration"]:
            try:
                duration = float(video_stream["duration"])
            except Exception:
                pass
        if duration == 0.0 and "duration" in format_info and format_info["duration"]:
            try:
                duration = float(format_info["duration"])
            except Exception:
                pass

        file_size = int(format_info.get("size", path.stat().st_size))
        bitrate = int(format_info.get("bit_rate", 0)) if format_info.get("bit_rate") else None

        # Audio stream info
        acodec = audio_stream.get("codec_name") if audio_stream else None
        channels = int(audio_stream.get("channels", 0)) if audio_stream else None
        sample_rate = int(audio_stream.get("sample_rate", 0)) if audio_stream else None

        return {
            "duration_seconds": round(duration, 2),
            "width": width,
            "height": height,
            "resolution": f"{width}x{height}" if width and height else None,
            "fps": fps,
            "video_codec": vcodec,
            "audio_codec": acodec,
            "channels": channels,
            "sample_rate": sample_rate,
            "pix_fmt": pix_fmt,
            "file_size_bytes": file_size,
            "bitrate": bitrate,
        }

    def extract_audio(self, video_path: str, output_audio_path: str) -> Optional[str]:
        """
        Extract audio to 16kHz mono 16-bit PCM WAV without loading video into RAM.
        Streams demuxer packets directly to disk.
        """
        out_p = Path(output_audio_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        if out_p.exists() and out_p.stat().st_size > 1000:
            return str(out_p.resolve())

        cmd = [
            self.ffmpeg,
            "-y",
            "-i", str(video_path),
            "-vn",
            "-acodec", "pcm_s16le",
            "-ar", "16000",
            "-ac", "1",
            str(out_p)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=180)
        if res.returncode != 0 or not out_p.exists():
            return None
        return str(out_p.resolve())

    def generate_thumbnail(self, video_path: str, output_path: str, timestamp_sec: float = 1.0) -> Optional[str]:
        """Generate high-quality representative poster thumbnail."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg,
            "-y",
            "-ss", str(timestamp_sec),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            "-vf", "scale=640:-1",
            str(out_p)
        ]
        res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=15)
        if res.returncode == 0 and out_p.exists():
            return str(out_p.resolve())

        # Fallback to OpenCV
        try:
            cap = cv2.VideoCapture(video_path)
            cap.set(cv2.CAP_PROP_POS_MSEC, timestamp_sec * 1000.0)
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                h, w = frame.shape[:2]
                new_w = 640
                new_h = int(h * (640 / w))
                resized = cv2.resize(frame, (new_w, new_h), interpolation=cv2.INTER_AREA)
                cv2.imwrite(str(out_p), resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
                return str(out_p.resolve())
        except Exception:
            pass
        return None

    def generate_preview_proxy(self, video_path: str, output_proxy_path: str, use_gpu: bool = True) -> Tuple[Optional[str], bool]:
        """
        Generate 720p/480p preview proxy.
        Attempts GPU acceleration (NVENC) with automatic CPU fallback.
        """
        out_p = Path(output_proxy_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        if out_p.exists() and out_p.stat().st_size > 10000:
            return str(out_p.resolve()), use_gpu

        gpu_success = False
        if use_gpu:
            cmd_gpu = [
                self.ffmpeg,
                "-y",
                "-i", str(video_path),
                "-vf", "scale=-2:720",
                "-c:v", "h264_nvenc",
                "-preset", "p4",
                "-b:v", "1500k",
                "-c:a", "aac",
                "-b:a", "128k",
                "-movflags", "+faststart",
                str(out_p)
            ]
            res_gpu = subprocess.run(cmd_gpu, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
            if res_gpu.returncode == 0 and out_p.exists() and out_p.stat().st_size > 1000:
                gpu_success = True
                return str(out_p.resolve()), True

        # CPU Fallback
        cmd_cpu = [
            self.ffmpeg,
            "-y",
            "-i", str(video_path),
            "-vf", "scale=-2:720",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "28",
            "-c:a", "aac",
            "-b:a", "128k",
            "-movflags", "+faststart",
            str(out_p)
        ]
        res_cpu = subprocess.run(cmd_cpu, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=300)
        if res_cpu.returncode == 0 and out_p.exists():
            return str(out_p.resolve()), False

        return None, False

    def extract_keyframes_for_chunk(
        self,
        video_path: str,
        chunk_start: float,
        chunk_end: float,
        interval_sec: float,
        output_dir: Path
    ) -> List[Dict[str, Any]]:
        """
        Extract keyframes at configurable intervals for the chunk.
        Uses OpenCV with fast timestamp seeks.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        keyframes = []
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return keyframes

        try:
            curr_time = chunk_start
            while curr_time <= chunk_end:
                cap.set(cv2.CAP_PROP_POS_MSEC, curr_time * 1000.0)
                ret, frame = cap.read()
                if not ret or frame is None:
                    curr_time += interval_sec
                    continue

                # Resize to standard timeline thumbnail dimensions (480x270)
                h, w = frame.shape[:2]
                target_w = 480
                target_h = int(h * (480 / w))
                resized = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)

                # Luminance for black frame detection
                gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                mean_lum = float(np.mean(gray))
                is_black = mean_lum < 15.0

                time_ms = int(curr_time * 1000)
                keyframe_filename = f"kf_{time_ms:09d}.jpg"
                keyframe_file = output_dir / keyframe_filename
                cv2.imwrite(str(keyframe_file), resized, [cv2.IMWRITE_JPEG_QUALITY, 80])

                keyframes.append({
                    "timestamp": round(curr_time, 2),
                    "timestamp_formatted": format_timestamp(curr_time),
                    "keyframe_path": str(keyframe_file.resolve()),
                    "keyframe_filename": keyframe_filename,
                    "is_black_frame": is_black,
                    "mean_luminance": mean_lum,
                })
                curr_time += interval_sec

        finally:
            cap.release()

        return keyframes

    def detect_scenes_chunk(
        self,
        video_path: str,
        chunk_start: float,
        chunk_end: float,
        threshold: float = 27.0
    ) -> List[Dict[str, Any]]:
        """
        Detect scene cuts and transitions in a chunk using PySceneDetect.
        Memory safe: only decodes the designated chunk slice.
        Note: Float is explicitly required by PySceneDetect to seek by seconds instead of frame count.
        """
        scenes = []
        chunk_start = float(chunk_start)
        chunk_end = float(chunk_end)
        chunk_duration = float(chunk_end - chunk_start)
        if chunk_duration <= 0.1:
            return scenes

        try:
            video = open_video(video_path)
            # Seek to chunk start (seconds)
            video.seek(chunk_start)
            scene_manager = SceneManager()
            scene_manager.add_detector(ContentDetector(threshold=threshold))
            scene_manager.detect_scenes(video=video, duration=chunk_duration)
            scene_list = scene_manager.get_scene_list()

            for idx, (start_tc, end_tc) in enumerate(scene_list, 1):
                start_sec = round(float(start_tc.seconds), 2)
                end_sec = round(float(end_tc.seconds), 2)
                scenes.append({
                    "scene_number": idx,
                    "start_time": start_sec,
                    "end_time": end_sec,
                    "duration": round(end_sec - start_sec, 2),
                })
        except Exception as e:
            print(f"[SceneDetect Warning] Chunk {chunk_start}-{chunk_end}s fallback: {e}")

        return scenes

    def analyze_audio_chunk(
        self,
        audio_path: str,
        chunk_start: float,
        chunk_end: float,
        silence_thresh_db: float = -35.0,
        peak_percentile: float = 85.0
    ) -> Tuple[List[Dict[str, Any]], List[float]]:
        """
        Analyze audio slice without loading whole recording into memory.
        Calculates RMS, dB peaks, silence, and normalized waveform samples.
        """
        timeline_audio_pts = []
        waveform_samples = []

        if not audio_path or not os.path.isfile(audio_path):
            return timeline_audio_pts, waveform_samples

        try:
            with wave.open(audio_path, "rb") as wf:
                sample_rate = wf.getframerate()
                n_channels = wf.getnchannels()
                sampwidth = wf.getsampwidth()
                total_frames = wf.getnframes()

                start_frame = int(chunk_start * sample_rate)
                end_frame = min(int(chunk_end * sample_rate), total_frames)

                if start_frame >= total_frames or start_frame >= end_frame:
                    return timeline_audio_pts, waveform_samples

                wf.setpos(start_frame)
                frames_to_read = end_frame - start_frame
                raw_bytes = wf.readframes(frames_to_read)

            if not raw_bytes:
                return timeline_audio_pts, waveform_samples

            # Convert to numpy array
            samples = np.frombuffer(raw_bytes, dtype=np.int16)
            if samples.size == 0:
                return timeline_audio_pts, waveform_samples

            # Sample in 1.0 second windows
            window_size = sample_rate
            n_windows = max(1, int(len(samples) / window_size))
            dbs = []

            for i in range(n_windows):
                w_start = i * window_size
                w_end = min((i + 1) * window_size, len(samples))
                win_samples = samples[w_start:w_end]
                if len(win_samples) == 0:
                    continue

                rms = float(np.sqrt(np.mean(win_samples.astype(np.float32) ** 2)))
                db = float(20 * np.log10(rms / 32768.0 + 1e-6))
                dbs.append(db)

                # Normalized waveform point (0.0 to 1.0)
                norm_amp = float(np.clip((db + 60.0) / 60.0, 0.0, 1.0))
                waveform_samples.append(round(norm_amp, 3))

            if not dbs:
                return timeline_audio_pts, waveform_samples

            # Compute dynamic audio peak threshold based on percentile
            threshold_db = float(np.percentile(dbs, peak_percentile))
            threshold_db = max(threshold_db, -25.0)  # Absolute sanity minimum

            for idx, db_val in enumerate(dbs):
                t_sec = round(chunk_start + idx * 1.0, 2)
                is_peak = db_val >= threshold_db
                is_silence = db_val <= silence_thresh_db
                timeline_audio_pts.append({
                    "timestamp": t_sec,
                    "db": round(db_val, 1),
                    "is_peak": is_peak,
                    "is_silence": is_silence,
                })

        except Exception as e:
            print(f"[Audio Chunk Error] {e}")

        return timeline_audio_pts, waveform_samples

    def process_recording(
        self,
        recording_id: int,
        progress_callback=None,
        cancel_event=None,
        chunk_duration_sec: Optional[int] = None,
        keyframe_interval_sec: Optional[float] = None,
        gpu_acceleration: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Master Video Processing Pipeline:
        1. Extract full metadata
        2. Generate poster thumbnail
        3. Extract audio stream to disk (zero video memory footprint)
        4. Generate low-resolution preview proxy with GPU/CPU fallback
        5. Chunk-based analysis loop with checkpoint recovery
        6. Timeline segments synthesis and SQLite persistence
        """
        db = SessionLocal()
        try:
            rec = db.query(Recording).filter(Recording.id == recording_id).first()
            if not rec:
                raise ValueError(f"Recording ID {recording_id} not found.")

            video_path = rec.file_path
            if not os.path.isfile(video_path):
                raise FileNotFoundError(f"Video file missing on disk: {video_path}")

            # Resolve settings
            chunk_duration = chunk_duration_sec or settings.CHUNK_DURATION_SEC
            keyframe_interval = keyframe_interval_sec or settings.KEYFRAME_INTERVAL_SEC
            use_gpu = gpu_acceleration if gpu_acceleration is not None else settings.GPU_ACCELERATION

            # Initialize or retrieve RecordingAnalysis
            analysis = db.query(RecordingAnalysis).filter(RecordingAnalysis.recording_id == recording_id).first()
            if not analysis:
                analysis = RecordingAnalysis(
                    recording_id=recording_id,
                    status="processing",
                    progress=5.0,
                    chunk_duration_sec=chunk_duration,
                    gpu_accelerated=use_gpu,
                )
                db.add(analysis)
                db.commit()
                db.refresh(analysis)
            else:
                analysis.status = "processing"
                analysis.error = None
                db.commit()

            # 1. Full Metadata
            if progress_callback:
                progress_callback(8.0, "Extracting full container & stream metadata...")
            meta = self.extract_full_metadata(video_path)
            duration = meta["duration_seconds"]

            # Update recording table with verified metadata
            rec.duration_seconds = duration
            rec.resolution = meta["resolution"]
            rec.fps = meta["fps"]
            rec.video_codec = meta["video_codec"]
            rec.audio_codec = meta["audio_codec"]
            rec.bitrate = meta["bitrate"]
            db.commit()

            # 2. Thumbnail
            if progress_callback:
                progress_callback(12.0, "Generating poster thumbnail...")
            thumb_path = Path(settings.THUMBNAILS_DIR) / f"thumb_rec_{recording_id}.jpg"
            thumb_file = self.generate_thumbnail(video_path, str(thumb_path), timestamp_sec=min(2.0, duration * 0.1))
            if thumb_file:
                analysis.thumbnail_path = thumb_file
                db.commit()

            # 3. Audio Extraction (Streaming demuxing - no video in RAM)
            if progress_callback:
                progress_callback(18.0, "Demuxing audio stream directly to disk...")
            audio_path = Path(settings.AUDIO_DIR) / f"audio_rec_{recording_id}.wav"
            extracted_audio = self.extract_audio(video_path, str(audio_path))
            if extracted_audio:
                analysis.audio_path = extracted_audio
                db.commit()

            # 4. Preview Proxy Generation (GPU NVENC with CPU fallback)
            if progress_callback:
                progress_callback(25.0, "Transcoding 720p preview proxy (GPU/CPU)...")
            proxy_path = Path(settings.PROXIES_DIR) / f"proxy_rec_{recording_id}.mp4"
            proxy_file, used_gpu = self.generate_preview_proxy(video_path, str(proxy_path), use_gpu=use_gpu)
            if proxy_file:
                analysis.proxy_path = proxy_file
                analysis.gpu_accelerated = used_gpu
                db.commit()

            # 5. Calculate Chunks for long recordings (e.g. up to 8 hours)
            n_chunks = max(1, math.ceil(duration / chunk_duration))
            analysis.total_chunks = n_chunks
            db.commit()

            keyframe_dir = Path(settings.KEYFRAMES_DIR) / f"rec_{recording_id}"
            keyframe_dir.mkdir(parents=True, exist_ok=True)

            existing_waveform = []
            if analysis.waveform_data:
                try:
                    existing_waveform = json.loads(analysis.waveform_data)
                except Exception:
                    pass

            existing_scenes = []
            if analysis.scenes_data:
                try:
                    existing_scenes = json.loads(analysis.scenes_data)
                except Exception:
                    pass

            all_waveform: List[float] = existing_waveform.copy()
            all_scenes_summary: List[Dict[str, Any]] = existing_scenes.copy()
            all_black_frames_summary: List[Dict[str, Any]] = []
            all_silence_summary: List[Dict[str, Any]] = []
            current_scene_number = len(all_scenes_summary) + 1

            # 6. Chunk-based Processing Loop with Checkpoint Recovery
            base_progress = 30.0
            chunk_progress_weight = 65.0 / n_chunks

            for c_idx in range(n_chunks):
                if cancel_event and cancel_event.is_set():
                    analysis.status = "cancelled"
                    db.commit()
                    return {"status": "cancelled"}

                c_start = c_idx * chunk_duration
                c_end = min((c_idx + 1) * chunk_duration, duration)

                # Check SQLite Checkpoint for recovery
                chunk_record = db.query(RecordingChunk).filter(
                    RecordingChunk.recording_id == recording_id,
                    RecordingChunk.chunk_index == c_idx
                ).first()

                if chunk_record and chunk_record.status == "completed":
                    print(f"⏩ [Recovery Checkpoint] Chunk {c_idx+1}/{n_chunks} already completed. Resuming...")
                    continue

                if not chunk_record:
                    chunk_record = RecordingChunk(
                        recording_id=recording_id,
                        chunk_index=c_idx,
                        start_time=c_start,
                        end_time=c_end,
                        status="processing"
                    )
                    db.add(chunk_record)
                    db.commit()
                else:
                    chunk_record.status = "processing"
                    db.commit()

                analysis.current_chunk = c_idx + 1
                curr_pct = round(base_progress + (c_idx * chunk_progress_weight), 1)
                if progress_callback:
                    progress_callback(curr_pct, f"Processing chunk {c_idx+1}/{n_chunks} ({format_timestamp(c_start)} - {format_timestamp(c_end)})...")

                # (a) Keyframes
                keyframes = self.extract_keyframes_for_chunk(
                    video_path, c_start, c_end, keyframe_interval, keyframe_dir
                )

                # (b) Scene Cuts
                scenes = self.detect_scenes_chunk(
                    video_path, c_start, c_end, threshold=settings.SCENE_THRESHOLD
                )
                print(f"[Debug Engine] Chunk {c_idx+1} ({c_start}-{c_end}s) detected {len(scenes)} scenes: {scenes}")
                for sc in scenes:
                    sc["global_scene_number"] = current_scene_number
                    current_scene_number += 1
                    all_scenes_summary.append(sc)

                # (c) Audio Peaks & Waveform
                audio_pts, chunk_wave = self.analyze_audio_chunk(
                    str(audio_path), c_start, c_end,
                    silence_thresh_db=settings.SILENCE_THRESHOLD_DB,
                    peak_percentile=settings.AUDIO_PEAK_PERCENTILE
                )
                all_waveform.extend(chunk_wave)

                # (d) Synthesize Timeline Segments for this Chunk
                audio_map = {pt["timestamp"]: pt for pt in audio_pts}
                scene_cut_times = {sc["start_time"] for sc in scenes}

                for kf in keyframes:
                    t = kf["timestamp"]
                    # Match nearest audio point
                    matched_audio = audio_map.get(round(t), None)
                    peak_db = matched_audio["db"] if matched_audio else -40.0
                    is_peak = matched_audio["is_peak"] if matched_audio else False
                    is_silence = matched_audio["is_silence"] if matched_audio else False
                    is_black = kf["is_black_frame"]

                    # Check if near a scene cut
                    is_cut = any(abs(t - cut_t) <= (keyframe_interval / 2.0) for cut_t in scene_cut_times)

                    # Compute Excitement Score (0 - 100)
                    norm_energy = min(40.0, max(0.0, (peak_db + 50.0) * 0.8))
                    score = norm_energy
                    if is_peak:
                        score += 30.0
                    if is_cut:
                        score += 20.0
                    if not is_black and not is_silence:
                        score += 10.0
                    excitement_score = min(100.0, round(score, 1))

                    segment = TimelineSegment(
                        recording_id=recording_id,
                        timestamp=t,
                        timestamp_formatted=kf["timestamp_formatted"],
                        scene_number=current_scene_number - 1 if current_scene_number > 1 else 1,
                        keyframe_path=kf["keyframe_path"],
                        audio_peak_db=peak_db,
                        is_audio_peak=is_peak,
                        is_scene_change=is_cut,
                        is_black_frame=is_black,
                        is_silence=is_silence,
                        excitement_score=excitement_score,
                        chunk_index=c_idx,
                    )
                    db.add(segment)

                # Commit Checkpoint for this chunk
                chunk_record.status = "completed"
                chunk_record.completed_at = func.now()
                db.commit()

            # 7. Finalize Analysis Summary
            if progress_callback:
                progress_callback(96.0, "Consolidating timeline heatmap and excitement scoring...")

            total_kf = db.query(TimelineSegment).filter(TimelineSegment.recording_id == recording_id).count()
            total_sc = len(all_scenes_summary)
            peaks_count = db.query(TimelineSegment).filter(
                TimelineSegment.recording_id == recording_id,
                TimelineSegment.is_audio_peak == True
            ).count()
            black_count = db.query(TimelineSegment).filter(
                TimelineSegment.recording_id == recording_id,
                TimelineSegment.is_black_frame == True
            ).count()
            silence_count = db.query(TimelineSegment).filter(
                TimelineSegment.recording_id == recording_id,
                TimelineSegment.is_silence == True
            ).count()

            # Downsample waveform for fast rendering in browser if long
            if len(all_waveform) > 300:
                step = math.ceil(len(all_waveform) / 300)
                display_waveform = [round(float(np.mean(all_waveform[i:i+step])), 3) for i in range(0, len(all_waveform), step)]
            else:
                display_waveform = all_waveform

            analysis.status = "completed"
            analysis.progress = 100.0
            analysis.total_scenes = total_sc
            analysis.total_keyframes = total_kf
            analysis.audio_peaks_count = peaks_count
            analysis.black_frames_count = black_count
            analysis.silence_count = silence_count
            analysis.waveform_data = json.dumps(display_waveform)
            analysis.scenes_data = json.dumps(all_scenes_summary)

            rec.status = RecordingStatus.ANALYZED
            db.commit()

            if progress_callback:
                progress_callback(100.0, "Video processing and timeline analysis complete!")

            return {
                "status": "completed",
                "recording_id": recording_id,
                "total_scenes": total_sc,
                "total_keyframes": total_kf,
                "audio_peaks_count": peaks_count,
                "proxy_path": analysis.proxy_path,
                "thumbnail_path": analysis.thumbnail_path,
            }

        except Exception as e:
            db.rollback()
            try:
                analysis = db.query(RecordingAnalysis).filter(RecordingAnalysis.recording_id == recording_id).first()
                if analysis:
                    analysis.status = "failed"
                    analysis.error = str(e)
                    db.commit()
            except Exception:
                pass
            raise e
        finally:
            db.close()

video_engine = VideoProcessingEngine()
