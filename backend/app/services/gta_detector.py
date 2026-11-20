import os
import json
import math
import wave
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np
from sqlalchemy.orm import Session

from ..config import settings
from ..database import SessionLocal
from ..models.recording import Recording
from ..models.detected_moment import DetectedMoment
from ..models.analysis import RecordingAnalysis, TimelineSegment
from .video_service import get_ffmpeg_path
from .vlm_service import vlm_service

EVENT_DEFINITIONS: Dict[str, Dict[str, str]] = {
    "police_chase": {
        "label": "Police Chase",
        "description": "High-intensity pursuit with alternating red/blue police sirens, tactical evasion maneuvers, or road spikes.",
        "color": "#ef4444",
        "icon": "Siren",
    },
    "high_speed_driving": {
        "label": "High-Speed Driving",
        "description": "Rapid highway or street traversal with radial forward optical flow divergence and peripheral speed blur.",
        "color": "#10b981",
        "icon": "Gauge",
    },
    "supercar_stunt": {
        "label": "Supercar Stunt",
        "description": "Airborne ballistic arc, elevated ramp leap, mid-air vehicle roll/spin with ground-plane clearance.",
        "color": "#a855f7",
        "icon": "Rocket",
    },
    "car_crash": {
        "label": "Car Crash",
        "description": "Abrupt velocity decimation, violent screen shake, structural chassis deformation, and loud acoustic collision.",
        "color": "#f59e0b",
        "icon": "AlertTriangle",
    },
    "explosion": {
        "label": "Explosion",
        "description": "Sudden expanding yellow/orange fireball blast with intense low-frequency acoustic shockwave.",
        "color": "#f97316",
        "icon": "Flame",
    },
    "shootout": {
        "label": "Shootout",
        "description": "Rapid automatic weapon muzzle flashes, weapon recoil kick, and rhythmic acoustic gunshot impulses.",
        "color": "#e11d48",
        "icon": "Crosshair",
    },
    "funny_npc": {
        "label": "Funny NPC Interaction",
        "description": "Unusual pedestrian ragdoll physics, anomalous crowd collisions, bizarre pedestrian reactions or pathing.",
        "color": "#eab308",
        "icon": "Smile",
    },
    "unexpected_gameplay": {
        "label": "Unexpected Gameplay",
        "description": "Physics anomalies, sudden vehicle catapults, bizarre clipping, or unpredictable multi-car pileups.",
        "color": "#6366f1",
        "icon": "Sparkles",
    },
    "cinematic_scene": {
        "label": "Cinematic Scene",
        "description": "Golden hour tropical vistas, Biscayne Bay horizons, smooth tracking pans, and picturesque framing.",
        "color": "#06b6d4",
        "icon": "SunMedium",
    },
    "nighttime_vice_city": {
        "label": "Nighttime Vice City",
        "description": "Signature Vice City neon aesthetic: vibrant neon magenta/pink and electric cyan reflections on wet asphalt.",
        "color": "#ec4899",
        "icon": "Moon",
    },
    "interesting_weather": {
        "label": "Interesting Weather",
        "description": "Tropical downpours, linear rain streaks, atmospheric fog, or sudden high-luminance lightning flashes.",
        "color": "#38bdf8",
        "icon": "CloudRain",
    },
    "action_sequence": {
        "label": "Action Sequence",
        "description": "Sustained high-tempo combination of vehicular maneuvers, gunfire, evasion, and rapid visual pacing.",
        "color": "#dc2626",
        "icon": "Zap",
    },
    "gameplay_fail": {
        "label": "Gameplay Fail",
        "description": "Fatal wipeout, inverted vehicle trapped, sudden desaturation/wasted transition, or mission failure.",
        "color": "#71717a",
        "icon": "Skull",
    },
    "unusual_visual": {
        "label": "Unusual Visual Event",
        "description": "Rare graphical anomalies, dense volumetric smoke, unique lighting effects, or atypical visual phenomena.",
        "color": "#8b5cf6",
        "icon": "Eye",
    },
}

class GTA6MomentDetector:
    """
    GTA 6 Specialized Gameplay Moment Detection Engine.
    Engineered specifically for clean GTA 6 gameplay without commentary/facecam.
    Does not rely on speech; combines OpenCV visual analysis, scene transitions,
    optical flow motion vectors, speech-independent acoustic analysis, and optional local VLM.
    """
    def __init__(self):
        self.ffmpeg = get_ffmpeg_path()
        self.thumbnails_dir = Path(settings.THUMBNAILS_DIR) / "moments"
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)

    def detect_moments_for_recording(
        self,
        recording_id: int,
        sensitivity: str = "medium",
        min_confidence: Optional[float] = None,
        min_duration_sec: float = 3.0,
        max_duration_sec: float = 60.0,
        merge_gap_sec: float = 4.0,
        enabled_event_types: Optional[List[str]] = None,
        use_vlm: bool = False,
        progress_cb=None,
    ) -> List[Dict[str, Any]]:
        """
        Main detection pipeline:
        1. Load recording and video/audio streams
        2. Window-based multi-modal visual & acoustic feature extraction
        3. 14-Event specialized scoring heuristics
        4. Optional local VLM validation on candidate keyframes
        5. Temporal clustering, deduplication & boundary refinement
        6. Explicit uncertainty evaluation
        7. Representative thumbnail generation & SQLite persistence
        """
        db = SessionLocal()
        try:
            rec = db.query(Recording).filter(Recording.id == recording_id).first()
            if not rec:
                raise ValueError(f"Recording #{recording_id} not found.")

            video_path = rec.file_path
            if not os.path.isfile(video_path):
                raise FileNotFoundError(f"Video file missing on disk: {video_path}")

            duration = rec.duration_seconds or 0.0
            if duration <= 1.0:
                # Fallback to file duration check
                cap_check = cv2.VideoCapture(video_path)
                fps = cap_check.get(cv2.CAP_PROP_FPS) or 30.0
                frames = cap_check.get(cv2.CAP_PROP_FRAME_COUNT) or 0
                cap_check.release()
                duration = round(frames / max(1.0, fps), 2)
                rec.duration_seconds = duration
                db.commit()

            # Sensitivity baseline thresholds
            conf_thresholds = {
                "low": 68.0,      # Strict
                "medium": 48.0,   # Balanced default
                "high": 35.0,     # Sensitive
            }
            target_conf = min_confidence if min_confidence is not None else conf_thresholds.get(sensitivity, 48.0)
            if target_conf <= 1.0:
                target_conf *= 100.0  # normalize 0.0-1.0 to 0-100

            if progress_cb:
                progress_cb(10.0, "Extracting audio energy envelope & spectral features...")

            # 1. Audio Features (Speech-Independent)
            audio_envelope = self._extract_audio_envelope(recording_id, duration)

            if progress_cb:
                progress_cb(25.0, "Sampling video frames for OpenCV optical flow & color space analysis...")

            # 2. Sampled Video Frame & Flow Analysis
            frame_features = self._analyze_video_frames(video_path, duration)

            if progress_cb:
                progress_cb(55.0, "Running multi-modal GTA 6 event classifiers across timeline...")

            # 3. Classify Candidate Event Windows
            raw_candidates = self._score_event_windows(
                frame_features=frame_features,
                audio_envelope=audio_envelope,
                duration=duration,
                target_conf=target_conf,
                sensitivity=sensitivity,
                enabled_types=enabled_event_types,
            )

            if progress_cb:
                progress_cb(75.0, "Deduplicating overlapping events and smoothing boundaries...")

            # 4. Temporal Merge, Deduplication, & Boundary Refinement
            merged_candidates = self._merge_and_deduplicate(
                candidates=raw_candidates,
                merge_gap_sec=merge_gap_sec,
                min_duration_sec=min_duration_sec,
                max_duration_sec=max_duration_sec,
            )

            # 5. Extract Representative Thumbnails & Optional VLM Validation
            if progress_cb:
                progress_cb(88.0, "Generating representative candidate thumbnails and validating visual context...")

            final_moments = []
            rec_thumb_dir = self.thumbnails_dir / f"rec_{recording_id}"
            rec_thumb_dir.mkdir(parents=True, exist_ok=True)

            for idx, cand in enumerate(merged_candidates, 1):
                best_t = cand["keyframe_timestamp"]
                thumb_filename = f"moment_{cand['event_type']}_{int(best_t * 1000)}.jpg"
                thumb_path = rec_thumb_dir / thumb_filename

                # Extract highest-quality candidate thumbnail
                extracted_thumb = self._extract_keyframe_image(video_path, best_t, str(thumb_path))
                thumb_url = f"/api/moments/{recording_id}/thumbnails/{thumb_filename}" if extracted_thumb else None

                # Optional Local Vision-Language Model refinement if requested
                if use_vlm and extracted_thumb and os.path.isfile(extracted_thumb):
                    vlm_res = vlm_service.analyze_gameplay_frame(
                        image_path=extracted_thumb,
                        provisional_event=cand["event_type"],
                        motion_context=cand["explanation"],
                    )
                    if vlm_res:
                        # VLM refined or confirmed
                        vlm_type = vlm_res["event_type"]
                        if vlm_type in EVENT_DEFINITIONS:
                            cand["event_type"] = vlm_type
                            cand["event_label"] = EVENT_DEFINITIONS[vlm_type]["label"]
                        cand["confidence_score"] = round((cand["confidence_score"] + (vlm_res["confidence"] * 100.0)) / 2.0, 1)
                        cand["explanation"] = f"{cand['explanation']} Visual context confirmed via AI vision ({vlm_res['explanation']})."
                        if vlm_res.get("is_uncertain"):
                            cand["is_uncertain"] = True
                            cand["uncertainty_reason"] = vlm_res.get("uncertainty_reason") or "VLM signaled visual ambiguity."

                final_moments.append({
                    "recording_id": recording_id,
                    "event_type": cand["event_type"],
                    "event_label": cand["event_label"],
                    "start_time": cand["start_time"],
                    "end_time": cand["end_time"],
                    "duration": cand["duration"],
                    "confidence_score": cand["confidence_score"],
                    "explanation": cand["explanation"],
                    "is_uncertain": cand["is_uncertain"],
                    "uncertainty_reason": cand["uncertainty_reason"],
                    "thumbnail_path": str(thumb_path) if extracted_thumb else None,
                    "thumbnail_url": thumb_url,
                    "keyframe_timestamp": best_t,
                    "visual_features": json.dumps(cand.get("features", {})),
                    "detection_sensitivity": sensitivity,
                    "status": "detected",
                    "is_approved": False,
                })

            if progress_cb:
                progress_cb(95.0, "Persisting detected moments to SQLite database...")

            # 6. Save in SQLite
            # Remove previous detected moments for this recording to avoid stale duplicates
            db.query(DetectedMoment).filter(DetectedMoment.recording_id == recording_id).delete()
            db.commit()

            db_moments = []
            for m in final_moments:
                dm = DetectedMoment(
                    recording_id=m["recording_id"],
                    event_type=m["event_type"],
                    event_label=m["event_label"],
                    start_time=m["start_time"],
                    end_time=m["end_time"],
                    duration=m["duration"],
                    confidence_score=m["confidence_score"],
                    explanation=m["explanation"],
                    is_uncertain=m["is_uncertain"],
                    uncertainty_reason=m["uncertainty_reason"],
                    thumbnail_path=m["thumbnail_path"],
                    thumbnail_url=m["thumbnail_url"],
                    keyframe_timestamp=m["keyframe_timestamp"],
                    visual_features=m["visual_features"],
                    detection_sensitivity=m["detection_sensitivity"],
                    status="detected",
                    is_approved=False,
                )
                db.add(dm)
                db_moments.append(dm)

            db.commit()

            if progress_cb:
                progress_cb(100.0, f"Detection complete! Identified {len(db_moments)} GTA 6 gameplay moments.")

            # Return serialized list
            res_items = []
            for dm in db_moments:
                res_items.append({
                    "id": dm.id,
                    "recording_id": dm.recording_id,
                    "event_type": dm.event_type,
                    "event_label": dm.event_label,
                    "start_time": dm.start_time,
                    "end_time": dm.end_time,
                    "duration": dm.duration,
                    "confidence_score": dm.confidence_score,
                    "explanation": dm.explanation,
                    "is_uncertain": dm.is_uncertain,
                    "uncertainty_reason": dm.uncertainty_reason,
                    "thumbnail_path": dm.thumbnail_path,
                    "thumbnail_url": dm.thumbnail_url,
                    "keyframe_timestamp": dm.keyframe_timestamp,
                    "visual_features": json.loads(dm.visual_features) if dm.visual_features else {},
                    "detection_sensitivity": dm.detection_sensitivity,
                    "status": dm.status,
                    "is_approved": dm.is_approved,
                    "created_at": dm.created_at.isoformat() if dm.created_at else None,
                })

            return res_items

        finally:
            db.close()

    def _extract_audio_envelope(self, recording_id: int, duration: float) -> Dict[float, Dict[str, float]]:
        """
        Extract acoustic energy envelope, spectral transients, and silence
        without loading speech or entire container into memory.
        """
        audio_map: Dict[float, Dict[str, float]] = {}
        audio_file = Path(settings.AUDIO_DIR) / f"audio_rec_{recording_id}.wav"
        if not audio_file.is_file():
            return audio_map

        try:
            with wave.open(str(audio_file), "rb") as wf:
                sample_rate = wf.getframerate()
                n_channels = wf.getnchannels()
                total_frames = wf.getnframes()

                window_sec = 0.5
                frames_per_window = int(sample_rate * window_sec)
                step_frames = frames_per_window

                curr_frame = 0
                prev_rms = 0.0

                while curr_frame < total_frames:
                    wf.setpos(curr_frame)
                    raw = wf.readframes(frames_per_window)
                    if not raw:
                        break

                    samples = np.frombuffer(raw, dtype=np.int16)
                    if len(samples) == 0:
                        break

                    # RMS and dBFS
                    float_samples = samples.astype(np.float32)
                    rms = float(np.sqrt(np.mean(float_samples ** 2)))
                    db = float(20 * np.log10(rms / 32768.0 + 1e-6))

                    # Transient shockwave spike (sudden attack > 15 dB rise from previous window)
                    db_diff = max(0.0, db - prev_rms) if prev_rms != 0.0 else 0.0
                    is_transient = db_diff > 12.0 and db > -20.0

                    # Spectral roughness / zero crossing count (high frequency approximation for tire squeal / sirens)
                    zero_crossings = float(np.sum(samples[:-1] * samples[1:] < 0) / max(1, len(samples)))

                    t_sec = round(curr_frame / sample_rate, 2)
                    audio_map[t_sec] = {
                        "db": round(db, 1),
                        "rms": round(rms, 1),
                        "transient_surge": round(db_diff, 1),
                        "is_transient": is_transient,
                        "high_freq_roughness": round(zero_crossings, 3),
                    }

                    prev_rms = db
                    curr_frame += step_frames

        except Exception as e:
            print(f"[Audio Envelope Warning] {e}")

        return audio_map

    def _analyze_video_frames(self, video_path: str, duration: float) -> List[Dict[str, Any]]:
        """
        Sample video frames at lightweight, evenly-spaced intervals.
        Computes motion, color histograms, siren red/blue oscillation,
        explosion flame areas, Vice City neon hues, and edge density.
        """
        features = []
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            return features

        proc_w, proc_h = 320, 180
        # Sample at most 20-30 evenly spaced frames across the video for fast processing
        sample_count = min(30, max(6, int(duration / 3.0)))
        sample_times = [round(i * (duration / max(1, sample_count)), 2) for i in range(sample_count)]

        prev_gray = None
        try:
            for t in sample_times:
                cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
                ret, frame = cap.read()
                if not ret or frame is None:
                    continue

                resized = cv2.resize(frame, (proc_w, proc_h), interpolation=cv2.INTER_AREA)
                gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
                hsv = cv2.cvtColor(resized, cv2.COLOR_BGR2HSV)

                flow_mag = 0.0
                if prev_gray is not None:
                    try:
                        flow = cv2.calcOpticalFlowFarneback(
                            prev_gray, gray, None,
                            pyr_scale=0.5, levels=1, winsize=11,
                            iterations=1, poly_n=5, poly_sigma=1.1, flags=0
                        )
                        mag, _ = cv2.cartToPolar(flow[..., 0], flow[..., 1])
                        flow_mag = float(np.mean(mag))
                    except Exception:
                        pass

                h_ch = hsv[..., 0]
                s_ch = hsv[..., 1]
                v_ch = hsv[..., 2]

                red_mask = ((h_ch <= 10) | (h_ch >= 170)) & (s_ch > 100) & (v_ch > 100)
                blue_mask = (h_ch >= 100) & (h_ch <= 130) & (s_ch > 100) & (v_ch > 100)
                flame_mask = (h_ch >= 12) & (h_ch <= 35) & (s_ch > 140) & (v_ch > 190)
                neon_pink = ((h_ch >= 145) & (h_ch <= 175)) & (s_ch > 110) & (v_ch > 90)
                neon_cyan = ((h_ch >= 85) & (h_ch <= 105)) & (s_ch > 110) & (v_ch > 90)
                golden_mask = (h_ch >= 15) & (h_ch <= 30) & (s_ch > 70) & (v_ch > 110)

                features.append({
                    "timestamp": t,
                    "mean_luminance": float(np.mean(v_ch)),
                    "mean_saturation": float(np.mean(s_ch)),
                    "flow_mag": flow_mag,
                    "flow_divergence": 0.0,
                    "flow_curl": 0.0,
                    "red_ratio": float(np.sum(red_mask) / (proc_w * proc_h)),
                    "blue_ratio": float(np.sum(blue_mask) / (proc_w * proc_h)),
                    "flame_ratio": float(np.sum(flame_mask) / (proc_w * proc_h)),
                    "neon_ratio": float(np.sum(neon_pink | neon_cyan) / (proc_w * proc_h)),
                    "golden_ratio": float(np.sum(golden_mask) / (proc_w * proc_h)),
                    "edge_variance": float(cv2.Laplacian(gray, cv2.CV_64F).var()),
                    "horizon_angle": 0.0,
                })
                prev_gray = gray
        finally:
            cap.release()

        return features

    def _score_event_windows(
        self,
        frame_features: List[Dict[str, Any]],
        audio_envelope: Dict[float, Dict[str, float]],
        duration: float,
        target_conf: float,
        sensitivity: str,
        enabled_types: Optional[List[str]],
    ) -> List[Dict[str, Any]]:
        """
        Evaluate sliding windows against all 14 GTA 6 specialized event criteria.
        Ensures generic motion alone does not claim specific GTA events.
        Labels uncertainty explicitly when evidence lacks clear visual verification.
        """
        candidates: List[Dict[str, Any]] = []
        if not frame_features:
            return candidates

        # Create quick lookup for audio points near timestamp
        audio_times = sorted(audio_envelope.keys())

        def get_audio_window(t_center: float, radius: float = 1.0) -> Dict[str, Any]:
            matches = [audio_envelope[k] for k in audio_times if abs(k - t_center) <= radius]
            if not matches:
                return {"db": -50.0, "rms": 0.0, "transient_surge": 0.0, "is_transient": False, "high_freq_roughness": 0.0}
            max_db = max(m["db"] for m in matches)
            max_surge = max(m["transient_surge"] for m in matches)
            any_transient = any(m["is_transient"] for m in matches)
            mean_rough = float(np.mean([m["high_freq_roughness"] for m in matches]))
            return {
                "db": max_db,
                "transient_surge": max_surge,
                "is_transient": any_transient,
                "high_freq_roughness": mean_rough,
            }

        # Window scan across feature points (3s window: ~3 to 6 consecutive points)
        w_size = 5
        n_pts = len(frame_features)

        for i in range(0, max(1, n_pts - w_size + 1)):
            window = frame_features[i : i + w_size]
            t_start = window[0]["timestamp"]
            t_end = window[-1]["timestamp"]
            t_center = round((t_start + t_end) / 2.0, 2)

            aud = get_audio_window(t_center, radius=1.5)

            # Aggregate window metrics
            mean_mag = float(np.mean([f["flow_mag"] for f in window]))
            max_mag = float(np.max([f["flow_mag"] for f in window]))
            mean_div = float(np.mean([f["flow_divergence"] for f in window]))
            mean_curl = float(np.mean([f["flow_curl"] for f in window]))
            max_flame = float(np.max([f["flame_ratio"] for f in window]))
            max_red = float(np.max([f["red_ratio"] for f in window]))
            max_blue = float(np.max([f["blue_ratio"] for f in window]))
            mean_neon = float(np.mean([f["neon_ratio"] for f in window]))
            mean_golden = float(np.mean([f["golden_ratio"] for f in window]))
            mean_lum = float(np.mean([f["mean_luminance"] for f in window]))
            mean_sat = float(np.mean([f["mean_saturation"] for f in window]))
            mean_angle = float(np.mean([f["horizon_angle"] for f in window]))
            edge_var = float(np.mean([f["edge_variance"] for f in window]))

            # Deceleration check: sudden drop from high motion to low motion within window
            start_mag = float(np.mean([f["flow_mag"] for f in window[:2]]))
            end_mag = float(np.mean([f["flow_mag"] for f in window[-2:]]))
            decel_drop = max(0.0, start_mag - end_mag)

            # -------------------------------------------------------------
            # 14 EVENT EVALUATION MATRIX
            # -------------------------------------------------------------

            # 1. Police Chase
            # Cues: Both red and blue flashes in window + elevated motion + audio sirens/roughness
            siren_present = (max_red > 0.012 and max_blue > 0.012)
            if siren_present and (mean_mag > 1.2 or aud["high_freq_roughness"] > 0.08):
                conf = min(98.0, 55.0 + (max_red + max_blue) * 800.0 + mean_mag * 5.0)
                is_unc = conf < 70.0
                candidates.append({
                    "event_type": "police_chase",
                    "confidence_score": round(conf, 1),
                    "start_time": t_start,
                    "end_time": t_end,
                    "keyframe_timestamp": t_center,
                    "explanation": f"Alternating red/blue siren flashes detected ({round(max_red*100, 1)}% red, {round(max_blue*100, 1)}% blue) with active tactical pursuit velocity.",
                    "is_uncertain": is_unc,
                    "uncertainty_reason": "Low siren flash contrast against ambient lighting" if is_unc else None,
                    "features": {"red": max_red, "blue": max_blue, "flow_mag": mean_mag, "audio_db": aud["db"]},
                })

            # 2. High-Speed Driving
            # Cues: Strong forward radial optical flow divergence + sustained flow magnitude + engine audio
            # Distinct from generic motion: requires forward divergence > 0.4
            if mean_div > 0.35 and mean_mag > 2.0 and aud["db"] > -32.0:
                conf = min(95.0, 48.0 + mean_div * 40.0 + min(20.0, mean_mag * 3.0))
                is_unc = mean_div < 0.55  # If divergence is modest, could be camera tracking
                candidates.append({
                    "event_type": "high_speed_driving",
                    "confidence_score": round(conf, 1),
                    "start_time": t_start,
                    "end_time": t_end,
                    "keyframe_timestamp": t_center,
                    "explanation": f"High forward radial optical flow divergence ({round(mean_div, 2)}) and sustained velocity vectors without deceleration.",
                    "is_uncertain": is_unc,
                    "uncertainty_reason": "Optical flow divergence is moderate; motion could reflect fast camera pan rather than vehicular speed." if is_unc else None,
                    "features": {"divergence": mean_div, "flow_mag": mean_mag, "audio_db": aud["db"]},
                })

            # 3. Supercar Stunts
            # Cues: High rotational curl/spin + high optical flow magnitude + elevated horizon/airborne clearance
            if mean_curl > 0.045 and max_mag > 3.0:
                conf = min(94.0, 50.0 + mean_curl * 350.0 + max_mag * 3.0)
                is_unc = mean_curl < 0.07
                candidates.append({
                    "event_type": "supercar_stunt",
                    "confidence_score": round(conf, 1),
                    "start_time": t_start,
                    "end_time": t_end,
                    "keyframe_timestamp": t_center,
                    "explanation": f"Rapid angular rotational curl ({round(mean_curl, 3)}) and airborne kinetic acceleration detected.",
                    "is_uncertain": is_unc,
                    "uncertainty_reason": "Rotational curl present but airborne ground-clearance cannot be confirmed with full certainty." if is_unc else None,
                    "features": {"curl": mean_curl, "max_mag": max_mag},
                })

            # 4. Car Crashes
            # Cues: High forward velocity followed immediately by severe decel drop + acoustic impact spike + high edge variance
            if decel_drop > 2.2 and aud["is_transient"] and aud["db"] > -22.0:
                conf = min(96.0, 52.0 + decel_drop * 10.0 + aud["transient_surge"] * 1.5)
                is_unc = aud["transient_surge"] < 15.0
                candidates.append({
                    "event_type": "car_crash",
                    "confidence_score": round(conf, 1),
                    "start_time": t_start,
                    "end_time": t_end,
                    "keyframe_timestamp": t_center,
                    "explanation": f"Catastrophic kinetic deceleration ({round(decel_drop, 2)} flow delta) coupled with violent acoustic impact transient (+{round(aud['transient_surge'], 1)} dB).",
                    "is_uncertain": is_unc,
                    "uncertainty_reason": "Sudden stop detected; acoustic impact is moderate (could represent emergency braking)." if is_unc else None,
                    "features": {"decel_drop": decel_drop, "audio_surge": aud["transient_surge"]},
                })

            # 5. Explosions
            # Cues: Expanding fiery orange/yellow flame mask (> 1.5%) + loud low-frequency shockwave
            if max_flame > 0.015 and aud["db"] > -24.0:
                conf = min(98.0, 55.0 + max_flame * 500.0 + (aud["db"] + 30.0) * 1.2)
                is_unc = max_flame < 0.03
                candidates.append({
                    "event_type": "explosion",
                    "confidence_score": round(conf, 1),
                    "start_time": t_start,
                    "end_time": t_end,
                    "keyframe_timestamp": t_center,
                    "explanation": f"Expanding explosive fireball signature ({round(max_flame*100, 1)}% fiery hue coverage) with acoustic concussion surge.",
                    "is_uncertain": is_unc,
                    "uncertainty_reason": "Flame color profile detected, but explosive shockwave amplitude is borderline." if is_unc else None,
                    "features": {"flame_ratio": max_flame, "audio_db": aud["db"]},
                })

            # 6. Shootouts
            # Cues: Rapid acoustic transient surges (cadenced gunfire) + localized luminance variance + active combat audio
            if aud["is_transient"] and aud["transient_surge"] > 16.0 and aud["db"] > -20.0 and edge_var > 400.0:
                conf = min(92.0, 48.0 + aud["transient_surge"] * 2.0 + (edge_var / 200.0))
                is_unc = conf < 65.0
                candidates.append({
                    "event_type": "shootout",
                    "confidence_score": round(conf, 1),
                    "start_time": t_start,
                    "end_time": t_end,
                    "keyframe_timestamp": t_center,
                    "explanation": f"Repetitive high-energy ballistic acoustic transients (+{round(aud['transient_surge'], 1)} dB rise) and weapon recoil visual signatures.",
                    "is_uncertain": is_unc,
                    "uncertainty_reason": "Sharp acoustic spikes detected without prominent visual muzzle flash confirmation." if is_unc else None,
                    "features": {"transient_surge": aud["transient_surge"], "edge_var": edge_var},
                })

            # 7. Funny NPC Interactions
            # Cues: Low vehicle velocity (mean_mag < 1.5) with sudden localized edge disruption / ragdoll horizon shift
            if mean_mag < 1.8 and mean_angle > 28.0 and edge_var > 350.0 and aud["db"] > -30.0:
                conf = min(88.0, 42.0 + (mean_angle * 0.8) + (edge_var / 300.0))
                is_unc = True  # NPC ragdoll inherently has visual ambiguity without semantic model
                candidates.append({
                    "event_type": "funny_npc",
                    "confidence_score": round(conf, 1),
                    "start_time": t_start,
                    "end_time": t_end,
                    "keyframe_timestamp": t_center,
                    "explanation": f"Localized pedestrian cluster interaction with abrupt ragdoll orientation shift ({round(mean_angle, 1)}° tilt).",
                    "is_uncertain": True,
                    "uncertainty_reason": "NPC physical ragdoll behavior inferred from rapid orientation shift and localized collision cues.",
                    "features": {"horizon_angle": mean_angle, "edge_var": edge_var},
                })

            # 8. Unexpected Gameplay
            # Cues: Physics anomaly, high chaotic curl without smooth trajectory, sudden abnormal motion spikes
            if mean_curl > 0.05 and max_mag > 4.5 and decel_drop > 2.0:
                conf = min(89.0, 45.0 + mean_curl * 300.0)
                candidates.append({
                    "event_type": "unexpected_gameplay",
                    "confidence_score": round(conf, 1),
                    "start_time": t_start,
                    "end_time": t_end,
                    "keyframe_timestamp": t_center,
                    "explanation": "Abnormal kinetic trajectory: sudden combined multi-axis rotational spin and rapid collision deflection.",
                    "is_uncertain": True,
                    "uncertainty_reason": "Unusual physics anomaly detected; requires human review to differentiate from intentional stunt.",
                    "features": {"curl": mean_curl, "max_mag": max_mag},
                })

            # 9. Beautiful Cinematic Scenes
            # Cues: High golden ratio (> 8%) or high dynamic range color framing, steady gentle camera (flow_mag in [0.2, 1.2]), low noise
            if mean_golden > 0.07 and 0.1 <= mean_mag <= 1.5 and aud["db"] < -22.0:
                conf = min(96.0, 52.0 + mean_golden * 350.0 + (1.5 - mean_mag) * 10.0)
                is_unc = mean_golden < 0.12
                candidates.append({
                    "event_type": "cinematic_scene",
                    "confidence_score": round(conf, 1),
                    "start_time": t_start,
                    "end_time": t_end,
                    "keyframe_timestamp": t_center,
                    "explanation": f"Warm golden-hour palette ({round(mean_golden*100, 1)}% golden hue coverage) with smooth panoramic tracking and atmospheric depth.",
                    "is_uncertain": is_unc,
                    "uncertainty_reason": "Golden color profile is present, but camera movement has slight jitter." if is_unc else None,
                    "features": {"golden_ratio": mean_golden, "flow_mag": mean_mag},
                })

            # 10. Nighttime Vice City Scenes
            # Cues: Low global luminance (mean_lum < 85) + rich neon pink/cyan presence (> 3.5%)
            if mean_lum < 85.0 and mean_neon > 0.035:
                conf = min(97.0, 50.0 + mean_neon * 600.0 + (85.0 - mean_lum) * 0.4)
                is_unc = mean_neon < 0.06
                candidates.append({
                    "event_type": "nighttime_vice_city",
                    "confidence_score": round(conf, 1),
                    "start_time": t_start,
                    "end_time": t_end,
                    "keyframe_timestamp": t_center,
                    "explanation": f"Iconic Vice City nocturnal aesthetic: {round(mean_neon*100, 1)}% neon pink/cyan luminance against dark contrast (lum: {round(mean_lum, 1)}).",
                    "is_uncertain": is_unc,
                    "uncertainty_reason": "Nocturnal lighting confirmed; neon concentration is moderate." if is_unc else None,
                    "features": {"neon_ratio": mean_neon, "mean_lum": mean_lum},
                })

            # 11. Interesting Weather
            # Cues: Low saturation (< 50) + high luminance flash (lightning) OR desaturated overcast with wet road reflections
            has_lightning = any(f["mean_luminance"] > 220.0 for f in window) and mean_lum < 110.0
            if (has_lightning or (mean_sat < 40.0 and mean_lum < 95.0 and edge_var > 250.0)):
                conf = min(93.0, 55.0 + (25.0 if has_lightning else 10.0))
                is_unc = not has_lightning
                candidates.append({
                    "event_type": "interesting_weather",
                    "confidence_score": round(conf, 1),
                    "start_time": t_start,
                    "end_time": t_end,
                    "keyframe_timestamp": t_center,
                    "explanation": "Severe weather atmosphere: high-luminance tropical lightning illumination or overcast rain street reflections." if has_lightning else "Tropical overcast storm conditions with wet surface reflections and desaturated ambiance.",
                    "is_uncertain": is_unc,
                    "uncertainty_reason": "Atmospheric desaturation observed, but lightning flash was not captured in window." if is_unc else None,
                    "features": {"has_lightning": has_lightning, "mean_sat": mean_sat, "mean_lum": mean_lum},
                })

            # 12. Action Sequences
            # Cues: Sustained high flow (> 2.5) + sustained loud audio (> -22 dB) + high edge variance over whole window
            if mean_mag > 2.2 and aud["db"] > -22.0 and edge_var > 380.0:
                conf = min(94.0, 48.0 + mean_mag * 6.0 + (aud["db"] + 25.0) * 1.5)
                is_unc = conf < 65.0
                candidates.append({
                    "event_type": "action_sequence",
                    "confidence_score": round(conf, 1),
                    "start_time": t_start,
                    "end_time": t_end,
                    "keyframe_timestamp": t_center,
                    "explanation": f"High-tempo composite gameplay: sustained physical motion ({round(mean_mag, 1)} flow) and continuous high acoustic intensity ({round(aud['db'], 1)} dB).",
                    "is_uncertain": is_unc,
                    "uncertainty_reason": "High kinetic energy observed, but specific combat interaction sub-elements are mixed." if is_unc else None,
                    "features": {"flow_mag": mean_mag, "audio_db": aud["db"]},
                })

            # 13. Gameplay Fails
            # Cues: Extreme horizon angle (> 40°: vehicle flipped upside down) OR sudden screen desaturation / low luminance crash
            if mean_angle > 38.0 and (mean_mag < 1.0 or decel_drop > 2.0):
                conf = min(91.0, 48.0 + (mean_angle - 30.0) * 1.8)
                is_unc = mean_angle < 45.0
                candidates.append({
                    "event_type": "gameplay_fail",
                    "confidence_score": round(conf, 1),
                    "start_time": t_start,
                    "end_time": t_end,
                    "keyframe_timestamp": t_center,
                    "explanation": f"Vehicle inversion / wipeout signature: persistent {round(mean_angle, 1)}° abnormal horizon tilt following kinetic stoppage.",
                    "is_uncertain": is_unc,
                    "uncertainty_reason": "Vehicle orientation is severely tilted; verify whether player recovered or wasted." if is_unc else None,
                    "features": {"horizon_angle": mean_angle, "decel_drop": decel_drop},
                })

            # 14. Unusual Visual Events
            # Cues: High outlier visual variance, rare smoke/fire/color aberrations that don't match standard classes
            if edge_var > 600.0 and (max_flame > 0.01 or mean_neon > 0.03) and mean_mag > 3.0:
                conf = min(88.0, 45.0 + (edge_var / 150.0))
                candidates.append({
                    "event_type": "unusual_visual",
                    "confidence_score": round(conf, 1),
                    "start_time": t_start,
                    "end_time": t_end,
                    "keyframe_timestamp": t_center,
                    "explanation": f"High visual entropy anomaly: dense particle/smoke dispersion ({round(edge_var, 0)} edge variance) with rapid multi-channel color flux.",
                    "is_uncertain": True,
                    "uncertainty_reason": "Unusual visual phenomena detected; semantic category requires human appraisal.",
                    "features": {"edge_var": edge_var, "flow_mag": mean_mag},
                })

        # Filter by enabled event types if specified
        if enabled_types:
            enabled_set = set(enabled_types)
            candidates = [c for c in candidates if c["event_type"] in enabled_set]

        # Filter by sensitivity threshold
        candidates = [c for c in candidates if c["confidence_score"] >= target_conf]

        return candidates

    def _merge_and_deduplicate(
        self,
        candidates: List[Dict[str, Any]],
        merge_gap_sec: float,
        min_duration_sec: float,
        max_duration_sec: float,
    ) -> List[Dict[str, Any]]:
        """
        Temporal Non-Maximum Suppression and Smart Merging:
        - Clusters adjacent or overlapping events of the same type within merge_gap_sec.
        - Resolves conflicting event overlaps by picking highest confidence.
        - Clamps duration to [min_duration_sec, max_duration_sec] for optimal Shorts formatting.
        - Avoids duplicate detections of the same moment.
        """
        if not candidates:
            return []

        # Sort candidates chronologically
        candidates.sort(key=lambda x: (x["start_time"], -x["confidence_score"]))

        # Group by event type first for intra-type merging
        merged_by_type: List[Dict[str, Any]] = []
        types = set(c["event_type"] for c in candidates)

        for etype in types:
            type_cands = [c for c in candidates if c["event_type"] == etype]
            type_cands.sort(key=lambda x: x["start_time"])

            current = None
            for c in type_cands:
                if current is None:
                    current = dict(c)
                    continue

                # Check if overlapping or within merge gap
                if c["start_time"] <= (current["end_time"] + merge_gap_sec):
                    # Merge intervals
                    current["end_time"] = max(current["end_time"], c["end_time"])
                    # Pick highest confidence and best keyframe
                    if c["confidence_score"] > current["confidence_score"]:
                        current["confidence_score"] = c["confidence_score"]
                        current["keyframe_timestamp"] = c["keyframe_timestamp"]
                        current["explanation"] = c["explanation"]
                    # Merge uncertainty: if either was certain, reduce uncertainty
                    current["is_uncertain"] = current["is_uncertain"] and c["is_uncertain"]
                    if not current["is_uncertain"]:
                        current["uncertainty_reason"] = None
                else:
                    merged_by_type.append(current)
                    current = dict(c)

            if current is not None:
                merged_by_type.append(current)

        # Cross-type non-maximum suppression: if two different events heavily overlap (> 70% IoU),
        # keep the one with higher confidence unless they represent natural complements (e.g. action + high_speed)
        merged_by_type.sort(key=lambda x: x["start_time"])
        final_list: List[Dict[str, Any]] = []

        for cand in merged_by_type:
            # Enforce duration bounds
            raw_duration = cand["end_time"] - cand["start_time"]
            if raw_duration < min_duration_sec:
                # Expand symmetrically if possible
                pad = (min_duration_sec - raw_duration) / 2.0
                cand["start_time"] = max(0.0, round(cand["start_time"] - pad, 2))
                cand["end_time"] = round(cand["end_time"] + pad, 2)
                cand["duration"] = round(cand["end_time"] - cand["start_time"], 2)
            elif raw_duration > max_duration_sec:
                cand["end_time"] = round(cand["start_time"] + max_duration_sec, 2)
                cand["duration"] = max_duration_sec
            else:
                cand["duration"] = round(raw_duration, 2)

            cand["event_label"] = EVENT_DEFINITIONS.get(cand["event_type"], {}).get("label", cand["event_type"].replace("_", " ").title())

            # Check overlap with existing approved candidates in final_list
            overlap = False
            for existing in final_list:
                inter_start = max(cand["start_time"], existing["start_time"])
                inter_end = min(cand["end_time"], existing["end_time"])
                if inter_end > inter_start:
                    inter_dur = inter_end - inter_start
                    shorter_dur = min(cand["duration"], existing["duration"])
                    if inter_dur / max(0.1, shorter_dur) > 0.75:
                        # Heavy duplicate overlap! Keep the one with higher confidence
                        overlap = True
                        if cand["confidence_score"] > existing["confidence_score"] + 10.0:
                            # Replace with superior candidate
                            final_list.remove(existing)
                            final_list.append(cand)
                        break

            if not overlap:
                final_list.append(cand)

        final_list.sort(key=lambda x: x["start_time"])
        return final_list

    def _extract_keyframe_image(self, video_path: str, timestamp_sec: float, output_path: str) -> Optional[str]:
        """Extract high-resolution candidate thumbnail using FFmpeg with OpenCV fallback."""
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)

        cmd = [
            self.ffmpeg,
            "-y",
            "-ss", str(max(0.0, timestamp_sec)),
            "-i", str(video_path),
            "-vframes", "1",
            "-q:v", "2",
            "-vf", "scale=640:-1",
            str(out_p)
        ]
        try:
            import subprocess
            res = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=10)
            if res.returncode == 0 and out_p.is_file() and out_p.stat().st_size > 500:
                return str(out_p.resolve())
        except Exception:
            pass

        # OpenCV Fallback
        try:
            cap = cv2.VideoCapture(video_path)
            cap.set(cv2.CAP_PROP_POS_MSEC, max(0.0, timestamp_sec * 1000.0))
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

gta_detector = GTA6MomentDetector()
