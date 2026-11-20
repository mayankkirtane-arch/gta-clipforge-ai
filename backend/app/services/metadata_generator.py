import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from ..models.clip import Clip, MomentType
from ..models.candidate_clip import CandidateClip
from ..models.detected_moment import DetectedMoment
from ..models.recording import Recording
from ..models.clip_metadata import ClipMetadata
from ..config import settings

# Curated, non-clickbait, gameplay-faithful title templates categorized by event type
METADATA_PRESETS: Dict[str, Dict[str, Any]] = {
    "police_chase": {
        "titles": [
            "GTA 6 Police Chase Went CRAZY 💀",
            "When The GTA 6 Cops Don't Play Around 🚓💨",
            "Closest Police Escape in Vice City! 🚨",
            "Can You Actually Escape 5 Stars in GTA 6? 😱",
            "This GTA 6 Pursuit Ended in Pure Chaos 💥",
            "Most Intense Police Pursuit in Vice City 🚓",
        ],
        "hooks": [
            "Wait until you see how this GTA 6 chase ends... 💀",
            "The GTA 6 police AI is on another level in this pursuit 🚨",
            "I genuinely thought this escape was impossible... watch this 🚓",
        ],
        "hashtags": ["#GTA6", "#GTA6Shorts", "#PoliceChase", "#ViceCity", "#GamingShorts"],
        "thumbnail_texts": ["LOST THEM?! 🚓", "5 STARS 💀", "NO ESCAPE", "INSANE PURSUIT"],
        "pinned_comments": [
            "Rate this police escape from 1 to 10! 👇",
            "Would you have taken that corner or crashed immediately? Be honest 😂",
            "What's your go-to getaway vehicle in Vice City? Drop it below! 🔥",
        ],
        "description_intro": "High-speed police pursuit through the neon streets of Vice City. The law enforcement AI in GTA 6 is relentless!",
    },
    "car_stunt": {
        "titles": [
            "Craziest GTA 6 Car Stunt! 🏎️💨",
            "Hit This Stunt in Vice City Perfectly! 🔥",
            "GTA 6 Vehicle Physics Are UNREAL 🤯",
            "Landing This Jump in GTA 6 Felt Amazing 🏆",
            "Physics Glitch or Skill? Craziest GTA 6 Stunt! 💀",
            "Supercar Stunt Jump in Vice City! 🚀",
        ],
        "hooks": [
            "Check out this jump over the Vice City canal... 🏎️",
            "The suspension physics in GTA 6 made this stunt look insane 🔥",
            "Didn't think the car would survive this landing... 🤯",
        ],
        "hashtags": ["#GTA6", "#GTA6Shorts", "#CarStunt", "#ViceCity", "#Gaming"],
        "thumbnail_texts": ["PERFECT JUMP 🏎️", "AIRTIME 🤯", "HOW DID HE LAND?!", "10/10 STUNT"],
        "pinned_comments": [
            "Rate this landing from 1 to 10! 👇",
            "Should I try hitting this stunt with a motorcycle next? Let me know! 🏍️",
            "What's the highest jump you've pulled off in GTA 6 so far? 🔥",
        ],
        "description_intro": "Pulling off a high-flying supercar stunt jump in Vice City. The vehicle suspension and aerodynamics in GTA 6 look incredible!",
    },
    "explosion": {
        "titles": [
            "This GTA 6 Explosion Was PURE CHAOS 💥",
            "When Everything Blows Up At Once in GTA 6 🔥",
            "Most Satisfying Chain Reaction Explosion in GTA 6! 💣",
            "Vice City Detonation Gone Completely Wrong 💀",
            "GTA 6 Fireball Physics Look Next-Gen! 🤯",
            "Massive Blast Sequence in Vice City! 💥",
        ],
        "hooks": [
            "Watch this chain reaction explosion unfold in slow motion 💥",
            "The fire and smoke effects in GTA 6 are genuinely next-gen 🔥",
            "Everything in this intersection exploded at the exact same second 💣",
        ],
        "hashtags": ["#GTA6", "#GTA6Shorts", "#EpicExplosion", "#ViceCity", "#GamingShorts"],
        "thumbnail_texts": ["TOTAL CHAOS 💥", "MASSIVE BOOM 🔥", "BLOWN AWAY", "PURE MAYHEM"],
        "pinned_comments": [
            "Did you expect the second explosion to go off? 😂",
            "The smoke physics in GTA 6 are insane. What do you think of the visuals? 👇",
            "Drop a like if you love explosive GTA moments! More coming daily 🔥",
        ],
        "description_intro": "Massive chain-reaction explosion tearing through Vice City. Smoke particles, volumetric flames, and sound design in full effect!",
    },
    "shootout": {
        "titles": [
            "Surviving This GTA 6 Shootout Felt Impossible 🎯",
            "Intense Vice City Gunfight Action! 🔥",
            "When You Get Pinned Down in GTA 6 💀",
            "Most Tactical Shootout in GTA 6 So Far! 💥",
            "GTA 6 Combat Mechanics in Action 🔫",
            "Clutch Aim Under Heavy Fire in Vice City! 🎯",
        ],
        "hooks": [
            "Watch how close this health bar got during this gunfight 🎯",
            "The cover mechanics and recoil in GTA 6 make shootouts intense 🔥",
            "Pinned down with zero armor left... check out this turnaround 💀",
        ],
        "hashtags": ["#GTA6", "#GTA6Shorts", "#Shootout", "#ViceCity", "#Gaming"],
        "thumbnail_texts": ["PINNED DOWN 🎯", "SURVIVED THIS?!", "CLUTCH AIM 🔫", "WARZONE"],
        "pinned_comments": [
            "What's your favorite weapon in GTA 6 so far? Drop your loadout below! 🔫",
            "Rate this combat clutch from 1 to 10! 👇",
            "Should I do a stealth run or go in guns blazing next? Let me know! 🔥",
        ],
        "description_intro": "Intense urban gunfight in Vice City showing off GTA 6's dynamic cover mechanics, bullet impacts, and tactical combat gameplay.",
    },
    "vice_city": {
        "titles": [
            "Vice City Looks INSANE at Night 🔥",
            "GTA 6 Neon Sunset Hits Completely Different 🌴",
            "Cruising Through Vice City Looks Like Real Life 🚗",
            "The Atmosphere in GTA 6 is Peak Gaming Aesthetic ✨",
            "Nighttime in Vice City is Absolutely Gorgeous 🌃",
            "Vice City Ocean Drive Vibes in GTA 6! 🌴",
        ],
        "hooks": [
            "Vice City lighting at night is on another level 🔥",
            "Take a look at the puddle reflections and neon glow in this clip ✨",
            "The retro 80s aesthetic of Vice City never gets old 🌴",
        ],
        "hashtags": ["#GTA6", "#ViceCity", "#GTA6Shorts", "#GamingAesthetic", "#Gaming"],
        "thumbnail_texts": ["PURE VIBES 🌴", "INSANE GRAPHICS 🔥", "NEON VICE ✨", "NIGHT DRIVE"],
        "pinned_comments": [
            "Is Vice City the most beautiful GTA map ever created? Let me know! 👇",
            "What's your favorite radio station while cruising at night in GTA 6? 📻",
            "Drop a like if you can't wait to explore every corner of Vice City! 🌴",
        ],
        "description_intro": "Atmospheric cinematic drive through neon-lit Vice City. Next-generation global illumination, ocean reflections, and iconic 80s aesthetics.",
    },
    "funny_npc": {
        "titles": [
            "That NPC Really Did That?! 😂",
            "GTA 6 NPC AI Had Zero Braincells Here 💀",
            "Funniest GTA 6 Interaction Ever Caught on Video 🤣",
            "When the NPC AI in GTA 6 Completely Breaks 😂",
            "Vice City NPCs Are Out of Control! 💀",
            "Bro Thought He Was The Main Character 😂",
        ],
        "hooks": [
            "Wait for what this NPC does in the background... 😂",
            "The NPC reactions in GTA 6 never fail to make me laugh 💀",
            "I genuinely did NOT expect this NPC conversation to end like this 🤣",
        ],
        "hashtags": ["#GTA6", "#GTA6Shorts", "#FunnyMoments", "#ViceCity", "#NPCMoments"],
        "thumbnail_texts": ["BRO WHAT?! 😂", "NPC MOMENT 💀", "HE TRIED IT 🤣", "INSTANT REGRET"],
        "pinned_comments": [
            "What would you do if an NPC did this to you? 😂",
            "GTA 6 NPCs are undefeated. What's the funniest glitch you've seen so far? 👇",
            "Subscribe for more hilarious GTA 6 NPC encounters every day! 💀",
        ],
        "description_intro": "Unscripted, hilarious NPC interaction caught live during free-roam in Vice City. The dynamic crowd AI in GTA 6 creates pure comedy!",
    },
    "badass_action": {
        "titles": [
            "Most Badass Moment in GTA 6 So Far! 😎",
            "When You Pull Off The Perfect Action Sequence in GTA 6 🔥",
            "Protagonist Energy in Full Effect in Vice City 💥",
            "Cleanest Action Highlight in GTA 6! 🏆",
            "GTA 6 Action Scenes Feel Like a Movie 🎬",
            "Unstoppable Momentum in Vice City! ⚡",
        ],
        "hooks": [
            "This whole sequence felt like a Hollywood action movie 🔥",
            "Watch how cleanly this entire mission objective was handled 😎",
            "Zero hesitation during this whole GTA 6 highlight 🏆",
        ],
        "hashtags": ["#GTA6", "#GTA6Shorts", "#BadassMoments", "#ViceCity", "#Gaming"],
        "thumbnail_texts": ["TOO SMOOTH 😎", "BADASS MOVE 🔥", "MOVIE SCENE 🎬", "UNSTOPPABLE"],
        "pinned_comments": [
            "Rate this action sequence from 1 to 10! 👇",
            "Drop a like if you love cinematic GTA gameplay! More shorts coming daily 🔥",
            "What mission should I tackle next in Vice City? Let me know! ⚡",
        ],
        "description_intro": "Action-packed gameplay highlight showcasing flawless combat flow, driving precision, and cinematic energy in GTA 6.",
    },
}

class MetadataGeneratorService:
    """
    AI-powered YouTube Shorts Metadata Generator for GTA CLIPFORGE AI.
    Produces:
    - 5 Title Suggestions (footage-faithful, non-clickbait)
    - 3 Opening Hook Suggestions
    - Optimized YouTube Shorts Description
    - 4-5 Curated Relevant Hashtags
    - Thumbnail Text Suggestions (punchy 2-4 words)
    - Pinned Comment Suggestions
    Saves and persists directly to SQLite `clip_metadata` table.
    """

    def resolve_category_key(self, clip: Clip, cand: Optional[CandidateClip] = None, moment: Optional[DetectedMoment] = None) -> str:
        """Determines the most specific category key from clip, preset, candidate, and detected moment."""
        preset = (clip.preset_name or "").upper()
        m_type = (clip.moment_type.value if hasattr(clip.moment_type, 'value') else str(clip.moment_type or "")).lower()
        cand_cat = (cand.category if cand else "").lower()
        mom_type = (moment.event_type if moment else "").lower()
        title_lower = (clip.title or "").lower()

        # Priority 1: Presets
        if "POLICE" in preset or "CHASE" in preset:
            return "police_chase"
        if "STUNT" in preset or "SUPER CAR" in preset:
            return "car_stunt"
        if "EXPLOSION" in preset:
            return "explosion"
        if "SHOOTOUT" in preset:
            return "shootout"
        if "VICE CITY" in preset:
            return "vice_city"
        if "FUNNY" in preset or "NPC" in preset:
            return "funny_npc"
        if "BADASS" in preset:
            return "badass_action"

        # Priority 2: Moment Type & Detected Moment
        if "chase" in m_type or "chase" in mom_type or "police" in mom_type:
            return "police_chase"
        if "stunt" in m_type or "stunt" in mom_type or "jump" in mom_type:
            return "car_stunt"
        if "explosion" in m_type or "explosion" in mom_type:
            return "explosion"
        if "shootout" in m_type or "combat" in mom_type or "shoot" in mom_type:
            return "shootout"
        if "funny" in m_type or "fail" in m_type or "npc" in mom_type:
            return "funny_npc"
        if "cinematic" in cand_cat or "night" in mom_type or "weather" in mom_type:
            return "vice_city"

        # Priority 3: Title cues
        if "chase" in title_lower or "police" in title_lower:
            return "police_chase"
        if "stunt" in title_lower or "car" in title_lower:
            return "car_stunt"
        if "explosion" in title_lower:
            return "explosion"
        if "shootout" in title_lower:
            return "shootout"
        if "npc" in title_lower or "funny" in title_lower:
            return "funny_npc"
        if "vice" in title_lower or "night" in title_lower:
            return "vice_city"

        return "badass_action"

    def generate_metadata_for_clip(
        self,
        db: Session,
        clip_id: int,
        tone: str = "viral",
        focus_keyword: Optional[str] = None,
        overwrite: bool = True
    ) -> ClipMetadata:
        """
        Generates and saves complete YouTube Shorts metadata for a specific clip.
        Persists to SQLite `clip_metadata`.
        """
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            raise ValueError(f"Clip #{clip_id} not found in database.")

        # Check existing metadata
        existing = db.query(ClipMetadata).filter(ClipMetadata.clip_id == clip_id).first()
        if existing and not overwrite:
            return existing

        # Fetch parent context
        cand = db.query(CandidateClip).filter(CandidateClip.id == clip.candidate_clip_id).first() if clip.candidate_clip_id else None
        moment = db.query(DetectedMoment).filter(DetectedMoment.id == clip.detected_moment_id).first() if clip.detected_moment_id else None
        rec = db.query(Recording).filter(Recording.id == clip.recording_id).first() if clip.recording_id else None

        category_key = self.resolve_category_key(clip, cand, moment)
        preset_pack = METADATA_PRESETS.get(category_key, METADATA_PRESETS["badass_action"])

        # 1. 5 Title Suggestions
        # Pick 5 distinct titles, incorporating focus keyword or clip specifics
        base_titles = list(preset_pack["titles"])
        if focus_keyword and len(focus_keyword.strip()) > 1:
            kw = focus_keyword.strip()
            base_titles.insert(0, f"GTA 6 {kw} Went CRAZY 🔥")
        
        # Ensure exactly 5 high quality title suggestions
        title_suggestions = base_titles[:5]
        active_title = title_suggestions[0]

        # 2. 3 Opening Hook Suggestions
        hook_suggestions = list(preset_pack["hooks"][:3])
        active_hook = hook_suggestions[0]

        # 3. Relevant Curated Hashtags (4-5 tags, avoiding hashtag spam)
        hashtags_list = list(preset_pack["hashtags"])
        if focus_keyword:
            clean_kw = "#" + re.sub(r'[^a-zA-Z0-9]', '', focus_keyword.title())
            if clean_kw not in hashtags_list and len(hashtags_list) < 6:
                hashtags_list.insert(2, clean_kw)
        active_hashtags = " ".join(hashtags_list)

        # 4. Thumbnail Text Suggestions (punchy 2-4 words)
        thumb_suggestions = list(preset_pack["thumbnail_texts"])
        active_thumb_text = thumb_suggestions[0]

        # 5. Pinned Comment Suggestions
        pinned_suggestions = list(preset_pack["pinned_comments"])
        active_pinned_comment = pinned_suggestions[0]

        # 6. Optimized YouTube Shorts Description
        duration_sec = round(clip.duration or 30.0, 1)
        desc_lines = [
            f"{preset_pack['description_intro']}",
            "",
            f"🎬 Captured in Vice City | {duration_sec}s YouTube Short",
            "🎮 Game: Grand Theft Auto VI (GTA 6)",
            "",
            "👉 Subscribe for daily GTA 6 gameplay clips, insane pursuits, and stunts!",
            "👍 Leave a like if you enjoyed this moment!",
            "",
            active_hashtags,
            "",
            "—",
            "Auto-clipped & edited with GTA CLIPFORGE AI"
        ]
        active_description = "\n".join(desc_lines)

        generation_context = {
            "category_key": category_key,
            "preset_name": clip.preset_name,
            "moment_type": str(clip.moment_type),
            "excitement_score": clip.excitement_score,
            "duration": duration_sec,
            "tone": tone,
            "focus_keyword": focus_keyword,
        }

        if existing:
            existing.title = active_title
            existing.description = active_description
            existing.hook = active_hook
            existing.hashtags = active_hashtags
            existing.thumbnail_text = active_thumb_text
            existing.pinned_comment = active_pinned_comment
            existing.title_suggestions = json.dumps(title_suggestions)
            existing.hook_suggestions = json.dumps(hook_suggestions)
            existing.hashtag_suggestions = json.dumps(hashtags_list)
            existing.thumbnail_text_suggestions = json.dumps(thumb_suggestions)
            existing.pinned_comment_suggestions = json.dumps(pinned_suggestions)
            existing.generation_context = json.dumps(generation_context)
            existing.is_user_edited = False
            db.commit()
            db.refresh(existing)
            return existing
        else:
            meta = ClipMetadata(
                clip_id=clip_id,
                title=active_title,
                description=active_description,
                hook=active_hook,
                hashtags=active_hashtags,
                thumbnail_text=active_thumb_text,
                pinned_comment=active_pinned_comment,
                title_suggestions=json.dumps(title_suggestions),
                hook_suggestions=json.dumps(hook_suggestions),
                hashtag_suggestions=json.dumps(hashtags_list),
                thumbnail_text_suggestions=json.dumps(thumb_suggestions),
                pinned_comment_suggestions=json.dumps(pinned_suggestions),
                generation_context=json.dumps(generation_context),
                is_user_edited=False,
            )
            db.add(meta)
            db.commit()
            db.refresh(meta)
            return meta

    def update_metadata(
        self,
        db: Session,
        clip_id: int,
        title: Optional[str] = None,
        description: Optional[str] = None,
        hook: Optional[str] = None,
        hashtags: Optional[str] = None,
        thumbnail_text: Optional[str] = None,
        pinned_comment: Optional[str] = None,
    ) -> ClipMetadata:
        """Update metadata with user edits."""
        meta = db.query(ClipMetadata).filter(ClipMetadata.clip_id == clip_id).first()
        if not meta:
            # Generate first then update
            meta = self.generate_metadata_for_clip(db, clip_id)

        if title is not None:
            meta.title = title.strip()
        if description is not None:
            meta.description = description.strip()
        if hook is not None:
            meta.hook = hook.strip()
        if hashtags is not None:
            meta.hashtags = hashtags.strip()
        if thumbnail_text is not None:
            meta.thumbnail_text = thumbnail_text.strip()
        if pinned_comment is not None:
            meta.pinned_comment = pinned_comment.strip()

        meta.is_user_edited = True
        db.commit()
        db.refresh(meta)
        return meta

    def build_youtube_publish_payload(self, db: Session, clip_id: int) -> Dict[str, Any]:
        """
        Prepares and validates metadata ready for YouTube Data API v3 publishing.
        """
        clip = db.query(Clip).filter(Clip.id == clip_id).first()
        if not clip:
            raise ValueError(f"Clip #{clip_id} not found.")

        meta = db.query(ClipMetadata).filter(ClipMetadata.clip_id == clip_id).first()
        if not meta:
            meta = self.generate_metadata_for_clip(db, clip_id)

        # Parse tags
        tags = [t.lstrip('#') for t in meta.hashtags.split() if t.startswith('#')]
        if "GTA6" not in tags:
            tags.insert(0, "GTA6")
        if "Shorts" not in tags:
            tags.append("Shorts")

        warnings = []
        if len(meta.title) > 100:
            warnings.append(f"Title is {len(meta.title)} characters (YouTube max is 100). Consider shortening.")
        elif len(meta.title) > 75:
            warnings.append(f"Title is {len(meta.title)} characters. Under 70 is recommended for mobile Shorts displays.")

        if len(meta.description) > 5000:
            warnings.append(f"Description is {len(meta.description)} characters (YouTube max is 5000).")

        tag_count = len(meta.hashtags.split())
        if tag_count > 15:
            warnings.append(f"Too many hashtags ({tag_count}). YouTube ignores videos with >15 hashtags.")

        is_valid = len(meta.title) <= 100 and len(meta.description) <= 5000 and len(meta.title) > 0

        return {
            "clip_id": clip_id,
            "title": meta.title,
            "description": meta.description,
            "tags": tags,
            "privacy_status": "public",
            "made_for_kids": False,
            "category_id": "20",  # Gaming
            "pinned_comment": meta.pinned_comment,
            "thumbnail_text": meta.thumbnail_text,
            "opening_hook": meta.hook,
            "video_path": clip.clip_path,
            "resolution": clip.resolution or "1080x1920",
            "aspect_ratio": clip.aspect_ratio or "9:16",
            "duration_seconds": clip.duration,
            "char_count_title": len(meta.title),
            "char_count_description": len(meta.description),
            "is_valid_for_youtube": is_valid,
            "validation_warnings": warnings,
        }

metadata_generator = MetadataGeneratorService()
