import json
import os
import shutil
import subprocess
import time
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from ..config import settings

def get_ffprobe_path() -> str:
    """Resolve ffprobe executable path."""
    candidates = [
        settings.FFPROBE_PATH,
        "D:/GTA_CLIPFORGE_AI/bin/ffprobe.exe",
        "C:/Users/91810/AppData/Local/Python/bin/ffprobe.exe",
    ]
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
            
    which_probe = shutil.which("ffprobe")
    if which_probe:
        return which_probe
        
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
        which_probe = shutil.which("ffprobe")
        if which_probe:
            return which_probe
    except Exception:
        pass
        
    return "ffprobe"

def get_ffmpeg_path() -> str:
    """Resolve ffmpeg executable path."""
    candidates = [
        settings.FFMPEG_PATH,
        "D:/GTA_CLIPFORGE_AI/bin/ffmpeg.exe",
        "C:/Users/91810/AppData/Local/Python/bin/ffmpeg.exe",
    ]
    for c in candidates:
        if c and os.path.isfile(c) and os.access(c, os.X_OK):
            return c
            
    which_ffmpeg = shutil.which("ffmpeg")
    if which_ffmpeg:
        return which_ffmpeg
        
    try:
        import static_ffmpeg
        static_ffmpeg.add_paths()
        which_ffmpeg = shutil.which("ffmpeg")
        if which_ffmpeg:
            return which_ffmpeg
    except Exception:
        pass
        
    return "ffmpeg"

def wait_until_file_ready(file_path: str, timeout_seconds: int = 60, check_interval: float = 1.0) -> bool:
    """
    Wait until a file has finished copying or writing.
    Checks that the file exists, has non-zero size, does not change size across consecutive intervals,
    and can be opened with read/write access to ensure the writer has completed.
    """
    path = Path(file_path)
    start_time = time.time()
    last_size = -1
    stable_count = 0

    while time.time() - start_time < timeout_seconds:
        if not path.exists():
            time.sleep(check_interval)
            continue

        try:
            current_size = path.stat().st_size
            if current_size > 0 and current_size == last_size:
                stable_count += 1
                if stable_count >= 2:
                    # Attempt to open file to ensure writer has released exclusive lock
                    try:
                        with open(path, "rb+") as f:
                            pass
                        return True
                    except (PermissionError, OSError):
                        pass
            else:
                stable_count = 0
            last_size = current_size
        except (PermissionError, OSError):
            stable_count = 0

        time.sleep(check_interval)

    # Final fallback check
    try:
        if path.exists() and path.stat().st_size > 0:
            with open(path, "rb") as f:
                f.read(1024)
            return True
    except Exception:
        pass

    return False

def calculate_file_hash(file_path: str, chunk_size: int = 4 * 1024 * 1024) -> str:
    """
    Calculate SHA-256 hash using streaming chunks to handle long 1-8 hour videos (up to 100GB)
    without high memory usage.
    """
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()

def validate_video(file_path: str) -> Dict[str, Any]:
    """
    Validate video integrity and extract metadata using FFprobe.
    Supports MP4, MKV, MOV, WebM and long 1-8 hour recordings.
    """
    path = Path(file_path)
    if not path.is_file():
        raise ValueError(f"File does not exist: {file_path}")

    ext = path.suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        raise ValueError(f"Unsupported file extension: {ext}. Allowed: {settings.ALLOWED_EXTENSIONS}")

    file_size_bytes = path.stat().st_size
    if file_size_bytes == 0:
        raise ValueError("Video file is empty (0 bytes).")

    ffprobe = get_ffprobe_path()

    cmd = [
        ffprobe,
        "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height,r_frame_rate,duration,codec_name",
        "-show_entries", "format=duration,size,bit_rate",
        "-of", "json",
        str(path)
    ]

    try:
        result = subprocess.run(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=30,
            check=False
        )
    except subprocess.TimeoutExpired:
        raise ValueError("FFprobe timed out while analyzing video.")
    except Exception as e:
        raise ValueError(f"Failed to execute FFprobe: {str(e)}")

    if result.returncode != 0:
        err = result.stderr.strip() or "Invalid video format or corrupted file"
        raise ValueError(f"FFprobe validation failed: {err}")

    try:
        data = json.loads(result.stdout)
    except Exception as e:
        raise ValueError(f"Failed to parse FFprobe output: {str(e)}")

    streams = data.get("streams", [])
    format_info = data.get("format", {})

    if not streams:
        raise ValueError("No video stream found in the file.")

    video_stream = streams[0]
    width = video_stream.get("width")
    height = video_stream.get("height")
    codec_name = video_stream.get("codec_name")
    
    # Calculate FPS
    fps = None
    r_frame_rate = video_stream.get("r_frame_rate", "")
    if "/" in r_frame_rate:
        try:
            num, den = map(float, r_frame_rate.split("/"))
            if den > 0:
                fps = round(num / den, 2)
        except Exception:
            fps = None

    # Calculate Duration
    duration = None
    if "duration" in video_stream and video_stream["duration"]:
        try:
            duration = round(float(video_stream["duration"]), 2)
        except Exception:
            pass

    if duration is None and "duration" in format_info and format_info["duration"]:
        try:
            duration = round(float(format_info["duration"]), 2)
        except Exception:
            pass

    # Bitrate
    bitrate = None
    if "bit_rate" in format_info and format_info["bit_rate"]:
        try:
            bitrate = int(format_info["bit_rate"])
        except Exception:
            pass

    resolution = f"{width}x{height}" if width and height else None

    return {
        "valid": True,
        "duration_seconds": duration,
        "resolution": resolution,
        "fps": fps,
        "width": width,
        "height": height,
        "video_codec": codec_name,
        "file_size_bytes": file_size_bytes,
        "bitrate": bitrate,
    }
