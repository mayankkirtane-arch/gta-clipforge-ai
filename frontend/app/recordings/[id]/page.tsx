"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ArrowLeft,
  Play,
  Pause,
  RotateCcw,
  Sparkles,
  Zap,
  Film,
  Volume2,
  VolumeX,
  Flame,
  Layers,
  Clock,
  HardDrive,
  Cpu,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Sliders,
  Scissors,
  Eye,
  ChevronRight,
  Maximize2,
} from "lucide-react";
import {
  api,
  Recording,
  RecordingAnalysis,
  TimelineSegment,
} from "@/lib/api";
import { formatBytes, formatDuration } from "@/lib/utils";

const statusVariants: Record<string, "default" | "warning" | "success" | "error"> = {
  pending: "default",
  processing: "warning",
  completed: "success",
  failed: "error",
};

export default function RecordingAnalysisPage() {
  const params = useParams();
  const router = useRouter();
  const recordingId = Number(params.id);

  const [recording, setRecording] = useState<Recording | null>(null);
  const [analysis, setAnalysis] = useState<RecordingAnalysis | null>(null);
  const [timeline, setTimeline] = useState<TimelineSegment[]>([]);
  const [timelineTotal, setTimelineTotal] = useState(0);
  const [timelinePage, setTimelinePage] = useState(1);
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);

  // Video Player state
  const videoRef = useRef<HTMLVideoElement>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [useProxy, setUseProxy] = useState(false);
  const [selectedFilter, setSelectedFilter] = useState<"all" | "cuts" | "peaks" | "exciting">("all");

  const loadData = useCallback(async () => {
    if (!recordingId || isNaN(recordingId)) return;
    try {
      const [recData, analysisData] = await Promise.all([
        api.getRecording(recordingId),
        api.getRecordingAnalysis(recordingId),
      ]);
      setRecording(recData);
      setAnalysis(analysisData);
      if (analysisData.has_proxy) {
        setUseProxy(true);
      }
    } catch (err) {
      console.error("Failed to load recording analysis data", err);
    } finally {
      setLoading(false);
    }
  }, [recordingId]);

  const loadTimeline = useCallback(async () => {
    if (!recordingId) return;
    try {
      const onlyPeaks = selectedFilter === "peaks";
      const onlyCuts = selectedFilter === "cuts";
      const res = await api.getRecordingTimeline(recordingId, timelinePage, 60, onlyPeaks, onlyCuts);
      
      let items = res.items;
      if (selectedFilter === "exciting") {
        items = items.filter((s) => s.excitement_score >= 65);
      }
      setTimeline(items);
      setTimelineTotal(res.total);
    } catch {}
  }, [recordingId, timelinePage, selectedFilter]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  useEffect(() => {
    loadTimeline();
  }, [loadTimeline]);

  // Periodic polling when analysis is in processing status
  useEffect(() => {
    if (analysis?.status !== "processing") return;
    const interval = setInterval(() => {
      loadData();
      loadTimeline();
    }, 3000);
    return () => clearInterval(interval);
  }, [analysis?.status, loadData, loadTimeline]);

  // Video time update listener
  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const seekTo = (seconds: number) => {
    if (videoRef.current) {
      videoRef.current.currentTime = seconds;
      videoRef.current.play().catch(() => {});
      setIsPlaying(true);
    }
  };

  const handleTriggerAnalysis = async (forceReanalyze = false) => {
    setAnalyzing(true);
    try {
      await api.triggerAnalysis(recordingId, forceReanalyze);
      await loadData();
    } catch (err: any) {
      alert(err.message || "Failed to trigger analysis");
    } finally {
      setAnalyzing(false);
    }
  };

  if (loading && !recording) {
    return (
      <div className="p-8 space-y-4 max-w-7xl">
        <div className="h-8 bg-surface-2 rounded w-60 animate-pulse" />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 aspect-video bg-surface-2 rounded-xl animate-pulse" />
          <div className="space-y-4">
            <div className="h-40 bg-surface-2 rounded-xl animate-pulse" />
            <div className="h-40 bg-surface-2 rounded-xl animate-pulse" />
          </div>
        </div>
      </div>
    );
  }

  if (!recording) {
    return (
      <div className="p-8 text-center">
        <AlertTriangle className="w-12 h-12 text-error mx-auto mb-3" />
        <h3 className="text-base font-semibold text-text-primary">Recording not found</h3>
        <Link href="/recordings" className="mt-4 inline-block text-xs text-primary-light hover:underline">
          &larr; Back to Recordings
        </Link>
      </div>
    );
  }

  const duration = recording.duration_seconds || 1;
  const progressRatio = duration > 0 ? (currentTime / duration) * 100 : 0;
  const waveform = analysis?.waveform_data || [];

  return (
    <div>
      <Header
        title={recording.original_filename}
        subtitle={`Gameplay Video Analysis & Timeline — ${recording.resolution || "1080p"} @ ${recording.fps || 60} FPS (${formatDuration(duration)})`}
      />

      <div className="p-6 space-y-6 max-w-7xl">
        {/* Top Navigation & Status Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-4 rounded-xl bg-surface-2 border border-border">
          <div className="flex items-center gap-3">
            <Link
              href="/recordings"
              className="p-2 rounded-lg bg-surface-3 hover:bg-surface-2 text-text-muted hover:text-text-primary transition-colors"
            >
              <ArrowLeft className="w-4 h-4" />
            </Link>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-text-primary truncate max-w-md">
                  {recording.original_filename}
                </span>
                <Badge variant={statusVariants[analysis?.status || "pending"] || "default"}>
                  {analysis?.status || "pending"}
                </Badge>
                {analysis?.gpu_accelerated && (
                  <Badge variant="info">
                    <Cpu className="w-3 h-3 mr-1" /> NVENC GPU
                  </Badge>
                )}
              </div>
              <p className="text-xs text-text-muted mt-0.5 font-mono">
                {recording.file_path}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link href="/detected-moments">
              <Button
                variant="primary"
                size="sm"
                className="bg-gradient-to-r from-primary to-electric text-white shadow-md shadow-primary/20"
              >
                <Zap className="w-3.5 h-3.5 mr-1.5 fill-current" />
                Detected Moments
              </Button>
            </Link>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleTriggerAnalysis(false)}
              disabled={analyzing || analysis?.status === "processing"}
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${analysis?.status === "processing" ? "animate-spin" : ""}`} />
              {analysis?.status === "processing" ? "Processing..." : "Resume / Run Analysis"}
            </Button>
            <Button
              variant="secondary"
              size="sm"
              onClick={() => handleTriggerAnalysis(true)}
              disabled={analyzing || analysis?.status === "processing"}
              title="Clear checkpoints and re-process from scratch"
            >
              <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> Re-analyze (Full)
            </Button>
          </div>
        </div>

        {/* Processing Progress Notification if Active */}
        {analysis?.status === "processing" && (
          <div className="p-4 rounded-xl bg-primary/10 border border-primary/30 space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span className="font-semibold text-primary-light flex items-center gap-2">
                <RefreshCw className="w-4 h-4 animate-spin" />
                Chunk-based Video Engine Processing in progress...
              </span>
              <span className="font-mono text-primary-light font-bold">
                {analysis.progress.toFixed(1)}% (Chunk {analysis.current_chunk} of {analysis.total_chunks})
              </span>
            </div>
            <div className="w-full bg-surface-3 rounded-full h-2 overflow-hidden">
              <div
                className="bg-gradient-to-r from-primary to-electric h-2 rounded-full transition-all duration-500"
                style={{ width: `${analysis.progress}%` }}
              />
            </div>
            <p className="text-[11px] text-text-muted">
              Processing 5-minute chunks without loading the entire video into RAM. Checkpoints are saved automatically after each chunk.
            </p>
          </div>
        )}

        {/* TOP SECTION: VIDEO PREVIEW + METRICS GRID */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* VIDEO PLAYER */}
          <div className="lg:col-span-2 space-y-3">
            <Card className="overflow-hidden">
              <div className="relative aspect-video bg-black flex items-center justify-center">
                <video
                  ref={videoRef}
                  className="w-full h-full object-contain"
                  src={
                    useProxy && analysis?.has_proxy
                      ? `${api.baseUrl}/api/recordings/${recording.id}/proxy`
                      : `${api.baseUrl}/api/recordings/${recording.id}/stream`
                  }
                  onTimeUpdate={handleTimeUpdate}
                  onPlay={() => setIsPlaying(true)}
                  onPause={() => setIsPlaying(false)}
                  controls
                />
              </div>

              {/* Player Sub-Bar */}
              <div className="p-3 bg-surface-2 flex items-center justify-between text-xs border-t border-border/40">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-text-primary">
                    {formatDuration(currentTime)} / {formatDuration(duration)}
                  </span>
                  <span className="text-text-muted text-[11px]">
                    Current Frame: {Math.floor(currentTime * (recording.fps || 30))}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {analysis?.has_proxy && (
                    <button
                      onClick={() => setUseProxy(!useProxy)}
                      className={`px-2 py-1 rounded text-[11px] font-semibold transition-colors border ${
                        useProxy
                          ? "bg-electric/20 border-electric text-electric"
                          : "bg-surface-3 border-border text-text-muted hover:text-text-primary"
                      }`}
                      title="Switch between Original 4K/1080p stream and low-res 720p proxy"
                    >
                      {useProxy ? "Proxy: 720p (Fast Scrub)" : "Original: Direct Stream"}
                    </button>
                  )}
                </div>
              </div>
            </Card>
          </div>

          {/* ENGINE METRICS & DETECTION SUMMARY */}
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Engine Detection Metrics</CardTitle>
                <Sparkles className="w-4 h-4 text-primary-light" />
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="p-2.5 rounded-lg bg-surface-2 border border-border/40">
                    <span className="text-[11px] text-text-muted block">Scenes Detected</span>
                    <span className="text-base font-bold text-text-primary font-mono mt-0.5 block">
                      {analysis?.total_scenes || 0}
                    </span>
                    <span className="text-[10px] text-primary-light">PySceneDetect cuts</span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-surface-2 border border-border/40">
                    <span className="text-[11px] text-text-muted block">Keyframes</span>
                    <span className="text-base font-bold text-text-primary font-mono mt-0.5 block">
                      {analysis?.total_keyframes || 0}
                    </span>
                    <span className="text-[10px] text-text-muted">10s intervals</span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-surface-2 border border-border/40">
                    <span className="text-[11px] text-text-muted block">Audio Peaks</span>
                    <span className="text-base font-bold text-warning font-mono mt-0.5 block">
                      {analysis?.audio_peaks_count || 0}
                    </span>
                    <span className="text-[10px] text-warning/80">Gunfights & crashes</span>
                  </div>

                  <div className="p-2.5 rounded-lg bg-surface-2 border border-border/40">
                    <span className="text-[11px] text-text-muted block">Black Screens</span>
                    <span className="text-base font-bold text-text-secondary font-mono mt-0.5 block">
                      {analysis?.black_frames_count || 0}
                    </span>
                    <span className="text-[10px] text-text-muted">Loading/respawn fades</span>
                  </div>
                </div>

                <div className="p-3 rounded-lg bg-surface-2 border border-border/40 space-y-1.5 text-xs">
                  <div className="flex justify-between items-center text-text-muted text-[11px]">
                    <span>Chunk Size</span>
                    <span className="text-text-primary font-mono">{analysis?.chunk_duration_sec || 300}s (5 min)</span>
                  </div>
                  <div className="flex justify-between items-center text-text-muted text-[11px]">
                    <span>Hardware Encoding</span>
                    <span className="text-text-primary font-mono">
                      {analysis?.gpu_accelerated ? "NVIDIA NVENC (GPU)" : "CPU x264 Fallback"}
                    </span>
                  </div>
                  <div className="flex justify-between items-center text-text-muted text-[11px]">
                    <span>Extracted Audio</span>
                    <span className="text-text-primary font-mono">16kHz PCM WAV</span>
                  </div>
                </div>
              </CardContent>
            </Card>

            {/* QUICK ACTIONS FOR CLIP GENERATION */}
            <Card>
              <CardHeader>
                <CardTitle>Next Pipeline Actions</CardTitle>
                <Flame className="w-4 h-4 text-warning" />
              </CardHeader>
              <CardContent className="space-y-2">
                <Button
                  className="w-full text-xs justify-start"
                  variant="primary"
                  onClick={() => router.push("/detected-moments")}
                >
                  <Sparkles className="w-3.5 h-3.5 mr-2" />
                  View Detected AI Moments
                </Button>
                <Button
                  className="w-full text-xs justify-start"
                  variant="outline"
                  onClick={() => router.push("/generated-shorts")}
                >
                  <Scissors className="w-3.5 h-3.5 mr-2" />
                  Generate 9:16 Shorts
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* AUDIO WAVEFORM & INTERACTIVE TIMELINE SCRUBBER */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-2">
                <Volume2 className="w-4 h-4 text-primary-light" />
                <CardTitle>Audio Waveform & Excitement Timeline</CardTitle>
              </div>
              <span className="text-[11px] text-text-muted">
                Click anywhere on the waveform or timeline track to seek the video
              </span>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {/* Visual Waveform Canvas / Bars */}
            <div
              className="relative h-24 bg-surface-2 rounded-lg p-2 overflow-hidden cursor-pointer select-none group border border-border/40"
              onClick={(e) => {
                const rect = e.currentTarget.getBoundingClientRect();
                const clickX = e.clientX - rect.left;
                const ratio = Math.max(0, Math.min(1, clickX / rect.width));
                seekTo(ratio * duration);
              }}
            >
              {/* Waveform Bars */}
              <div className="w-full h-full flex items-end gap-[1px]">
                {waveform.length > 0 ? (
                  waveform.map((val, idx) => {
                    const isPeak = val >= 0.75;
                    return (
                      <div
                        key={idx}
                        className={`flex-1 rounded-t transition-all ${
                          isPeak
                            ? "bg-warning hover:bg-warning/80"
                            : "bg-primary-light/60 hover:bg-primary-light"
                        }`}
                        style={{ height: `${Math.max(8, val * 100)}%` }}
                        title={`Sample ${idx}: ${(val * 100).toFixed(0)}% amplitude`}
                      />
                    );
                  })
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-xs text-text-muted">
                    {analysis?.status === "processing" ? "Extracting audio waveform..." : "Audio waveform will appear once analysis runs."}
                  </div>
                )}
              </div>

              {/* Scrubber Playhead Line */}
              <div
                className="absolute top-0 bottom-0 w-0.5 bg-electric z-10 pointer-events-none transition-all duration-100 shadow-[0_0_8px_rgba(0,240,255,0.8)]"
                style={{ left: `${progressRatio}%` }}
              >
                <div className="w-2.5 h-2.5 -ml-1 -mt-0.5 bg-electric rounded-full" />
              </div>
            </div>

            {/* Timeline Track with Scene Markers */}
            <div className="space-y-1.5">
              <div className="flex justify-between text-[11px] font-mono text-text-muted">
                <span>00:00:00</span>
                <span className="text-electric font-semibold">{formatDuration(currentTime)}</span>
                <span>{formatDuration(duration)}</span>
              </div>

              {/* Marker Track */}
              <div
                className="relative h-6 bg-surface-3 rounded-md overflow-hidden cursor-pointer border border-border/50"
                onClick={(e) => {
                  const rect = e.currentTarget.getBoundingClientRect();
                  const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width));
                  seekTo(ratio * duration);
                }}
              >
                {/* Scene markers */}
                {analysis?.scenes_data?.map((sc, i) => {
                  const leftPct = (sc.start_time / duration) * 100;
                  return (
                    <div
                      key={i}
                      className="absolute top-0 bottom-0 w-1 bg-primary border-r border-black/40 z-0"
                      style={{ left: `${leftPct}%` }}
                      title={`Scene ${sc.scene_number} @ ${formatDuration(sc.start_time)}`}
                    />
                  );
                })}

                {/* Progress bar overlay */}
                <div
                  className="absolute top-0 bottom-0 left-0 bg-primary/20 pointer-events-none"
                  style={{ width: `${progressRatio}%` }}
                />

                {/* Playhead marker */}
                <div
                  className="absolute top-0 bottom-0 w-1 bg-electric z-10 pointer-events-none"
                  style={{ left: `${progressRatio}%` }}
                />
              </div>

              <div className="flex items-center gap-4 text-[10px] text-text-muted pt-1">
                <span className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded bg-primary" /> Scene Cut (PySceneDetect)
                </span>
                <span className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded bg-warning" /> Audio Peak (Excitement)
                </span>
                <span className="flex items-center gap-1">
                  <div className="w-2 h-2 rounded bg-electric" /> Video Playhead
                </span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* KEYFRAME SCRUBBER & TIMELINE SEGMENTS GALLERY */}
        <Card>
          <CardHeader>
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 w-full">
              <div className="flex items-center gap-2">
                <Layers className="w-4 h-4 text-primary-light" />
                <CardTitle>Timeline Keyframes & Moments ({timelineTotal})</CardTitle>
              </div>

              {/* Filter Chips */}
              <div className="flex items-center gap-1.5 flex-wrap">
                {[
                  { id: "all", label: "All Keyframes" },
                  { id: "cuts", label: "Scene Cuts" },
                  { id: "peaks", label: "Audio Peaks" },
                  { id: "exciting", label: "High Excitement (>65)" },
                ].map((f) => (
                  <button
                    key={f.id}
                    onClick={() => {
                      setSelectedFilter(f.id as any);
                      setTimelinePage(1);
                    }}
                    className={`px-2.5 py-1 rounded-full text-xs font-semibold transition-all ${
                      selectedFilter === f.id
                        ? "bg-primary text-white"
                        : "bg-surface-2 text-text-muted hover:bg-surface-3 hover:text-text-primary"
                    }`}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {timeline.length === 0 ? (
              <div className="text-center py-12 text-text-muted">
                <Film className="w-10 h-10 mx-auto mb-2 opacity-30" />
                <p className="text-sm font-medium">No timeline segments matched this filter</p>
                <p className="text-xs mt-1">Run video engine processing to extract keyframes and detect moments.</p>
              </div>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-3">
                {timeline.map((seg) => {
                  const isCurrent = Math.abs(currentTime - seg.timestamp) < 5.0;
                  return (
                    <div
                      key={seg.id}
                      onClick={() => seekTo(seg.timestamp)}
                      className={`group rounded-lg overflow-hidden border bg-surface-2 cursor-pointer transition-all hover:scale-[1.02] hover:border-primary/80 ${
                        isCurrent ? "border-electric ring-1 ring-electric" : "border-border/60"
                      }`}
                    >
                      {/* Keyframe image */}
                      <div className="relative aspect-video bg-black overflow-hidden">
                        {seg.keyframe_url ? (
                          <img
                            src={`${api.baseUrl}${seg.keyframe_url}`}
                            alt={seg.timestamp_formatted}
                            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                            loading="lazy"
                          />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-xs text-text-muted">
                            <Film className="w-6 h-6 opacity-30" />
                          </div>
                        )}

                        {/* Timestamp tag */}
                        <div className="absolute bottom-1 right-1 px-1.5 py-0.5 rounded bg-black/80 font-mono text-[10px] text-white">
                          {seg.timestamp_formatted}
                        </div>

                        {/* Excitement Badge */}
                        <div className="absolute top-1 left-1 px-1.5 py-0.5 rounded bg-black/80 text-[10px] font-bold flex items-center gap-0.5">
                          <Flame className="w-2.5 h-2.5 text-warning" />
                          <span
                            className={
                              seg.excitement_score >= 70
                                ? "text-warning"
                                : seg.excitement_score >= 45
                                ? "text-primary-light"
                                : "text-text-muted"
                            }
                          >
                            {seg.excitement_score.toFixed(0)}
                          </span>
                        </div>
                      </div>

                      {/* Info Footer */}
                      <div className="p-2 space-y-1">
                        <div className="flex items-center justify-between text-[10px]">
                          <span className="text-text-muted">Scene #{seg.scene_number}</span>
                          {seg.audio_peak_db && (
                            <span className="font-mono text-text-secondary">{seg.audio_peak_db} dB</span>
                          )}
                        </div>

                        {/* Attribute Badges */}
                        <div className="flex items-center gap-1 flex-wrap pt-0.5">
                          {seg.is_scene_change && (
                            <span className="px-1 py-0.2 rounded bg-primary/20 text-primary-light text-[9px] font-semibold">
                              Cut
                            </span>
                          )}
                          {seg.is_audio_peak && (
                            <span className="px-1 py-0.2 rounded bg-warning/20 text-warning text-[9px] font-semibold">
                              Peak
                            </span>
                          )}
                          {seg.is_black_frame && (
                            <span className="px-1 py-0.2 rounded bg-surface-3 text-text-muted text-[9px]">
                              Fade
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
