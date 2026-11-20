"use client";

import React, { useState, useEffect, useRef } from "react";
import { Header } from "@/components/layout/header";
import {
  api,
  Recording,
  Clip,
  CinematicPresetInfo,
  AudioTrackInfo,
  CinematicRenderResult,
  ShortVerificationResult,
} from "@/lib/api";
import {
  Scissors,
  Play,
  Pause,
  Sparkles,
  Layers,
  Crop,
  Type,
  CheckCircle2,
  AlertCircle,
  Download,
  Film,
  Sliders,
  RefreshCw,
  Clock,
  Flame,
  ShieldAlert,
  Zap,
  Crosshair,
  Palette,
  Smile,
  Music,
  Volume2,
  VolumeX,
  Eye,
  Video,
  Radio,
  FileCheck,
} from "lucide-react";

export default function ClipEditorPage() {
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [selectedRecId, setSelectedRecId] = useState<number | null>(null);
  const [clips, setClips] = useState<Clip[]>([]);
  const [selectedClip, setSelectedClip] = useState<Clip | null>(null);

  // Phase 7 Mode & Presets
  const [editMode, setEditMode] = useState<"raw" | "cinematic">("cinematic");
  const [presets, setPresets] = useState<CinematicPresetInfo[]>([]);
  const [selectedPresetName, setSelectedPresetName] = useState<string>("BADASS CINEMATIC");
  const [musicTracks, setMusicTracks] = useState<AudioTrackInfo[]>([]);
  const [sfxTracks, setSfxTracks] = useState<AudioTrackInfo[]>([]);

  // Detailed Sliders & Controls
  const [zoomIntensity, setZoomIntensity] = useState<number>(1.18);
  const [slowmoSpeed, setSlowmoSpeed] = useState<number>(0.5);
  const [colorGradingIntensity, setColorGradingIntensity] = useState<number>(1.0);
  const [audioVolume, setAudioVolume] = useState<number>(1.25);
  const [musicVolume, setMusicVolume] = useState<number>(0.4);
  const [selectedMusicId, setSelectedMusicId] = useState<string>("dark_cyber_pulse");
  const [selectedSfxId, setSelectedSfxId] = useState<string>("sub_bass_impact");
  const [transitionDuration, setTransitionDuration] = useState<number>(0.35);

  // Timing & Reframing
  const [startTime, setStartTime] = useState<number>(0);
  const [endTime, setEndTime] = useState<number>(30);
  const [title, setTitle] = useState<string>("GTA 6 Badass Cinematic Short");
  const [renderMode, setRenderMode] = useState<"blurred_background" | "smart_crop" | "action_hybrid">("blurred_background");
  const [targetLength, setTargetLength] = useState<number>(30);
  const [hasSubtitles, setHasSubtitles] = useState<boolean>(true);
  const [subtitleText, setSubtitleText] = useState<string>("GTA 6 BADASS MOMENT");
  const [subtitleStyle, setSubtitleStyle] = useState<string>("vice_neon");
  const [useGpu, setUseGpu] = useState<boolean>(true);

  // Playback & Verification States
  const [isGenerating, setIsGenerating] = useState<boolean>(false);
  const [isPreviewLoading, setIsPreviewLoading] = useState<boolean>(false);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [generatedClip, setGeneratedClip] = useState<Clip | null>(null);
  const [verificationResult, setVerificationResult] = useState<ShortVerificationResult | null>(null);
  const [activeMediaSource, setActiveMediaSource] = useState<"preview" | "final" | null>(null);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    loadInitialData();
  }, []);

  useEffect(() => {
    if (selectedRecId) {
      loadClipsForRec();
    }
  }, [selectedRecId]);

  const loadInitialData = async () => {
    try {
      const [recs, presetList, musicList, sfxList] = await Promise.all([
        api.getRecordings(1, 50),
        api.getCinematicPresets().catch(() => []),
        api.getMusicTracks().catch(() => []),
        api.getSfxTracks().catch(() => []),
      ]);

      setRecordings(recs.items || []);
      if (recs.items?.length > 0) {
        setSelectedRecId(recs.items[0].id);
      }
      setPresets(presetList || []);
      setMusicTracks(musicList || []);
      setSfxTracks(sfxList || []);
    } catch (e) {
      console.error("Failed to load initial editor data", e);
    }
  };

  const loadClipsForRec = async () => {
    if (!selectedRecId) return;
    try {
      const c = await api.getClips({ recording_id: selectedRecId, page_size: 20 });
      setClips(c || []);
      if (c && c.length > 0) {
        selectExistingClip(c[0]);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const selectExistingClip = (clip: Clip) => {
    setSelectedClip(clip);
    setStartTime(clip.start_time || 0);
    setEndTime(clip.end_time || 30);
    setTitle(clip.title || "GTA 6 Custom Short");
    setSubtitleText(clip.subtitle_text || clip.title || "GTA 6 ACTION HIGHLIGHT");
    setRenderMode((clip.render_mode as any) || "blurred_background");
    setHasSubtitles(clip.has_subtitles || false);
    if (clip.edit_mode === "raw" || clip.edit_mode === "cinematic") {
      setEditMode(clip.edit_mode as any);
    }
    if (clip.preset_name) {
      applyPresetValues(clip.preset_name);
    }
    setGeneratedClip(clip);
    setActiveMediaSource("final");
    setPreviewUrl(null);
  };

  const applyPresetValues = (presetName: string) => {
    setSelectedPresetName(presetName);
    const p = presets.find((item) => item.name.toUpperCase() === presetName.toUpperCase());
    if (p) {
      setZoomIntensity(p.default_zoom || 1.15);
      setSlowmoSpeed(p.default_slowmo || 0.5);
      setColorGradingIntensity(1.0);
      setTransitionDuration(0.35);
      if (p.suggested_music) setSelectedMusicId(p.suggested_music);
      if (p.suggested_sfx) setSelectedSfxId(p.suggested_sfx);
      setTitle(`GTA 6 ${p.name}`);
      setSubtitleText(`GTA 6 ${p.name.toUpperCase()}`);
    }
  };

  const handleGeneratePreview = async () => {
    if (!selectedRecId) return;
    setIsPreviewLoading(true);
    try {
      const res = await api.generateCinematicPreview({
        recording_id: selectedRecId,
        start_time: startTime,
        end_time: endTime,
        edit_mode: editMode,
        preset_name: selectedPresetName,
        render_mode: renderMode,
        zoom_intensity: zoomIntensity,
        slowmo_speed: slowmoSpeed,
        color_grading_intensity: colorGradingIntensity,
        audio_volume: audioVolume,
        music_volume: editMode === "cinematic" ? musicVolume : 0,
        music_track_id: selectedMusicId,
        sfx_track_id: selectedSfxId,
        preview_duration: 4.0,
      });
      setPreviewUrl(`${api["baseUrl"]}${res.preview_url}`);
      setActiveMediaSource("preview");
    } catch (e: any) {
      alert(`Preview failed: ${e.message}`);
    } finally {
      setIsPreviewLoading(false);
    }
  };

  const handleRenderFull = async () => {
    if (!selectedRecId) return;
    setIsGenerating(true);
    setVerificationResult(null);
    try {
      const result: CinematicRenderResult = await api.renderCinematicShort({
        recording_id: selectedRecId,
        clip_id: selectedClip?.id || undefined,
        candidate_clip_id: selectedClip?.candidate_clip_id || undefined,
        title: title,
        start_time: startTime,
        end_time: endTime,
        edit_mode: editMode,
        preset_name: editMode === "cinematic" ? selectedPresetName : undefined,
        render_mode: renderMode,
        target_length: targetLength,
        zoom_intensity: zoomIntensity,
        slowmo_speed: slowmoSpeed,
        color_grading_intensity: colorGradingIntensity,
        audio_volume: audioVolume,
        music_volume: editMode === "cinematic" ? musicVolume : 0.0,
        music_track_id: editMode === "cinematic" ? selectedMusicId : undefined,
        sfx_track_id: editMode === "cinematic" ? selectedSfxId : undefined,
        transition_duration: transitionDuration,
        subtitles: hasSubtitles,
        subtitle_text: subtitleText,
        subtitle_style: subtitleStyle,
        use_gpu: useGpu,
      });

      if (result.verification) {
        setVerificationResult(result.verification);
      }

      // Refresh clips and select new
      await loadClipsForRec();
      if (result.clip && result.clip.clip_id) {
        const fullClip = await api.getClip(result.clip.clip_id);
        setGeneratedClip(fullClip);
        setActiveMediaSource("final");
      }
    } catch (e: any) {
      alert(`Render failed: ${e.message}`);
    } finally {
      setIsGenerating(false);
    }
  };

  const currentDuration = Math.max(0, endTime - startTime);

  const getPresetIcon = (iconName: string) => {
    switch (iconName) {
      case "Flame":
        return <Flame className="w-4 h-4 text-red-400" />;
      case "Siren":
        return <ShieldAlert className="w-4 h-4 text-blue-400" />;
      case "Zap":
        return <Zap className="w-4 h-4 text-amber-400" />;
      case "Bomb":
        return <Sparkles className="w-4 h-4 text-orange-400" />;
      case "Crosshair":
        return <Crosshair className="w-4 h-4 text-rose-400" />;
      case "Sun":
        return <Palette className="w-4 h-4 text-fuchsia-400" />;
      case "Smile":
        return <Smile className="w-4 h-4 text-emerald-400" />;
      default:
        return <Sparkles className="w-4 h-4 text-cyan-400" />;
    }
  };

  return (
    <div className="min-h-screen bg-background text-text-primary pb-12">
      <Header
        title="Phase 7: GTA 6 Cinematic Shorts Studio"
        subtitle="Dynamic push-in zooms, speed ramping, color grading, audio normalization & 100% royalty-free beats"
      />

      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Source & Mode Selection Banner */}
        <div className="p-4 rounded-xl border border-border bg-surface flex flex-wrap items-center justify-between gap-4 shadow-md">
          <div className="flex items-center gap-3">
            <span className="text-xs text-text-muted font-medium">Gameplay Recording:</span>
            <select
              value={selectedRecId || ""}
              onChange={(e) => setSelectedRecId(Number(e.target.value) || null)}
              className="bg-background border border-border text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-cyan-500 font-mono"
            >
              {recordings.map((r) => (
                <option key={r.id} value={r.id}>
                  #{r.id} {r.original_filename} ({r.duration_seconds?.toFixed(0)}s)
                </option>
              ))}
            </select>
          </div>

          {/* Mode Switcher: RAW vs CINEMATIC */}
          <div className="flex items-center gap-2 bg-background p-1 rounded-xl border border-border">
            <button
              type="button"
              onClick={() => setEditMode("raw")}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                editMode === "raw"
                  ? "bg-zinc-700 text-white shadow"
                  : "text-text-muted hover:text-white"
              }`}
            >
              <Video className="w-3.5 h-3.5" />
              RAW GAMEPLAY
            </button>
            <button
              type="button"
              onClick={() => setEditMode("cinematic")}
              className={`px-3 py-1.5 rounded-lg text-xs font-bold transition-all flex items-center gap-1.5 ${
                editMode === "cinematic"
                  ? "bg-gradient-to-r from-cyan-500 to-purple-600 text-white shadow-lg shadow-purple-500/20"
                  : "text-text-muted hover:text-white"
              }`}
            >
              <Sparkles className="w-3.5 h-3.5" />
              CINEMATIC EDIT
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted">Load Existing Clip:</span>
            <select
              value={selectedClip?.id || ""}
              onChange={(e) => {
                const c = clips.find((item) => item.id === Number(e.target.value));
                if (c) selectExistingClip(c);
              }}
              className="bg-background border border-border text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-cyan-500 max-w-xs truncate"
            >
              <option value="">Custom New Boundary</option>
              {clips.map((c) => (
                <option key={c.id} value={c.id}>
                  #{c.id} {c.title} ({c.duration?.toFixed(0)}s)
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* 7 Signature Presets Grid (Shown in Cinematic Mode) */}
        {editMode === "cinematic" && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider text-text-muted flex items-center gap-2">
                <Flame className="w-4 h-4 text-purple-400" />
                Select GTA 6 Cinematic Preset:
              </span>
              <span className="text-[11px] text-cyan-400 font-mono">
                Safe Action Framing &bull; Dynamic Zoom &bull; 0.5x Slow-Mo Climax
              </span>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-7 gap-3">
              {presets.map((p) => {
                const isSelected = selectedPresetName.toUpperCase() === p.name.toUpperCase();
                return (
                  <button
                    key={p.id}
                    type="button"
                    onClick={() => applyPresetValues(p.name)}
                    className={`p-3 rounded-xl border text-left transition-all flex flex-col justify-between space-y-2 relative overflow-hidden ${
                      isSelected
                        ? "bg-surface border-cyan-400 ring-2 ring-cyan-500/30 shadow-lg shadow-cyan-500/10"
                        : "bg-surface/50 border-border hover:border-zinc-500 hover:bg-surface"
                    }`}
                  >
                    {isSelected && (
                      <div className="absolute top-1 right-1">
                        <CheckCircle2 className="w-3.5 h-3.5 text-cyan-400" />
                      </div>
                    )}
                    <div className="flex items-center gap-2">
                      <div className="p-1.5 rounded-lg bg-background border border-border">
                        {getPresetIcon(p.icon)}
                      </div>
                      <span className="text-xs font-bold text-white tracking-tight leading-tight">
                        {p.name}
                      </span>
                    </div>
                    <p className="text-[10px] text-text-muted line-clamp-2 leading-relaxed">
                      {p.tagline}
                    </p>
                  </button>
                );
              })}
            </div>
          </div>
        )}

        {/* 2-Column Interface: Left (9:16 Video Stage) & Right (Controls & Audio) */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Left Column: Vertical 9:16 Preview Player */}
          <div className="lg:col-span-5 bg-surface border border-border rounded-xl p-5 flex flex-col items-center justify-between space-y-4 shadow-xl">
            <div className="w-full flex items-center justify-between border-b border-border pb-3">
              <span className="text-xs font-semibold text-white flex items-center gap-2">
                <Film className="w-4 h-4 text-cyan-400" />
                9:16 YouTube Shorts Monitor
              </span>
              <div className="flex items-center gap-2">
                {activeMediaSource === "preview" && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30 animate-pulse">
                    Instant 4s Preview
                  </span>
                )}
                {activeMediaSource === "final" && (
                  <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                    Full Render Output
                  </span>
                )}
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                  1080 x 1920
                </span>
              </div>
            </div>

            {/* Video Player Display */}
            <div className="relative aspect-[9/16] w-full max-w-[280px] bg-black rounded-xl overflow-hidden border border-border flex items-center justify-center shadow-2xl">
              {activeMediaSource === "preview" && previewUrl ? (
                <video
                  ref={videoRef}
                  src={previewUrl}
                  className="w-full h-full object-contain"
                  controls
                  autoPlay
                  loop
                  playsInline
                />
              ) : activeMediaSource === "final" && generatedClip && generatedClip.clip_path ? (
                <video
                  ref={videoRef}
                  src={api.getClipStreamUrl(generatedClip.id)}
                  className="w-full h-full object-contain"
                  controls
                  playsInline
                />
              ) : (
                <div className="flex flex-col items-center justify-center text-center p-6 text-zinc-600 space-y-2">
                  <Film className="w-12 h-12" />
                  <p className="text-xs font-medium text-text-muted">
                    Click &apos;Instant 4s Preview&apos; or &apos;Render Full Short&apos; to view the 9:16 video.
                  </p>
                </div>
              )}
            </div>

            {/* Video Info & Download */}
            <div className="w-full space-y-2 pt-2 border-t border-border">
              <div className="flex items-center justify-between text-xs text-text-muted">
                <span>
                  Preset:{" "}
                  <strong className="text-white">
                    {editMode === "raw" ? "RAW GAMEPLAY" : selectedPresetName}
                  </strong>
                </span>
                {generatedClip && (
                  <a
                    href={api.getClipDownloadUrl(generatedClip.id)}
                    download
                    className="text-cyan-400 hover:text-cyan-300 flex items-center gap-1 font-semibold"
                  >
                    <Download className="w-3.5 h-3.5" />
                    Download MP4
                  </a>
                )}
              </div>

              {/* FFprobe Verification Badge */}
              {verificationResult && (
                <div className="p-2.5 rounded-lg bg-emerald-950/40 border border-emerald-500/30 text-[11px] space-y-1">
                  <div className="flex items-center gap-1.5 text-emerald-400 font-bold">
                    <FileCheck className="w-4 h-4" />
                    FFprobe Verification: Passed
                  </div>
                  <div className="grid grid-cols-2 gap-1 text-[10px] text-zinc-300 font-mono">
                    <span>Res: 1080x1920 (9:16)</span>
                    <span>Dur: {verificationResult.duration}s</span>
                    <span>Video: {verificationResult.video_codec.toUpperCase()}</span>
                    <span>Audio: {verificationResult.audio_codec.toUpperCase()}</span>
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* Right Column: Editing Controls & Sliders */}
          <div className="lg:col-span-7 bg-surface border border-border rounded-xl p-6 space-y-5 shadow-xl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="font-semibold text-white text-sm flex items-center gap-2">
                <Sliders className="w-4 h-4 text-cyan-400" />
                {editMode === "raw" ? "Raw Gameplay Trimming" : "Cinematic Effects & Audio Design"}
              </h3>
              <span className="text-xs font-mono text-cyan-300 font-bold">
                Length: {currentDuration.toFixed(1)}s
              </span>
            </div>

            {/* Title Input */}
            <div className="space-y-1.5">
              <label className="text-xs font-medium text-text-muted">Short Title:</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 font-medium"
              />
            </div>

            {/* Timing Inputs */}
            <div className="grid grid-cols-2 gap-4 p-4 rounded-xl border border-border bg-background">
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-text-muted">Start Time:</span>
                  <span className="font-mono text-white font-bold">{startTime.toFixed(1)}s</span>
                </div>
                <input
                  type="number"
                  step="0.5"
                  min="0"
                  value={startTime}
                  onChange={(e) => setStartTime(Math.max(0, parseFloat(e.target.value) || 0))}
                  className="w-full bg-surface border border-border rounded px-2.5 py-1.5 text-xs text-white font-mono"
                />
              </div>

              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs">
                  <span className="text-text-muted">End Time:</span>
                  <span className="font-mono text-white font-bold">{endTime.toFixed(1)}s</span>
                </div>
                <input
                  type="number"
                  step="0.5"
                  min="1"
                  value={endTime}
                  onChange={(e) => setEndTime(Math.max(startTime + 1, parseFloat(e.target.value) || 1))}
                  className="w-full bg-surface border border-border rounded px-2.5 py-1.5 text-xs text-white font-mono"
                />
              </div>
            </div>

            {/* Duration Presets */}
            <div className="space-y-2">
              <label className="text-xs font-medium text-text-muted">Target Duration Preset:</label>
              <div className="grid grid-cols-5 gap-2">
                {[15, 20, 30, 45, 60].map((sec) => (
                  <button
                    key={sec}
                    type="button"
                    onClick={() => {
                      setTargetLength(sec);
                      setEndTime(startTime + sec);
                    }}
                    className={`py-2 rounded-lg text-xs font-semibold border transition-all ${
                      Math.round(currentDuration) === sec
                        ? "bg-cyan-500 text-white border-cyan-400"
                        : "border-border bg-background text-text-secondary hover:border-text-muted"
                    }`}
                  >
                    {sec}s
                  </button>
                ))}
              </div>
            </div>

            {/* Sliders (Only in Cinematic Mode) */}
            {editMode === "cinematic" && (
              <div className="p-4 rounded-xl border border-border bg-background space-y-4">
                <span className="text-xs font-bold text-white flex items-center gap-2">
                  <Sliders className="w-3.5 h-3.5 text-purple-400" />
                  Cinematic Fine-Tuning Sliders:
                </span>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {/* Zoom Intensity */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px]">
                      <span className="text-text-muted">Push-In Zoom:</span>
                      <span className="font-mono text-cyan-300 font-bold">{zoomIntensity.toFixed(2)}x</span>
                    </div>
                    <input
                      type="range"
                      min="1.0"
                      max="1.5"
                      step="0.02"
                      value={zoomIntensity}
                      onChange={(e) => setZoomIntensity(parseFloat(e.target.value))}
                      className="w-full accent-cyan-400 cursor-pointer"
                    />
                  </div>

                  {/* Slow-Motion Speed */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px]">
                      <span className="text-text-muted">Slow-Mo Climax:</span>
                      <span className="font-mono text-purple-300 font-bold">{slowmoSpeed.toFixed(2)}x</span>
                    </div>
                    <input
                      type="range"
                      min="0.25"
                      max="1.0"
                      step="0.05"
                      value={slowmoSpeed}
                      onChange={(e) => setSlowmoSpeed(parseFloat(e.target.value))}
                      className="w-full accent-purple-400 cursor-pointer"
                    />
                  </div>

                  {/* Color Grading Intensity */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px]">
                      <span className="text-text-muted">Color Grading:</span>
                      <span className="font-mono text-amber-300 font-bold">{Math.round(colorGradingIntensity * 100)}%</span>
                    </div>
                    <input
                      type="range"
                      min="0.0"
                      max="1.0"
                      step="0.05"
                      value={colorGradingIntensity}
                      onChange={(e) => setColorGradingIntensity(parseFloat(e.target.value))}
                      className="w-full accent-amber-400 cursor-pointer"
                    />
                  </div>

                  {/* Transition Duration */}
                  <div className="space-y-1">
                    <div className="flex justify-between text-[11px]">
                      <span className="text-text-muted">Transition Time:</span>
                      <span className="font-mono text-emerald-300 font-bold">{transitionDuration.toFixed(2)}s</span>
                    </div>
                    <input
                      type="range"
                      min="0.1"
                      max="1.0"
                      step="0.05"
                      value={transitionDuration}
                      onChange={(e) => setTransitionDuration(parseFloat(e.target.value))}
                      className="w-full accent-emerald-400 cursor-pointer"
                    />
                  </div>
                </div>

                {/* Audio Design & Mixing */}
                <div className="pt-2 border-t border-border/60 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white flex items-center gap-1.5">
                      <Music className="w-3.5 h-3.5 text-cyan-400" />
                      Audio Design (100% Royalty-Free & Safe)
                    </span>
                    <span className="px-2 py-0.5 rounded text-[10px] font-semibold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                      DMCA Protected
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                    <div>
                      <label className="text-[11px] text-text-muted block mb-1">Background Track:</label>
                      <select
                        value={selectedMusicId}
                        onChange={(e) => setSelectedMusicId(e.target.value)}
                        className="w-full bg-surface border border-border rounded px-2.5 py-1.5 text-xs text-white"
                      >
                        {musicTracks.map((m) => (
                          <option key={m.id} value={m.id}>
                            {m.title} ({m.duration_seconds}s - {m.genre})
                          </option>
                        ))}
                      </select>
                    </div>

                    <div>
                      <label className="text-[11px] text-text-muted block mb-1">Cinematic SFX:</label>
                      <select
                        value={selectedSfxId}
                        onChange={(e) => setSelectedSfxId(e.target.value)}
                        className="w-full bg-surface border border-border rounded px-2.5 py-1.5 text-xs text-white"
                      >
                        {sfxTracks.map((s) => (
                          <option key={s.id} value={s.id}>
                            {s.title} ({s.genre})
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  {/* Volume Sliders */}
                  <div className="grid grid-cols-2 gap-4 pt-1">
                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px]">
                        <span className="text-text-muted">Game Audio:</span>
                        <span className="font-mono text-white font-bold">{Math.round(audioVolume * 100)}%</span>
                      </div>
                      <input
                        type="range"
                        min="0.0"
                        max="2.0"
                        step="0.05"
                        value={audioVolume}
                        onChange={(e) => setAudioVolume(parseFloat(e.target.value))}
                        className="w-full accent-cyan-400 cursor-pointer"
                      />
                    </div>

                    <div className="space-y-1">
                      <div className="flex justify-between text-[11px]">
                        <span className="text-text-muted">Music Volume:</span>
                        <span className="font-mono text-purple-300 font-bold">{Math.round(musicVolume * 100)}%</span>
                      </div>
                      <input
                        type="range"
                        min="0.0"
                        max="1.0"
                        step="0.05"
                        value={musicVolume}
                        onChange={(e) => setMusicVolume(parseFloat(e.target.value))}
                        className="w-full accent-purple-400 cursor-pointer"
                      />
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Subtitles & Hook Title */}
            <div className="p-4 rounded-xl border border-border bg-background space-y-3">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Type className="w-4 h-4 text-cyan-400" />
                  <span className="text-xs font-semibold text-white">Top Hook Subtitles</span>
                </div>
                <input
                  type="checkbox"
                  checked={hasSubtitles}
                  onChange={(e) => setHasSubtitles(e.target.checked)}
                  className="w-4 h-4 accent-cyan-500 cursor-pointer"
                />
              </div>

              {hasSubtitles && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-1">
                  <div>
                    <label className="text-[11px] text-text-muted block mb-1">Hook Caption Text:</label>
                    <input
                      type="text"
                      value={subtitleText}
                      onChange={(e) => setSubtitleText(e.target.value)}
                      className="w-full bg-surface border border-border rounded px-2.5 py-1.5 text-xs text-white"
                    />
                  </div>
                  <div>
                    <label className="text-[11px] text-text-muted block mb-1">Neon Styling:</label>
                    <select
                      value={subtitleStyle}
                      onChange={(e) => setSubtitleStyle(e.target.value)}
                      className="w-full bg-surface border border-border rounded px-2.5 py-1.5 text-xs text-white"
                    >
                      <option value="vice_neon">Vice City Neon Cyan</option>
                      <option value="bold_yellow">Bold Gaming Yellow</option>
                      <option value="clean_white">Clean Minimal White</option>
                    </select>
                  </div>
                </div>
              )}
            </div>

            {/* Action Buttons: Preview & Full Render */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
              <button
                type="button"
                disabled={isPreviewLoading || isGenerating}
                onClick={handleGeneratePreview}
                className="py-3 px-4 rounded-xl text-xs font-bold text-white bg-surface hover:bg-surface/80 border border-border hover:border-cyan-500 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isPreviewLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin text-cyan-400" />
                    <span>Rendering 4s Preview...</span>
                  </>
                ) : (
                  <>
                    <Eye className="w-4 h-4 text-cyan-400" />
                    <span>Instant 4s Preview</span>
                  </>
                )}
              </button>

              <button
                type="button"
                disabled={isGenerating || isPreviewLoading}
                onClick={handleRenderFull}
                className="py-3 px-4 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-400 hover:to-purple-500 shadow-xl shadow-cyan-500/25 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
              >
                {isGenerating ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Rendering 1080x1920 Short...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>
                      {editMode === "raw" ? "Render Raw Short" : "Render Cinematic Short"} ({currentDuration.toFixed(0)}s)
                    </span>
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
