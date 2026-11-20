"use client";

import React, { useEffect, useState, useCallback, useRef, useMemo } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Zap,
  Play,
  Pause,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCcw,
  Sparkles,
  Sliders,
  Filter,
  Film,
  Flame,
  Volume2,
  Eye,
  Clock,
  ChevronRight,
  ShieldAlert,
  ArrowRight,
  Check,
  X,
  Scissors,
  Layers,
  Info,
  Maximize2,
  RefreshCw,
  Search,
  Award,
} from "lucide-react";
import {
  api,
  Recording,
  DetectedMoment,
  EventTypeInfo,
  MomentDetectionOptions,
  DetectedMomentSummary,
} from "@/lib/api";
import { formatDuration } from "@/lib/utils";

// Event visual themes
const EVENT_COLORS: Record<string, { bg: string; text: string; border: string; bar: string }> = {
  police_chase: { bg: "bg-red-500/15", text: "text-red-400", border: "border-red-500/30", bar: "#ef4444" },
  high_speed_driving: { bg: "bg-emerald-500/15", text: "text-emerald-400", border: "border-emerald-500/30", bar: "#10b981" },
  supercar_stunt: { bg: "bg-purple-500/15", text: "text-purple-400", border: "border-purple-500/30", bar: "#a855f7" },
  car_crash: { bg: "bg-amber-500/15", text: "text-amber-400", border: "border-amber-500/30", bar: "#f59e0b" },
  explosion: { bg: "bg-orange-500/15", text: "text-orange-400", border: "border-orange-500/30", bar: "#f97316" },
  shootout: { bg: "bg-rose-500/15", text: "text-rose-400", border: "border-rose-500/30", bar: "#e11d48" },
  funny_npc: { bg: "bg-yellow-500/15", text: "text-yellow-400", border: "border-yellow-500/30", bar: "#eab308" },
  unexpected_gameplay: { bg: "bg-indigo-500/15", text: "text-indigo-400", border: "border-indigo-500/30", bar: "#6366f1" },
  cinematic_scene: { bg: "bg-cyan-500/15", text: "text-cyan-400", border: "border-cyan-500/30", bar: "#06b6d4" },
  nighttime_vice_city: { bg: "bg-pink-500/15", text: "text-pink-400", border: "border-pink-500/30", bar: "#ec4899" },
  interesting_weather: { bg: "bg-sky-500/15", text: "text-sky-400", border: "border-sky-500/30", bar: "#38bdf8" },
  action_sequence: { bg: "bg-red-600/15", text: "text-red-400", border: "border-red-600/30", bar: "#dc2626" },
  gameplay_fail: { bg: "bg-zinc-500/15", text: "text-zinc-400", border: "border-zinc-500/30", bar: "#71717a" },
  unusual_visual: { bg: "bg-violet-500/15", text: "text-violet-400", border: "border-violet-500/30", bar: "#8b5cf6" },
};

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

export default function DetectedMomentsPage() {
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [selectedRecId, setSelectedRecId] = useState<number | null>(null);
  const [eventTypes, setEventTypes] = useState<EventTypeInfo[]>([]);
  const [moments, setMoments] = useState<DetectedMoment[]>([]);
  const [summary, setSummary] = useState<DetectedMomentSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [detecting, setDetecting] = useState(false);
  const [detectProgress, setDetectProgress] = useState<string | null>(null);

  // Filters & State
  const [selectedEventType, setSelectedEventType] = useState<string>("all");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");
  const [uncertainOnly, setUncertainOnly] = useState<boolean>(false);
  const [minConfidenceFilter, setMinConfidenceFilter] = useState<number>(0);
  const [searchQuery, setSearchQuery] = useState("");

  // Sensitivity Modal State
  const [showSensitivityModal, setShowSensitivityModal] = useState(false);
  const [sensitivity, setSensitivity] = useState<"low" | "medium" | "high">("medium");
  const [useVLM, setUseVLM] = useState(false);
  const [minDuration, setMinDuration] = useState(3.0);
  const [mergeGap, setMergeGap] = useState(4.0);

  // Video Preview Modal State
  const [previewMoment, setPreviewMoment] = useState<DetectedMoment | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Load initial recordings and event definitions
  useEffect(() => {
    async function init() {
      try {
        const [recsRes, typesRes] = await Promise.all([
          api.getRecordings(1, 50),
          api.getEventTypes().catch(() => []),
        ]);
        setRecordings(recsRes.items);
        if (recsRes.items.length > 0) {
          setSelectedRecId(recsRes.items[0].id);
        }
        if (typesRes.length > 0) {
          setEventTypes(typesRes);
        }
      } catch (e) {
        console.error("Init error", e);
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  // Fetch moments whenever active recording or filters change
  const loadMoments = useCallback(async () => {
    if (!selectedRecId) {
      setMoments([]);
      setSummary(null);
      return;
    }
    setLoading(true);
    try {
      const res = await api.getDetectedMoments({
        recording_id: selectedRecId,
        event_type: selectedEventType !== "all" ? selectedEventType : undefined,
        status: selectedStatus !== "all" ? selectedStatus : undefined,
        is_uncertain: uncertainOnly ? true : undefined,
        min_confidence: minConfidenceFilter > 0 ? minConfidenceFilter : undefined,
        page_size: 100,
      });
      setMoments(res.items);
      setSummary(res.summary || null);
    } catch (e) {
      console.error("Error loading moments", e);
    } finally {
      setLoading(false);
    }
  }, [selectedRecId, selectedEventType, selectedStatus, uncertainOnly, minConfidenceFilter]);

  useEffect(() => {
    loadMoments();
  }, [loadMoments]);

  const activeRecording = useMemo(() => {
    return recordings.find((r) => r.id === selectedRecId) || null;
  }, [recordings, selectedRecId]);

  // Trigger Detection on Current Recording
  const handleRunDetection = async () => {
    if (!selectedRecId) return;
    setDetecting(true);
    setDetectProgress("Starting multi-modal visual & acoustic event analysis...");
    setShowSensitivityModal(false);

    try {
      const res = await api.triggerMomentDetection(selectedRecId, {
        sensitivity,
        use_vlm: useVLM,
        min_duration_sec: minDuration,
        merge_gap_sec: mergeGap,
      });

      // Poll job progress
      const pollInterval = setInterval(async () => {
        try {
          const jobs = await api.getJobs("all", 10);
          const currentJob = jobs.find((j) => j.id === res.job_id);
          if (currentJob) {
            setDetectProgress(currentJob.message || `Processing... ${currentJob.progress}%`);
            if (currentJob.status === "completed" || currentJob.status === "failed") {
              clearInterval(pollInterval);
              setDetecting(false);
              setDetectProgress(null);
              loadMoments();
            }
          }
        } catch {
          clearInterval(pollInterval);
          setDetecting(false);
          setDetectProgress(null);
          loadMoments();
        }
      }, 1500);
    } catch (e: any) {
      alert(`Detection failed: ${e.message}`);
      setDetecting(false);
      setDetectProgress(null);
    }
  };

  // Status updates
  const handleApprove = async (momentId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.updateDetectedMoment(momentId, { is_approved: true, status: "approved" });
      setMoments((prev) =>
        prev.map((m) => (m.id === momentId ? { ...m, is_approved: true, status: "approved" } : m))
      );
    } catch (err: any) {
      alert(`Error approving moment: ${err.message}`);
    }
  };

  const handleReject = async (momentId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await api.updateDetectedMoment(momentId, { is_approved: false, status: "rejected" });
      setMoments((prev) =>
        prev.map((m) => (m.id === momentId ? { ...m, is_approved: false, status: "rejected" } : m))
      );
    } catch (err: any) {
      alert(`Error rejecting moment: ${err.message}`);
    }
  };

  const handleConvertToClip = async (momentId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      const res = await api.convertMomentToClip(momentId);
      alert(`Converted to YouTube Short candidate: "${res.title}"`);
      setMoments((prev) =>
        prev.map((m) => (m.id === momentId ? { ...m, status: "converted", clip_id: res.clip_id } : m))
      );
    } catch (err: any) {
      alert(`Error converting: ${err.message}`);
    }
  };

  // Preview Modal video control
  const openPreview = (m: DetectedMoment) => {
    setPreviewMoment(m);
    setCurrentTime(m.start_time);
    setIsPlaying(true);
  };

  const closePreview = () => {
    setPreviewMoment(null);
    setIsPlaying(false);
    if (videoRef.current) {
      videoRef.current.pause();
    }
  };

  const recordingDuration = activeRecording?.duration_seconds || 60.0;

  // Filtered moments list
  const filteredMoments = useMemo(() => {
    return moments.filter((m) => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchLabel = m.event_label.toLowerCase().includes(q);
        const matchType = m.event_type.toLowerCase().includes(q);
        const matchExp = m.explanation.toLowerCase().includes(q);
        if (!matchLabel && !matchType && !matchExp) return false;
      }
      return true;
    });
  }, [moments, searchQuery]);

  return (
    <div className="min-h-screen pb-16">
      <Header
        title="Detected Moments"
        subtitle="Phase 4 — GTA 6 Specialized Gameplay Moment Detection (Speech-Independent Vision & Acoustic Engine)"
      />

      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        {/* Top Control Bar: Recording Selector & Action Buttons */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-surface p-4 rounded-xl border border-border">
          <div className="flex items-center gap-3 w-full md:w-auto">
            <Film className="w-5 h-5 text-primary-light flex-shrink-0" />
            <div className="flex flex-col">
              <span className="text-xs text-text-muted">Target Gameplay Recording</span>
              <select
                value={selectedRecId || ""}
                onChange={(e) => setSelectedRecId(Number(e.target.value))}
                className="bg-surface-2 border border-border text-white text-sm rounded-lg px-3 py-1.5 focus:outline-none focus:border-primary mt-0.5 min-w-[280px]"
              >
                {recordings.map((r) => (
                  <option key={r.id} value={r.id}>
                    #{r.id} — {r.original_filename} ({formatDuration(r.duration_seconds || 0)})
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="flex items-center gap-3 w-full md:w-auto justify-end">
            <Link href="/candidate-clips">
              <Button
                variant="outline"
                size="sm"
                className="border-primary/40 text-primary-light hover:bg-primary/10"
              >
                <Award className="w-4 h-4 mr-1.5" />
                Rank & Select Clips
                <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
              </Button>
            </Link>

            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowSensitivityModal(true)}
              className="border-border text-text-secondary hover:text-white"
            >
              <Sliders className="w-4 h-4 mr-2 text-primary-light" />
              Sensitivity: <span className="capitalize ml-1 text-primary-light font-bold">{sensitivity}</span>
            </Button>

            <Button
              onClick={handleRunDetection}
              disabled={detecting || !selectedRecId}
              className="bg-gradient-to-r from-primary to-electric text-white shadow-lg shadow-primary/25 hover:brightness-110"
            >
              {detecting ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Zap className="w-4 h-4 mr-2 fill-current" />
                  Run GTA 6 Detection
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Progress Alert Banner when running */}
        {detectProgress && (
          <div className="p-4 rounded-xl bg-primary/10 border border-primary/30 flex items-center justify-between animate-pulse">
            <div className="flex items-center gap-3">
              <RefreshCw className="w-5 h-5 text-primary-light animate-spin" />
              <div>
                <h4 className="text-sm font-semibold text-white">Detection Pipeline Active</h4>
                <p className="text-xs text-text-muted">{detectProgress}</p>
              </div>
            </div>
            <Badge variant="warning">Processing</Badge>
          </div>
        )}

        {/* Summary KPI Metrics */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="bg-surface-2/60 border-border">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-primary/20 text-primary-light">
                  <Zap className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-text-muted block">Total Moments</span>
                  <span className="text-xl font-bold text-white">{summary.total_moments}</span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-surface-2/60 border-border">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-success/20 text-success">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-text-muted block">Approved Highlights</span>
                  <span className="text-xl font-bold text-white">{summary.approved_moments}</span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-surface-2/60 border-border">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-electric/20 text-electric">
                  <Sparkles className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-text-muted block">High Confidence (&gt;=70%)</span>
                  <span className="text-xl font-bold text-white">{summary.high_confidence_moments}</span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-surface-2/60 border-border">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-warning/20 text-warning">
                  <AlertTriangle className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-text-muted block">Uncertain / Review</span>
                  <span className="text-xl font-bold text-white">{summary.uncertain_moments}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Interactive Timeline Bar with Color-Coded Event Markers */}
        <Card className="bg-surface border-border overflow-hidden">
          <CardHeader className="p-4 pb-2 border-b border-border/50 flex flex-row items-center justify-between">
            <CardTitle className="text-sm font-semibold text-text-primary flex items-center gap-2">
              <Layers className="w-4 h-4 text-primary-light" />
              Recording Timeline Markers (00:00 - {formatTimestamp(recordingDuration)})
            </CardTitle>
            <span className="text-xs text-text-muted">{moments.length} moments detected</span>
          </CardHeader>
          <CardContent className="p-4 pt-3 space-y-2">
            {/* Timeline Ruler */}
            <div className="relative w-full h-12 bg-surface-2 rounded-lg border border-border/60 overflow-hidden select-none">
              {/* Background tick marks */}
              <div className="absolute inset-0 flex justify-between px-2 text-[9px] text-text-muted font-mono items-end pb-0.5 opacity-60">
                <span>00:00</span>
                <span>{formatTimestamp(recordingDuration * 0.25)}</span>
                <span>{formatTimestamp(recordingDuration * 0.5)}</span>
                <span>{formatTimestamp(recordingDuration * 0.75)}</span>
                <span>{formatTimestamp(recordingDuration)}</span>
              </div>

              {/* Event Marker Segments */}
              {moments.map((m) => {
                const leftPct = Math.max(0, Math.min(100, (m.start_time / recordingDuration) * 100));
                const widthPct = Math.max(1.5, Math.min(100 - leftPct, (m.duration / recordingDuration) * 100));
                const theme = EVENT_COLORS[m.event_type] || { bar: "#a855f7" };

                return (
                  <div
                    key={m.id}
                    onClick={() => openPreview(m)}
                    title={`${m.event_label}: ${formatTimestamp(m.start_time)} - ${formatTimestamp(m.end_time)} (${m.confidence_score}%)`}
                    style={{
                      left: `${leftPct}%`,
                      width: `${widthPct}%`,
                      backgroundColor: theme.bar,
                    }}
                    className="absolute top-1 bottom-4 rounded cursor-pointer transition-all duration-150 hover:brightness-125 hover:z-20 shadow-md group flex items-center justify-center"
                  >
                    {m.is_uncertain && (
                      <span className="w-1.5 h-1.5 rounded-full bg-white animate-pulse" />
                    )}
                  </div>
                );
              })}
            </div>

            {/* Event Legend Bar */}
            <div className="flex flex-wrap items-center gap-3 pt-1 text-[11px] text-text-muted">
              <span className="font-semibold text-text-secondary">Key Events:</span>
              {Object.entries(EVENT_COLORS).slice(0, 8).map(([key, style]) => {
                const info = eventTypes.find((e) => e.id === key);
                return (
                  <div key={key} className="flex items-center gap-1.5">
                    <span className="w-2.5 h-2.5 rounded-sm" style={{ backgroundColor: style.bar }} />
                    <span>{info ? info.label : key.replace("_", " ")}</span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Filters Toolbar */}
        <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 bg-surface p-4 rounded-xl border border-border">
          <div className="flex flex-wrap items-center gap-2">
            {/* Status tabs */}
            <div className="flex rounded-lg bg-surface-2 p-1 border border-border">
              {["all", "approved", "detected", "rejected"].map((st) => (
                <button
                  key={st}
                  onClick={() => setSelectedStatus(st)}
                  className={`px-3 py-1 rounded text-xs font-medium capitalize transition-all ${
                    selectedStatus === st
                      ? "bg-primary text-white shadow-sm"
                      : "text-text-muted hover:text-white"
                  }`}
                >
                  {st}
                </button>
              ))}
            </div>

            {/* Uncertain toggle button */}
            <button
              onClick={() => setUncertainOnly(!uncertainOnly)}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium border transition-all ${
                uncertainOnly
                  ? "bg-warning/20 border-warning text-warning"
                  : "bg-surface-2 border-border text-text-muted hover:text-white"
              }`}
            >
              <AlertTriangle className="w-3.5 h-3.5" />
              Uncertain Flagged
            </button>

            {/* Event Type dropdown */}
            <select
              value={selectedEventType}
              onChange={(e) => setSelectedEventType(e.target.value)}
              className="bg-surface-2 border border-border text-white text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-primary"
            >
              <option value="all">All 14 GTA 6 Event Types</option>
              {eventTypes.map((et) => (
                <option key={et.id} value={et.id}>
                  {et.label}
                </option>
              ))}
            </select>
          </div>

          {/* Search box */}
          <div className="relative min-w-[200px]">
            <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              placeholder="Search explanations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-surface-2 border border-border rounded-lg pl-9 pr-3 py-1.5 text-xs text-white placeholder-text-muted focus:outline-none focus:border-primary"
            />
          </div>
        </div>

        {/* Candidate Moments Grid */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 text-text-muted">
            <RefreshCw className="w-8 h-8 animate-spin mb-3 text-primary-light" />
            <p className="text-sm">Loading detected gameplay moments...</p>
          </div>
        ) : filteredMoments.length === 0 ? (
          <div className="rounded-xl border border-border bg-surface flex flex-col items-center justify-center py-20 text-center p-6">
            <Zap className="w-16 h-16 text-text-muted opacity-20 mb-4" />
            <h3 className="text-lg font-semibold text-text-secondary">No Moments Found</h3>
            <p className="text-sm text-text-muted mt-2 max-w-md">
              {moments.length === 0
                ? "No GTA 6 gameplay moments detected yet for this recording. Click 'Run GTA 6 Detection' to analyze OpenCV motion, colors, and audio."
                : "No moments match the active filter criteria. Try resetting filters."}
            </p>
            {moments.length === 0 && (
              <Button
                onClick={handleRunDetection}
                disabled={detecting}
                className="mt-5 bg-primary hover:bg-primary-dark text-white"
              >
                <Zap className="w-4 h-4 mr-2" />
                Analyze Recording Now
              </Button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredMoments.map((moment) => {
              const theme = EVENT_COLORS[moment.event_type] || {
                bg: "bg-surface-2",
                text: "text-primary-light",
                border: "border-border",
              };

              return (
                <Card
                  key={moment.id}
                  onClick={() => openPreview(moment)}
                  className="bg-surface border-border hover:border-primary/50 transition-all duration-200 cursor-pointer overflow-hidden group flex flex-col justify-between"
                >
                  <div>
                    {/* Thumbnail Preview Banner */}
                    <div className="relative aspect-video w-full bg-black/40 overflow-hidden">
                      {moment.thumbnail_url ? (
                        <img
                          src={moment.thumbnail_url}
                          alt={moment.event_label}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center bg-surface-2 text-text-muted">
                          <Film className="w-8 h-8 opacity-40" />
                        </div>
                      )}

                      {/* Top Badges */}
                      <div className="absolute top-2 left-2 flex items-center gap-1.5 flex-wrap">
                        <span
                          className={`text-[11px] font-bold px-2 py-0.5 rounded-md border backdrop-blur-md ${theme.bg} ${theme.text} ${theme.border}`}
                        >
                          {moment.event_label}
                        </span>

                        {moment.is_uncertain && (
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-md bg-warning/90 text-black flex items-center gap-1 shadow-sm">
                            <AlertTriangle className="w-3 h-3" />
                            Uncertain
                          </span>
                        )}
                      </div>

                      {/* Confidence Score Pill */}
                      <div className="absolute top-2 right-2">
                        <span className="text-[11px] font-mono font-bold px-2 py-0.5 rounded-md bg-black/70 text-white border border-white/10 backdrop-blur-md">
                          {Math.round(moment.confidence_score)}% Conf
                        </span>
                      </div>

                      {/* Timestamp duration pill */}
                      <div className="absolute bottom-2 left-2">
                        <span className="text-[11px] font-mono px-2 py-0.5 rounded bg-black/80 text-white backdrop-blur-md flex items-center gap-1">
                          <Clock className="w-3 h-3 text-primary-light" />
                          {formatTimestamp(moment.start_time)} - {formatTimestamp(moment.end_time)} ({moment.duration}s)
                        </span>
                      </div>

                      {/* Center Play Overlay */}
                      <div className="absolute inset-0 bg-black/30 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center">
                        <div className="w-11 h-11 rounded-full bg-primary/90 text-white flex items-center justify-center shadow-lg">
                          <Play className="w-5 h-5 ml-0.5 fill-current" />
                        </div>
                      </div>
                    </div>

                    {/* Content Section */}
                    <div className="p-4 space-y-3">
                      <p className="text-xs text-text-secondary leading-relaxed line-clamp-3">
                        {moment.explanation}
                      </p>

                      {/* Uncertainty reason banner if present */}
                      {moment.is_uncertain && moment.uncertainty_reason && (
                        <div className="p-2 rounded bg-warning/10 border border-warning/20 text-[11px] text-warning flex items-start gap-1.5">
                          <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0 mt-0.5" />
                          <span>{moment.uncertainty_reason}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Card Action Footer */}
                  <div className="p-3 border-t border-border/50 bg-surface-2/30 flex items-center justify-between gap-2">
                    <div className="flex items-center gap-1">
                      {moment.status === "approved" ? (
                        <Badge variant="success" className="text-[10px]">
                          Approved
                        </Badge>
                      ) : moment.status === "rejected" ? (
                        <Badge variant="error" className="text-[10px]">
                          Rejected
                        </Badge>
                      ) : moment.status === "converted" ? (
                        <Badge variant="purple" className="text-[10px]">
                          Clip Created
                        </Badge>
                      ) : (
                        <Badge variant="default" className="text-[10px]">
                          Detected
                        </Badge>
                      )}
                    </div>

                    <div className="flex items-center gap-1.5">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => handleReject(moment.id, e)}
                        title="Reject moment"
                        className="h-7 w-7 p-0 border-border hover:border-red-500/50 hover:text-red-400"
                      >
                        <X className="w-3.5 h-3.5" />
                      </Button>

                      <Button
                        size="sm"
                        variant="outline"
                        onClick={(e) => handleApprove(moment.id, e)}
                        title="Approve moment"
                        className="h-7 w-7 p-0 border-border hover:border-emerald-500/50 hover:text-emerald-400"
                      >
                        <Check className="w-3.5 h-3.5" />
                      </Button>

                      <Button
                        size="sm"
                        onClick={(e) => handleConvertToClip(moment.id, e)}
                        title="Convert to YouTube Short"
                        className="h-7 px-2.5 text-xs bg-primary/20 text-primary-light hover:bg-primary hover:text-white border border-primary/30"
                      >
                        <Scissors className="w-3 h-3 mr-1" />
                        Create Short
                      </Button>
                    </div>
                  </div>
                </Card>
              );
            })}
          </div>
        )}
      </div>

      {/* Sensitivity & Configuration Modal */}
      {showSensitivityModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl max-w-lg w-full p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <h3 className="text-base font-bold text-white flex items-center gap-2">
                <Sliders className="w-5 h-5 text-primary-light" />
                Detection Engine Sensitivity
              </h3>
              <button
                onClick={() => setShowSensitivityModal(false)}
                className="text-text-muted hover:text-white"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="space-y-4 text-sm">
              {/* Sensitivity Preset */}
              <div>
                <label className="text-xs text-text-muted block mb-2 font-medium">Detection Preset</label>
                <div className="grid grid-cols-3 gap-2">
                  {[
                    { id: "low", label: "Low (Strict)", desc: "Conf >= 68%. Only unmistakable events." },
                    { id: "medium", label: "Medium (Balanced)", desc: "Conf >= 48%. Recommended default." },
                    { id: "high", label: "High (Sensitive)", desc: "Conf >= 35%. Captures subtle NPC/stunt moments." },
                  ].map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setSensitivity(p.id as any)}
                      className={`p-3 rounded-xl border text-left transition-all ${
                        sensitivity === p.id
                          ? "bg-primary/20 border-primary text-white font-semibold"
                          : "bg-surface-2 border-border text-text-muted hover:text-white"
                      }`}
                    >
                      <div className="text-xs font-bold text-text-primary">{p.label}</div>
                      <div className="text-[10px] text-text-muted mt-1 leading-tight">{p.desc}</div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Min Duration & Merge Window */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-text-muted block mb-1">Min Duration (Sec)</label>
                  <input
                    type="number"
                    min={2.0}
                    max={15.0}
                    step={0.5}
                    value={minDuration}
                    onChange={(e) => setMinDuration(Number(e.target.value))}
                    className="w-full bg-surface-2 border border-border rounded-lg px-3 py-1.5 text-xs text-white"
                  />
                </div>
                <div>
                  <label className="text-xs text-text-muted block mb-1">Merge Window (Sec)</label>
                  <input
                    type="number"
                    min={1.0}
                    max={10.0}
                    step={0.5}
                    value={mergeGap}
                    onChange={(e) => setMergeGap(Number(e.target.value))}
                    className="w-full bg-surface-2 border border-border rounded-lg px-3 py-1.5 text-xs text-white"
                  />
                </div>
              </div>

              {/* Optional Local VLM Toggle */}
              <div className="p-3.5 rounded-xl bg-surface-2 border border-border flex items-center justify-between">
                <div>
                  <span className="text-xs font-semibold text-text-primary block">
                    Optional Local Vision-Language Model
                  </span>
                  <span className="text-[11px] text-text-muted">
                    Query local Ollama (LLaVA/Moondream) to cross-verify keyframe context.
                  </span>
                </div>
                <input
                  type="checkbox"
                  checked={useVLM}
                  onChange={(e) => setUseVLM(e.target.checked)}
                  className="w-4 h-4 accent-primary rounded cursor-pointer"
                />
              </div>
            </div>

            <div className="flex justify-end gap-3 pt-3 border-t border-border">
              <Button variant="outline" onClick={() => setShowSensitivityModal(false)}>
                Cancel
              </Button>
              <Button onClick={() => setShowSensitivityModal(false)} className="bg-primary text-white">
                Apply & Save
              </Button>
            </div>
          </div>
        </div>
      )}

      {/* Video Preview Modal */}
      {previewMoment && activeRecording && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl max-w-3xl w-full overflow-hidden shadow-2xl space-y-0">
            {/* Modal Header */}
            <div className="p-4 bg-surface-2 flex items-center justify-between border-b border-border">
              <div className="flex items-center gap-2">
                <span
                  className={`text-xs font-bold px-2 py-0.5 rounded border ${
                    (EVENT_COLORS[previewMoment.event_type] || {}).bg
                  } ${(EVENT_COLORS[previewMoment.event_type] || {}).text} ${
                    (EVENT_COLORS[previewMoment.event_type] || {}).border
                  }`}
                >
                  {previewMoment.event_label}
                </span>
                <span className="text-xs text-text-muted">
                  {formatTimestamp(previewMoment.start_time)} - {formatTimestamp(previewMoment.end_time)} ({previewMoment.duration}s)
                </span>
                {previewMoment.is_uncertain && (
                  <Badge variant="warning" className="text-[10px]">
                    Uncertain
                  </Badge>
                )}
              </div>
              <button onClick={closePreview} className="text-text-muted hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Video Player */}
            <div className="relative aspect-video bg-black flex items-center justify-center">
              <video
                ref={videoRef}
                src={`/api/recordings/${activeRecording.id}/proxy`}
                controls
                autoPlay
                onLoadedMetadata={() => {
                  if (videoRef.current) {
                    videoRef.current.currentTime = previewMoment.start_time;
                  }
                }}
                onTimeUpdate={() => {
                  if (videoRef.current) {
                    setCurrentTime(videoRef.current.currentTime);
                    // Loop or pause if exceeded end_time + 1
                    if (videoRef.current.currentTime >= previewMoment.end_time + 0.5) {
                      videoRef.current.currentTime = previewMoment.start_time;
                    }
                  }
                }}
                className="w-full h-full object-contain"
              />
            </div>

            {/* Modal Footer & Explanation */}
            <div className="p-4 space-y-3 bg-surface">
              <p className="text-xs text-text-secondary leading-relaxed">{previewMoment.explanation}</p>
              {previewMoment.is_uncertain && previewMoment.uncertainty_reason && (
                <div className="p-2.5 rounded bg-warning/10 border border-warning/20 text-xs text-warning flex items-start gap-2">
                  <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
                  <span>{previewMoment.uncertainty_reason}</span>
                </div>
              )}

              <div className="flex items-center justify-between pt-2 border-t border-border">
                <div className="text-xs text-text-muted">
                  Confidence Score: <span className="font-bold text-white">{Math.round(previewMoment.confidence_score)}%</span>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => handleReject(previewMoment.id, e)}
                    className="text-xs border-border text-red-400 hover:bg-red-500/10"
                  >
                    <X className="w-3.5 h-3.5 mr-1" />
                    Reject
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={(e) => handleApprove(previewMoment.id, e)}
                    className="text-xs border-border text-emerald-400 hover:bg-emerald-500/10"
                  >
                    <Check className="w-3.5 h-3.5 mr-1" />
                    Approve
                  </Button>
                  <Button
                    size="sm"
                    onClick={(e) => handleConvertToClip(previewMoment.id, e)}
                    className="text-xs bg-primary text-white hover:bg-primary-dark"
                  >
                    <Scissors className="w-3.5 h-3.5 mr-1" />
                    Create Short Clip
                  </Button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
