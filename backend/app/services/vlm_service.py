import os
import base64
import json
import urllib.request
import urllib.error
from pathlib import Path
from typing import Optional, Dict, Any

class LocalVLMService:
    """
    Interface for optional local Vision-Language Models (e.g., Ollama running LLaVA,
    Moondream, or Qwen2-VL) to classify GTA 6 gameplay keyframes and surrounding context.
    Falls back gracefully to OpenCV visual analysis when VLM is unavailable or offline.
    """
    def __init__(self, endpoint: str = "http://127.0.0.1:11434", default_model: str = "llava"):
        self.endpoint = endpoint.rstrip("/")
        self.default_model = default_model
        self._is_available: Optional[bool] = None

    def check_status(self) -> Dict[str, Any]:
        """Check if local VLM server (e.g. Ollama) is reachable and list vision models."""
        try:
            req = urllib.request.Request(f"{self.endpoint}/api/tags", headers={"User-Agent": "GTA-ClipForge-AI"})
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name", "") for m in data.get("models", [])]
                    vision_models = [m for m in models if any(v in m.lower() for v in ["llava", "vision", "moondream", "qwen2-vl", "bakllava"])]
                    self._is_available = len(vision_models) > 0
                    return {
                        "available": self._is_available,
                        "server_online": True,
                        "endpoint": self.endpoint,
                        "vision_models": vision_models,
                        "active_model": vision_models[0] if vision_models else self.default_model,
                    }
        except Exception:
            pass

        self._is_available = False
        return {
            "available": False,
            "server_online": False,
            "endpoint": self.endpoint,
            "vision_models": [],
            "active_model": None,
        }

    def analyze_gameplay_frame(
        self,
        image_path: str,
        provisional_event: Optional[str] = None,
        motion_context: Optional[str] = None,
        model_name: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Query local VLM with keyframe and surrounding context.
        Returns classified event, confidence, explanation, and uncertainty assessment.
        """
        img_p = Path(image_path)
        if not img_p.is_file():
            return None

        # Quick check if server is reachable
        if self._is_available is False:
            return None

        status = self.check_status()
        if not status["available"]:
            return None

        chosen_model = model_name or status.get("active_model") or self.default_model

        try:
            with open(str(img_p), "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            prompt = (
                "You are an expert video game analyst for clean GTA 6 gameplay (no facecam, no commentary).\n"
                f"Surrounding physical context: {motion_context or 'Standard gameplay flow'}. "
                f"Preliminary candidate: {provisional_event or 'unknown'}.\n"
                "Examine this frame carefully. Classify the gameplay event into EXACTLY ONE of the following types:\n"
                "1. police_chase (sirens, squad cars, pursuit, roadblocks)\n"
                "2. high_speed_driving (rapid motion, expressway, clear forward corridor)\n"
                "3. supercar_stunt (airborne ramp launch, barrel roll, rooftop leap)\n"
                "4. car_crash (impact, vehicle collision, crumpled chassis)\n"
                "5. explosion (fireball, explosive blast, blown vehicle)\n"
                "6. shootout (gunfire, muzzle flash, firefight, cover)\n"
                "7. funny_npc (bizarre pedestrian ragdoll, crowd anomaly)\n"
                "8. unexpected_gameplay (physics glitch, bizarre vehicle interaction)\n"
                "9. cinematic_scene (golden hour, vista, picturesque skyline, composition)\n"
                "10. nighttime_vice_city (vibrant neon pink/cyan lighting, nightlife)\n"
                "11. interesting_weather (heavy tropical storm, rain reflection, lightning)\n"
                "12. action_sequence (fast multi-phase combat/pursuit combination)\n"
                "13. gameplay_fail (wasted screen, inverted stuck vehicle, fatal wipeout)\n"
                "14. unusual_visual (rare graphical occurrence, smoke/lighting anomaly)\n"
                "Or none if standard mundane wandering.\n\n"
                "Return ONLY a valid JSON object matching this schema:\n"
                "{\n"
                '  "event_type": "<one_of_the_above_or_none>",\n'
                '  "confidence": <float 0.0 to 1.0>,\n'
                '  "is_uncertain": <true or false>,\n'
                '  "uncertainty_reason": "<brief note if uncertain, else null>",\n'
                '  "explanation": "<concise factual 1-sentence explanation of visible visual cues>"\n'
                "}"
            )

            payload = {
                "model": chosen_model,
                "prompt": prompt,
                "images": [img_b64],
                "stream": False,
                "format": "json",
                "options": {
                    "temperature": 0.1,
                    "num_predict": 150,
                }
            }

            data_bytes = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                f"{self.endpoint}/api/generate",
                data=data_bytes,
                headers={"Content-Type": "application/json"}
            )

            with urllib.request.urlopen(req, timeout=12.0) as resp:
                if resp.status == 200:
                    res_json = json.loads(resp.read().decode("utf-8"))
                    raw_text = res_json.get("response", "").strip()
                    parsed = json.loads(raw_text)
                    if parsed.get("event_type") and parsed.get("event_type") != "none":
                        return {
                            "event_type": parsed["event_type"],
                            "confidence": float(parsed.get("confidence", 0.7)),
                            "is_uncertain": bool(parsed.get("is_uncertain", False)),
                            "uncertainty_reason": parsed.get("uncertainty_reason"),
                            "explanation": parsed.get("explanation", "Verified via local vision-language model."),
                            "source": f"vlm:{chosen_model}",
                        }
        except Exception as e:
            # Fall back gracefully to OpenCV without breaking
            pass

        return None

vlm_service = LocalVLMService()
