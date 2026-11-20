import os
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
import cv2
import numpy as np
from sqlalchemy.orm import Session
from sqlalchemy import desc

from ..config import settings
from ..database import SessionLocal
from ..models.recording import Recording
from ..models.detected_moment import DetectedMoment
from ..models.candidate_clip import CandidateClip
from ..models.analysis import RecordingAnalysis, TimelineSegment
from .video_service import get_ffmpeg_path

CLIP_CATEGORIES: Dict[str, Dict[str, str]] = {
    "badass_moments": {
        "label": "Badass Moments",
        "description": "High-octane driving, clean combat precision, and flawless escapes.",
        "color": "#ef4444",
        "icon": "Flame",
    },
    "police_chase": {
        "label": "Police Chase",
        "description": "Intense multi-car pursuit, flashing sirens, and tactical roadblocks.",
        "color": "#3b82f6",
        "icon": "Siren",
    },
    "car_stunts": {
        "label": "Epic Car Stunts",
        "description": "Massive ramp launches, aerial barrel rolls, and rooftop landings.",
        "color": "#a855f7",
        "icon": "Rocket",
    },
    "explosions": {
        "label": "Explosions",
        "description": "Catastrophic fireballs, chain vehicle blasts, and concussive shockwaves.",
        "color": "#f97316",
        "icon": "Bomb",
    },
    "funny_npc": {
        "label": "Funny NPC Moments",
        "description": "Hilarious ragdoll physics, crowd chaos, and unexpected NPC reactions.",
        "color": "#eab308",
        "icon": "Laugh",
    },
    "shootouts": {
        "label": "Shootouts",
        "description": "Heavy automatic gunfire firefights, cover maneuvers, and weapon accuracy.",
        "color": "#e11d48",
        "icon": "Crosshair",
    },
    "cinematic_scenes": {
        "label": "Cinematic Scenes",
        "description": "Breathtaking Vice City sunsets, neon skylines, and picturesque cruising.",
        "color": "#06b6d4",
        "icon": "Film",
    },
    "unexpected_events": {
        "label": "Unexpected Events",
        "description": "Unbelievable physics anomalies, wild glitches, and unpredictable mayhem.",
        "color": "#8b5cf6",
        "icon": "Sparkles",
    },
}

TARGET_LENGTHS = [15, 20, 30, 45, 60]

# Mapping from Phase 4 14-event taxonomy to Phase 5 8-category YouTube Shorts taxonomy
EVENT_TO_CATEGORY_MAP = {
    "police_chase": "police_chase",
    "high_speed_driving": "badass_moments",
    "supercar_stunt": "car_stunts",
    "car_crash": "unexpected_events",
    "explosion": "explosions",
    "shootout": "shootouts",
    "funny_npc": "funny_npc",
    "unexpected_gameplay": "unexpected_events",
    "cinematic_scene": "cinematic_scenes",
    "nighttime_vice_city": "cinematic_scenes",
    "interesting_weather": "cinematic_scenes",
    "action_sequence": "badass_moments",
    "gameplay_fail": "funny_npc",
    "unusual_visual": "unexpected_events",
}

class AIClipRanker:
    """
    Phase 5 AI Clip Ranking and Intelligent Selection Engine.
    Evaluates 9 heuristic scoring factors, optimizes clip boundaries for
    YouTube Shorts (15s, 20s, 30s, 45s, 60s), prevents abrupt cuts/missing action,
    and ranks clips from 1 to 100.
    """
    def __init__(self):
        self.ffmpeg = get_ffmpeg_path()
        self.thumbnails_dir = Path(settings.THUMBNAILS_DIR) / "candidates"
        self.thumbnails_dir.mkdir(parents=True, exist_ok=True)

    def optimize_clip_boundaries(
        self,
        climax_time: float,
        target_length: int,
        recording_duration: float,
        scene_cuts: Optional[List[float]] = None,
    ) -> Tuple[float, float, float, float]:
        """
        Calculates optimal start and end timestamps for the designated target duration.
        - Ensures appropriate pre-roll setup (1.5s - 4.0s) so viewers are hooked immediately.
        - Ensures appropriate post-roll resolution (2.0s - 5.0s) showing consequences/landing.
        - Avoids abrupt starts and endings by snapping to natural scene cuts if within 1.0s.
        - Clamps within [0, recording_duration].
        Returns (start_time, end_time, pre_roll_sec, post_roll_sec).
        """
        # Desired pre-roll based on clip target length
        # YouTube Shorts retention requires the hook in the first 2.5 - 3.5 seconds
        if target_length <= 15:
            ideal_pre_roll = min(3.0, max(1.5, climax_time * 0.3))
        elif target_length <= 20:
            ideal_pre_roll = min(4.0, max(2.0, climax_time * 0.35))
        elif target_length <= 30:
            ideal_pre_roll = min(6.0, max(3.0, climax_time * 0.4))
        elif target_length <= 45:
            ideal_pre_roll = min(8.0, max(4.0, climax_time * 0.45))
        else: # 60s
            ideal_pre_roll = min(12.0, max(5.0, climax_time * 0.5))

        proposed_start = max(0.0, climax_time - ideal_pre_roll)
        proposed_end = proposed_start + target_length

        # If proposed end exceeds video duration, shift window backwards
        if proposed_end > recording_duration:
            overflow = proposed_end - recording_duration
            proposed_start = max(0.0, proposed_start - overflow)
            proposed_end = min(recording_duration, proposed_start + target_length)

        # Snap to nearest natural scene cuts if within 1.0s to avoid abrupt partial cuts
        if scene_cuts:
            for cut_t in scene_cuts:
                if abs(cut_t - proposed_start) <= 1.0 and cut_t < climax_time - 1.0:
                    proposed_start = cut_t
                    proposed_end = min(recording_duration, proposed_start + target_length)
                    break

            for cut_t in scene_cuts:
                if abs(cut_t - proposed_end) <= 1.0 and cut_t > climax_time + 1.0:
                    proposed_end = cut_t
                    # keep target length within 1-2s tolerance
                    proposed_start = max(0.0, proposed_end - target_length)
                    break

        actual_duration = round(proposed_end - proposed_start, 2)
        actual_pre_roll = round(max(0.5, climax_time - proposed_start), 2)
        actual_post_roll = round(max(0.5, proposed_end - climax_time), 2)

        return round(proposed_start, 2), round(proposed_end, 2), actual_pre_roll, actual_post_roll

    def calculate_heuristic_score(
        self,
        category: str,
        moment_data: Optional[Dict[str, Any]],
        start_time: float,
        end_time: float,
        climax_time: float,
        pre_roll: float,
        post_roll: float,
        timeline_segments: List[TimelineSegment],
    ) -> Tuple[int, Dict[str, float], str]:
        """
        Scores candidate clip across the 9 factors (1 - 100):
        1. Visual Excitement
        2. Unexpectedness
        3. Action Intensity
        4. Cinematic Quality
        5. Entertainment Value
        6. Audio Excitement
        7. Event Completeness
        8. Beginning and Ending Quality
        9. Duplicate Penalty
        """
        # Base features from detected moment if available
        base_conf = float(moment_data.get("confidence_score", 70.0)) if moment_data else 65.0
        visual_feat = moment_data.get("visual_features", {}) if moment_data else {}
        is_uncertain = moment_data.get("is_uncertain", False) if moment_data else False

        # Timeline segments within this clip window
        win_segments = [s for s in timeline_segments if start_time <= s.timestamp <= end_time]
        peak_count = sum(1 for s in win_segments if s.is_audio_peak)
        cut_count = sum(1 for s in win_segments if s.is_scene_change)
        mean_excitement = float(np.mean([s.excitement_score for s in win_segments])) if win_segments else 60.0

        # 1. Visual Excitement (0 - 100)
        flow_mag = float(visual_feat.get("flow_mag", 2.5))
        flame_ratio = float(visual_feat.get("flame_ratio", 0.0))
        siren_ratio = float(visual_feat.get("red", 0.0) + visual_feat.get("blue", 0.0))
        v_excitement = min(100.0, 40.0 + min(35.0, flow_mag * 10.0) + flame_ratio * 400.0 + siren_ratio * 300.0)

        # 2. Unexpectedness (0 - 100)
        curl = float(visual_feat.get("curl", 0.0))
        decel = float(visual_feat.get("decel_drop", 0.0))
        unexp_boost = 30.0 if category in ["unexpected_events", "funny_npc", "car_stunts"] else 15.0
        unexpectedness = min(100.0, 35.0 + unexp_boost + curl * 400.0 + decel * 8.0)

        # 3. Action Intensity (0 - 100)
        action_boost = 30.0 if category in ["shootouts", "police_chase", "badass_moments"] else 15.0
        action_intensity = min(100.0, 35.0 + action_boost + min(30.0, mean_excitement * 0.4) + min(15.0, peak_count * 5.0))

        # 4. Cinematic Quality (0 - 100)
        golden = float(visual_feat.get("golden_ratio", 0.0))
        neon = float(visual_feat.get("neon_ratio", 0.0))
        cinematic_boost = 35.0 if category == "cinematic_scenes" else 15.0
        cinematic_quality = min(100.0, 45.0 + cinematic_boost + golden * 300.0 + neon * 300.0)

        # 5. Entertainment Value (0 - 100)
        entertainment_value = min(100.0, (v_excitement * 0.4) + (unexpectedness * 0.4) + (action_intensity * 0.2))
        if category in ["funny_npc", "car_stunts", "explosions"]:
            entertainment_value = min(100.0, entertainment_value + 10.0)

        # 6. Audio Excitement (0 - 100)
        audio_db = float(visual_feat.get("audio_db", -25.0))
        audio_surge = float(visual_feat.get("audio_surge", visual_feat.get("transient_surge", 10.0)))
        audio_excitement = min(100.0, max(20.0, 50.0 + (audio_db + 30.0) * 1.5 + audio_surge * 1.5 + peak_count * 4.0))

        # 7. Event Completeness (0 - 100)
        # Full arc check: did the event start and resolve cleanly?
        has_adequate_setup = pre_roll >= 1.5
        has_adequate_aftermath = post_roll >= 2.0
        completeness = 70.0
        if has_adequate_setup and has_adequate_aftermath:
            completeness = 95.0
        elif has_adequate_setup or has_adequate_aftermath:
            completeness = 80.0
        else:
            completeness = 55.0

        # 8. Beginning and Ending Quality (0 - 100)
        # Avoid abrupt starts and endings
        b_quality = 75.0
        if pre_roll >= 2.0:
            b_quality += 12.0
        elif pre_roll < 1.0:
            b_quality -= 20.0  # Abrupt start penalty

        if post_roll >= 2.5:
            b_quality += 13.0
        elif post_roll < 1.2:
            b_quality -= 20.0  # Abrupt ending penalty
        b_quality = min(100.0, max(20.0, b_quality))

        # 9. Duplicate similarity penalty (initially 0, calculated during ranking loop)
        dup_penalty = 0.0

        # Weighted Composite Score (1 - 100)
        weights = {
            "visual_excitement": 0.18,
            "unexpectedness": 0.14,
            "action_intensity": 0.16,
            "cinematic_quality": 0.12,
            "entertainment_value": 0.14,
            "audio_excitement": 0.14,
            "event_completeness": 0.06,
            "boundary_quality": 0.06,
        }

        composite_raw = (
            v_excitement * weights["visual_excitement"]
            + unexpectedness * weights["unexpectedness"]
            + action_intensity * weights["action_intensity"]
            + cinematic_quality * weights["cinematic_quality"]
            + entertainment_value * weights["entertainment_value"]
            + audio_excitement * weights["audio_excitement"]
            + completeness * weights["event_completeness"]
            + b_quality * weights["boundary_quality"]
        )

        # Apply uncertainty factor discount if visual verification was ambiguous
        if is_uncertain:
            composite_raw *= 0.90

        final_score = int(np.clip(round(composite_raw), 1, 100))

        breakdown = {
            "visual_excitement": round(v_excitement, 1),
            "unexpectedness": round(unexpectedness, 1),
            "action_intensity": round(action_intensity, 1),
            "cinematic_quality": round(cinematic_quality, 1),
            "entertainment_value": round(entertainment_value, 1),
            "audio_excitement": round(audio_excitement, 1),
            "event_completeness": round(completeness, 1),
            "boundary_quality": round(b_quality, 1),
            "duplicate_penalty": 0.0,
        }

        reason = (
            f"Heuristic score: {final_score}/100. High visual excitement ({round(v_excitement)}) "
            f"and action intensity ({round(action_intensity)}), with clean {round(pre_roll, 1)}s pre-roll hook "
            f"and complete {round(post_roll, 1)}s resolution arc. (Note: Heuristic estimate, not guaranteed viral prediction)."
        )

        return final_score, breakdown, reason

    def generate_ranked_candidates(
        self,
        recording_id: int,
        target_lengths: Optional[List[int]] = None,
        categories: Optional[List[str]] = None,
        min_score: int = 1,
        progress_cb=None,
    ) -> List[Dict[str, Any]]:
        """
        Master Phase 5 Pipeline:
        1. Retrieve recording, detected moments, and scene cut timestamps
        2. Expand moments and discover candidate windows for each target length (15s, 20s, 30s, 45s, 60s)
        3. Optimize boundaries (avoid abrupt cuts, align with scene transitions, ensure setup & resolution)
        4. Calculate 9-factor heuristic AI score (1-100)
        5. Apply duplicate similarity penalties to ensure variety
        6. Persist ranked candidates in SQLite
        7. Pre-select top 10 candidates by default
        """
        db = SessionLocal()
        try:
            rec = db.query(Recording).filter(Recording.id == recording_id).first()
            if not rec:
                raise ValueError(f"Recording #{recording_id} not found.")

            duration = rec.duration_seconds or 30.0
            video_path = rec.file_path

            # Retrieve detected moments and timeline cuts
            moments = db.query(DetectedMoment).filter(DetectedMoment.recording_id == recording_id).all()
            timeline_segments = db.query(TimelineSegment).filter(TimelineSegment.recording_id == recording_id).all()
            scene_cuts = [s.timestamp for s in timeline_segments if s.is_scene_change]

            lengths = target_lengths or TARGET_LENGTHS
            # Filter lengths exceeding video duration
            lengths = [L for L in lengths if L <= max(15, duration + 2.0)]
            if not lengths:
                lengths = [int(min(duration, 15))]

            if progress_cb:
                progress_cb(10.0, f"Evaluating candidate seeds across {len(lengths)} Shorts durations...")

            candidate_seeds = []

            # 1. Seeds from Phase 4 Detected Moments
            for m in moments:
                cat = EVENT_TO_CATEGORY_MAP.get(m.event_type, "unexpected_events")
                if categories and cat not in categories:
                    continue

                climax = m.keyframe_timestamp or round((m.start_time + m.end_time) / 2.0, 2)
                candidate_seeds.append({
                    "moment_id": m.id,
                    "climax_time": climax,
                    "category": cat,
                    "category_label": CLIP_CATEGORIES.get(cat, {}).get("label", cat.title()),
                    "title": f"GTA 6 {CLIP_CATEGORIES.get(cat, {}).get('label', cat.title())}",
                    "moment_data": {
                        "confidence_score": m.confidence_score,
                        "is_uncertain": m.is_uncertain,
                        "visual_features": json.loads(m.visual_features) if m.visual_features else {},
                        "explanation": m.explanation,
                    },
                })

            # 2. If no detected moments yet or short recording, generate seeds from peak timeline segments
            if not candidate_seeds:
                peak_segments = [s for s in timeline_segments if s.is_audio_peak or s.excitement_score >= 60.0]
                if not peak_segments:
                    # Generic midpoint seed
                    peak_segments = [TimelineSegment(timestamp=min(duration * 0.5, 5.0), excitement_score=75.0)]

                for idx, ps in enumerate(peak_segments[:6], 1):
                    cat = "badass_moments" if idx % 2 == 0 else "car_stunts"
                    candidate_seeds.append({
                        "moment_id": None,
                        "climax_time": ps.timestamp,
                        "category": cat,
                        "category_label": CLIP_CATEGORIES[cat]["label"],
                        "title": f"GTA 6 {CLIP_CATEGORIES[cat]['label']} Highlight #{idx}",
                        "moment_data": {"confidence_score": ps.excitement_score, "is_uncertain": False, "visual_features": {}},
                    })

            if progress_cb:
                progress_cb(35.0, "Optimizing clip boundaries and pre-roll/post-roll margins...")

            # Generate candidate clips for each seed and target duration
            raw_candidates = []
            for seed in candidate_seeds:
                climax = seed["climax_time"]
                for L in lengths:
                    start_t, end_t, pre_roll, post_roll = self.optimize_clip_boundaries(
                        climax_time=climax,
                        target_length=L,
                        recording_duration=duration,
                        scene_cuts=scene_cuts,
                    )

                    ai_score, breakdown, reason = self.calculate_heuristic_score(
                        category=seed["category"],
                        moment_data=seed.get("moment_data"),
                        start_time=start_t,
                        end_time=end_t,
                        climax_time=climax,
                        pre_roll=pre_roll,
                        post_roll=post_roll,
                        timeline_segments=timeline_segments,
                    )

                    raw_candidates.append({
                        "recording_id": recording_id,
                        "detected_moment_id": seed.get("moment_id"),
                        "category": seed["category"],
                        "category_label": seed["category_label"],
                        "title": f"{seed['title']} ({int(end_t - start_t)}s)",
                        "start_time": start_t,
                        "end_time": end_t,
                        "duration": round(end_t - start_t, 2),
                        "target_length": L,
                        "climax_time": climax,
                        "pre_roll_sec": pre_roll,
                        "post_roll_sec": post_roll,
                        "ai_score": ai_score,
                        "score_breakdown": breakdown,
                        "score_reason": reason,
                    })

            if progress_cb:
                progress_cb(60.0, "Penalizing duplicate overlaps and ranking candidates from 1–100...")

            # 3. Sort by initial score descending
            raw_candidates.sort(key=lambda x: -x["ai_score"])

            # 4. Duplicate Similarity Penalty
            # Penalize clips that heavily overlap with a higher-scoring clip
            ranked_candidates = []
            for cand in raw_candidates:
                dup_penalty = 0.0
                for accepted in ranked_candidates:
                    # Check temporal intersection over union
                    overlap_start = max(cand["start_time"], accepted["start_time"])
                    overlap_end = min(cand["end_time"], accepted["end_time"])
                    if overlap_end > overlap_start:
                        inter_dur = overlap_end - overlap_start
                        union_dur = (cand["end_time"] - cand["start_time"]) + (accepted["end_time"] - accepted["start_time"]) - inter_dur
                        iou = inter_dur / max(0.1, union_dur)
                        if iou > 0.40:
                            # Significant overlap! Apply progressive duplicate penalty
                            dup_penalty = max(dup_penalty, min(25.0, round(iou * 35.0, 1)))

                if dup_penalty > 0:
                    cand["ai_score"] = int(max(1, cand["ai_score"] - dup_penalty))
                    cand["score_breakdown"]["duplicate_penalty"] = -dup_penalty
                    cand["score_reason"] = f"{cand['score_reason']} [Duplicate similarity penalty: -{int(dup_penalty)} pts due to overlap with top clip]."

                if cand["ai_score"] >= min_score:
                    ranked_candidates.append(cand)

            # Re-sort after penalties
            ranked_candidates.sort(key=lambda x: -x["ai_score"])

            # Assign selection ranks (1, 2, 3...)
            for idx, cand in enumerate(ranked_candidates, 1):
                cand["selection_rank"] = idx
                # Pre-select top 10 by default
                cand["is_selected"] = idx <= 10

            if progress_cb:
                progress_cb(80.0, "Generating representative candidate thumbnails on disk...")

            # 5. Extract Thumbnails for Candidates
            rec_thumb_dir = self.thumbnails_dir / f"rec_{recording_id}"
            rec_thumb_dir.mkdir(parents=True, exist_ok=True)

            for cand in ranked_candidates:
                t_frame = cand["climax_time"]
                thumb_filename = f"cand_{cand['category']}_{cand['target_length']}s_{int(t_frame * 1000)}.jpg"
                thumb_path = rec_thumb_dir / thumb_filename

                extracted = self._extract_keyframe(video_path, t_frame, str(thumb_path))
                cand["thumbnail_path"] = str(thumb_path) if extracted else None
                cand["thumbnail_url"] = f"/api/candidate-clips/{recording_id}/thumbnails/{thumb_filename}" if extracted else None

            if progress_cb:
                progress_cb(92.0, "Persisting ranked candidates in SQLite database...")

            # 6. Save in SQLite
            # Clear previous candidates for this recording to avoid stale clutter
            db.query(CandidateClip).filter(CandidateClip.recording_id == recording_id).delete()
            db.commit()

            db_items = []
            for cand in ranked_candidates:
                c = CandidateClip(
                    recording_id=cand["recording_id"],
                    detected_moment_id=cand["detected_moment_id"],
                    category=cand["category"],
                    category_label=cand["category_label"],
                    title=cand["title"],
                    start_time=cand["start_time"],
                    end_time=cand["end_time"],
                    duration=cand["duration"],
                    target_length=cand["target_length"],
                    climax_time=cand["climax_time"],
                    pre_roll_sec=cand["pre_roll_sec"],
                    post_roll_sec=cand["post_roll_sec"],
                    ai_score=cand["ai_score"],
                    score_breakdown=json.dumps(cand["score_breakdown"]),
                    score_reason=cand["score_reason"],
                    is_selected=cand["is_selected"],
                    selection_rank=cand["selection_rank"],
                    thumbnail_path=cand["thumbnail_path"],
                    thumbnail_url=cand["thumbnail_url"],
                    status="candidate",
                    is_approved=False,
                )
                db.add(c)
                db_items.append(c)

            db.commit()

            if progress_cb:
                progress_cb(100.0, f"Ranked {len(db_items)} candidate clips successfully (Top Score: {ranked_candidates[0]['ai_score'] if ranked_candidates else 0})")

            # Return serialized list
            results = []
            for c in db_items:
                results.append({
                    "id": c.id,
                    "recording_id": c.recording_id,
                    "detected_moment_id": c.detected_moment_id,
                    "category": c.category,
                    "category_label": c.category_label,
                    "title": c.title,
                    "start_time": c.start_time,
                    "end_time": c.end_time,
                    "duration": c.duration,
                    "target_length": c.target_length,
                    "climax_time": c.climax_time,
                    "pre_roll_sec": c.pre_roll_sec,
                    "post_roll_sec": c.post_roll_sec,
                    "ai_score": c.ai_score,
                    "score_breakdown": json.loads(c.score_breakdown) if c.score_breakdown else {},
                    "score_reason": c.score_reason,
                    "is_selected": c.is_selected,
                    "selection_rank": c.selection_rank,
                    "thumbnail_path": c.thumbnail_path,
                    "thumbnail_url": c.thumbnail_url,
                    "status": c.status,
                    "is_approved": c.is_approved,
                    "created_at": c.created_at.isoformat() if c.created_at else None,
                })

            return results

        finally:
            db.close()

    def batch_select_clips(
        self,
        recording_id: int,
        select_top_n: Optional[int] = None,
        selected_ids: Optional[List[int]] = None,
        deselect_all: bool = False,
    ) -> List[int]:
        """Update candidate clip selection flags in SQLite."""
        db = SessionLocal()
        try:
            clips = db.query(CandidateClip).filter(CandidateClip.recording_id == recording_id).order_by(CandidateClip.selection_rank.asc()).all()

            if deselect_all:
                for c in clips:
                    c.is_selected = False
                db.commit()
                return []

            if select_top_n is not None:
                selected_ids_result = []
                for idx, c in enumerate(clips):
                    is_sel = idx < select_top_n
                    c.is_selected = is_sel
                    if is_sel:
                        selected_ids_result.append(c.id)
                db.commit()
                return selected_ids_result

            if selected_ids is not None:
                id_set = set(selected_ids)
                for c in clips:
                    c.is_selected = c.id in id_set
                db.commit()
                return [c.id for c in clips if c.is_selected]

            return [c.id for c in clips if c.is_selected]
        finally:
            db.close()

    def _extract_keyframe(self, video_path: str, timestamp_sec: float, output_path: str) -> Optional[str]:
        """Extract candidate thumbnail with FFmpeg / OpenCV."""
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

clip_ranker = AIClipRanker()
