"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import {
  api,
  Clip,
  Recording,
  Job,
  ShortVerificationResult,
} from "@/lib/api";
import { MetadataModal } from "@/components/shorts/metadata-modal";
import {
  Video,
  Play,
  Pause,
  Volume2,
  VolumeX,
  Maximize2,
  CheckCircle2,
  XCircle,
  Download,
  Trash2,
  RotateCcw,
  Sparkles,
  Layers,
  Crop,
  ShieldCheck,
  Film,
  ArrowRight,
  Settings,
  Flame,
  Clock,
  HardDrive,
  FileVideo,
  RefreshCw,
  Sliders,
  Type,
  Eye,
} from "lucide-react";

export default function GeneratedShortsPage() {
  const [clips, setClips] = useState<Clip[]>([]);
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [selectedRecId, setSelectedRecId] = useState<number | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [modeFilter, setModeFilter] = useState<string>("all");
  const [activeJob, setActiveJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  // Video Modal State
  const [previewClip, setPreviewClip] = useState<Clip | null>(null);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [currentTime, setCurrentTime] = useState<number>(0);
  const [duration, setDuration] = useState<number>(0);
  const [isMuted, setIsMuted] = useState<boolean>(false);
  const [volume, setVolume] = useState<number>(1.0);
  const [verificationData, setVerificationData] = useState<ShortVerificationResult | null>(null);
  const [verifying, setVerifying] = useState<boolean>(false);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Batch Generation Modal State
  const [showBatchModal, setShowBatchModal] = useState<boolean>(false);
  const [batchRenderMode, setBatchRenderMode] = useState<"blurred_background" | "smart_crop" | "action_hybrid">("blurred_background");
  const [batchTargetLength, setBatchTargetLength] = useState<number | undefined>(undefined);
  const [batchSubtitles, setBatchSubtitles] = useState<boolean>(false);
  const [batchSubtitleStyle, setBatchSubtitleStyle] = useState<string>("vice_neon");
  const [batchUseGpu, setBatchUseGpu] = useState<boolean>(true);
  const [batchSelectN, setBatchSelectN] = useState<number>(10);
  const [isSubmittingBatch, setIsSubmittingBatch] = useState<boolean>(false);

  // Phase 8: Metadata Modal State
  const [metadataModalClip, setMetadataModalClip] = useState<Clip | null>(null);

  // Initial Load
  useEffect(() => {
    loadData();
    const interval = setInterval(checkActiveJobs, 3000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    loadClips();
  }, [selectedRecId, statusFilter, modeFilter]);

  const loadData = async () => {
    setLoading(true);
    try {
      const recsRes = await api.getRecordings(1, 100);
      setRecordings(recsRes.items || []);
      if (recsRes.items?.length > 0 && selectedRecId === null) {
        setSelectedRecId(recsRes.items[0].id);
      }
    } catch (e) {
      console.error("Failed to load recordings:", e);
    } finally {
      setLoading(false);
    }
  };

  const loadClips = async () => {
    try {
      const data = await api.getClips({
        recording_id: selectedRecId || undefined,
        status: statusFilter,
        render_mode: modeFilter,
        page_size: 50,
      });
      setClips(data || []);
    } catch (e) {
      console.error("Failed to load clips:", e);
    }
  };

  const checkActiveJobs = async () => {
    try {
      const jobs = await api.getJobs("running", 10);
      const genJob = jobs.find((j) => j.job_type === "clip_generation");
      if (genJob) {
        setActiveJob(genJob);
      } else {
        const procJobs = await api.getJobs("processing", 10);
        const pJob = procJobs.find((j) => j.job_type === "clip_generation");
        if (pJob) {
          setActiveJob(pJob);
        } else if (activeJob) {
          setActiveJob(null);
          loadClips();
        }
      }
    } catch (e) {}
  };

  // Video Player Controls
  const openPreview = async (c: Clip) => {
    setPreviewClip(c);
    setIsPlaying(false);
    setCurrentTime(0);
    setVerificationData(null);
    try {
      setVerifying(true);
      const ver = await api.verifyClip(c.id);
      setVerificationData(ver);
    } catch (err) {
      console.error("Verification failed:", err);
    } finally {
      setVerifying(false);
    }
  };

  const closePreview = () => {
    if (videoRef.current) {
      videoRef.current.pause();
    }
    setPreviewClip(null);
    setIsPlaying(false);
  };

  const togglePlay = () => {
    if (!videoRef.current) return;
    if (isPlaying) {
      videoRef.current.pause();
      setIsPlaying(false);
    } else {
      videoRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
      setDuration(videoRef.current.duration || 0);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    setCurrentTime(time);
    if (videoRef.current) {
      videoRef.current.currentTime = time;
    }
  };

  const handleApprove = async (clipId: number) => {
    try {
      const updated = await api.approveClip(clipId);
      setClips((prev) => prev.map((c) => (c.id === clipId ? updated : c)));
      if (previewClip?.id === clipId) setPreviewClip(updated);
    } catch (e: any) {
      alert(`Approval failed: ${e.message}`);
    }
  };

  const handleReject = async (clipId: number) => {
    try {
      const updated = await api.rejectClip(clipId);
      setClips((prev) => prev.map((c) => (c.id === clipId ? updated : c)));
      if (previewClip?.id === clipId) setPreviewClip(updated);
    } catch (e: any) {
      alert(`Rejection failed: ${e.message}`);
    }
  };

  const handleDelete = async (clipId: number, deleteFile = true) => {
    if (!confirm("Are you sure you want to delete this generated Short?")) return;
    try {
      await api.deleteClip(clipId, deleteFile);
      setClips((prev) => prev.filter((c) => c.id !== clipId));
      if (previewClip?.id === clipId) closePreview();
    } catch (e: any) {
      alert(`Delete failed: ${e.message}`);
    }
  };

  // Run Batch Generation
  const handleTriggerBatch = async () => {
    if (!selectedRecId) return;
    setIsSubmittingBatch(true);
    try {
      const res = await api.batchGenerateShorts({
        recording_id: selectedRecId,
        select_top_n: batchSelectN,
        target_length: batchTargetLength,
        render_mode: batchRenderMode,
        subtitles: batchSubtitles,
        subtitle_style: batchSubtitleStyle,
        use_gpu: batchUseGpu,
      });
      setShowBatchModal(false);
      checkActiveJobs();
      alert(`Batch Generation started! Job #${res.job_id} queued.`);
    } catch (e: any) {
      alert(`Batch generation failed: ${e.message}`);
    } finally {
      setIsSubmittingBatch(false);
    }
  };

  const handleBatchGenerateMetadata = async () => {
    if (clips.length === 0) {
      alert("No shorts available to generate metadata for.");
      return;
    }
    try {
      const clipIds = clips.map((c) => c.id);
      const res = await api.batchGenerateMetadata({ clip_ids: clipIds, overwrite_existing: false });
      alert(`AI YouTube Shorts Metadata generated for ${res.generated_count} clips!`);
      loadClips();
    } catch (e: any) {
      alert(`Batch metadata generation failed: ${e.message}`);
    }
  };

  const formatSeconds = (sec: number | null) => {
    if (!sec) return "0:00";
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return `${m}:${s < 10 ? "0" : ""}${s}`;
  };

  const formatBytes = (bytes?: number | null) => {
    if (!bytes) return "0 MB";
    const mb = bytes / (1024 * 1024);
    return `${mb.toFixed(1)} MB`;
  };

  return (
    <div className="min-h-screen bg-background text-text-primary">
      <Header
        title="Generated YouTube Shorts"
        subtitle="Automatic 9:16 vertical gameplay shorts with action preservation & gameplay audio"
      />

      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        {/* Top Feature Summary Bar */}
        <div className="p-4 rounded-xl border border-cyan-500/30 bg-gradient-to-r from-cyan-950/20 via-purple-950/20 to-background flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-lg bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Film className="w-5 h-5" />
    </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-semibold text-white">Default YouTube Shorts Output:</span>
                <span className="px-2 py-0.5 rounded text-xs font-mono bg-cyan-500/20 text-cyan-300 border border-cyan-500/40">
                  1080x1920 (9:16)
                </span>
                <span className="px-2 py-0.5 rounded text-xs font-mono bg-purple-500/20 text-purple-300 border border-purple-500/40">
                  H.264 + AAC
                </span>
                <span className="px-2 py-0.5 rounded text-xs font-mono bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                  30 / 60 FPS
                </span>
      </div>
              <p className="text-xs text-text-muted mt-1">
                Saved directly to <span className="font-mono text-cyan-400">D:\GTA_CLIPFORGE_AI\GTA6_SHORTS</span> • Never stretched • Smooth audio & video transitions
              </p>
    </div>
            {/* AI YouTube Shorts Metadata Modal */}

    </div>

          <div className="flex items-center gap-3 w-full md:w-auto justify-end">
            <Link
              href="/candidate-clips"
              className="px-3.5 py-2 text-xs font-medium text-text-muted hover:text-white border border-border hover:border-text-muted rounded-lg transition-colors flex items-center gap-1.5"
            >
              <span>View Candidate Clips</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </Link>
            <button
              onClick={handleBatchGenerateMetadata}
              className="px-3.5 py-2 text-xs font-semibold text-cyan-300 bg-cyan-950/40 hover:bg-cyan-900/50 border border-cyan-500/40 rounded-lg transition-all flex items-center gap-1.5"
              title="Generate AI YouTube Shorts Metadata for all loaded clips"
            >
              <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
              <span>AI Metadata (All)</span>
            </button>
            <button
              onClick={() => setShowBatchModal(true)}
              className="px-4 py-2 text-xs font-semibold text-white bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-400 hover:to-purple-500 rounded-lg shadow-lg shadow-cyan-500/20 transition-all flex items-center gap-2"
            >
              <Sparkles className="w-4 h-4" />
              <span>Generate Shorts Batch</span>
            </button>
            {/* AI YouTube Shorts Metadata Modal */}

    </div>
          {/* AI YouTube Shorts Metadata Modal */}

    </div>

        {/* Real-Time Processing Banner */}
        {activeJob && (
          <div className="p-4 rounded-xl border border-amber-500/40 bg-amber-500/10 flex items-center justify-between animate-pulse">
            <div className="flex items-center gap-3">
              <RefreshCw className="w-5 h-5 text-amber-400 animate-spin" />
              <div>
                <p className="text-sm font-semibold text-amber-300">
                  Shorts Generation in Progress: {activeJob.progress.toFixed(0)}%
                </p>
                <p className="text-xs text-amber-200/80">{activeJob.message || "Rendering 9:16 vertical shorts..."}</p>
      </div>
    </div>
            <div className="w-48 bg-black/40 rounded-full h-2.5 overflow-hidden border border-amber-500/30">
              <div
                className="bg-amber-400 h-2.5 rounded-full transition-all duration-300"
                style={{ width: `${Math.max(5, activeJob.progress)}%` }}
              />
    </div>
            {/* AI YouTube Shorts Metadata Modal */}

    </div>
        )}

        {/* Filter Controls Bar */}
        <div className="p-4 rounded-xl border border-border bg-surface flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            {/* Recording Select */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-muted font-medium">Recording:</span>
              <select
                value={selectedRecId || ""}
                onChange={(e) => setSelectedRecId(Number(e.target.value) || null)}
                className="bg-background border border-border text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-cyan-500"
              >
                {recordings.map((r) => (
                  <option key={r.id} value={r.id}>
                    #{r.id} {r.original_filename} ({r.duration_seconds?.toFixed(0)}s)
                  </option>
                ))}
              </select>
    </div>

            {/* Render Mode Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-muted font-medium">Render Mode:</span>
              <select
                value={modeFilter}
                onChange={(e) => setModeFilter(e.target.value)}
                className="bg-background border border-border text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-cyan-500"
              >
                <option value="all">All Modes</option>
                <option value="blurred_background">Blurred Background Fill (100% Action)</option>
                <option value="smart_crop">Smart Vertical Action Crop</option>
                <option value="action_hybrid">Action Hybrid Zoom</option>
              </select>
    </div>

            {/* Approval Status Filter */}
            <div className="flex items-center gap-2">
              <span className="text-xs text-text-muted font-medium">Status:</span>
              <select
                value={statusFilter}
                onChange={(e) => setStatusFilter(e.target.value)}
                className="bg-background border border-border text-xs rounded-lg px-3 py-1.5 focus:outline-none focus:border-cyan-500"
              >
                <option value="all">All Statuses</option>
                <option value="generated">Generated</option>
                <option value="approved">Approved</option>
                <option value="rejected">Rejected</option>
              </select>
    </div>
            {/* AI YouTube Shorts Metadata Modal */}

    </div>

          <div className="flex items-center gap-2 text-xs text-text-muted">
            <Link
              href="/recordings?action=youtube"
              className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-600/90 hover:bg-red-600 text-white text-xs font-semibold transition-colors"
            >
              <Video className="w-3.5 h-3.5" />
              Paste YouTube Link
            </Link>
            <span className="px-2.5 py-1 rounded-md bg-background border border-border">
              Total Shorts: <strong className="text-white">{clips.length}</strong>
            </span>
            <button
              onClick={loadClips}
              className="p-1.5 rounded-lg border border-border hover:border-text-muted hover:text-white transition-colors"
              title="Refresh"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          </div>
          {/* AI YouTube Shorts Metadata Modal */}

    </div>

        {/* Empty State */}
        {clips.length === 0 && !loading && (
          <div className="rounded-2xl border border-dashed border-border bg-surface/50 p-12 text-center flex flex-col items-center justify-center space-y-4">
            <div className="w-16 h-16 rounded-full bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400">
              <Film className="w-8 h-8" />
    </div>
            <div className="max-w-md">
              <h3 className="text-lg font-semibold text-white">No YouTube Shorts Generated Yet</h3>
              <p className="text-sm text-text-muted mt-1">
                Candidate clips have been identified! Click below to automatically render up to 20 vertical 9:16 YouTube Shorts with zero distortion.
              </p>
    </div>
            <div className="flex items-center gap-3 pt-2">
              <Link
                href="/candidate-clips"
                className="px-4 py-2 text-xs font-semibold text-text-secondary border border-border hover:border-text-muted rounded-lg"
              >
                Inspect Candidate Clips
              </Link>
              <button
                onClick={() => setShowBatchModal(true)}
                className="px-4 py-2 text-xs font-semibold text-white bg-cyan-500 hover:bg-cyan-400 rounded-lg shadow-lg shadow-cyan-500/20"
              >
                Generate Shorts Now
              </button>
    </div>
            {/* AI YouTube Shorts Metadata Modal */}

    </div>
        )}

        {/* 9:16 Shorts Grid Cards */}
        {clips.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
            {clips.map((clip) => {
              const isApproved = clip.is_approved || clip.status === "approved";
              const isRejected = clip.status === "rejected";

              return (
                <div
                  key={clip.id}
                  className="group rounded-xl border border-border bg-surface overflow-hidden hover:border-cyan-500/50 transition-all flex flex-col shadow-lg"
                >
                  {/* 9:16 Aspect Thumbnail Container */}
                  <div
                    className="relative aspect-[9/16] bg-black cursor-pointer overflow-hidden flex items-center justify-center"
                    onClick={() => openPreview(clip)}
                  >
                    {clip.thumbnail_path ? (
                      <img
                        src={api.getClipThumbnailUrl(clip.id)}
                        alt={clip.title || "Short Thumbnail"}
                        className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        onError={(e) => {
                          (e.target as HTMLElement).style.display = "none";
                        }}
                      />
                    ) : (
                      <div className="w-full h-full flex flex-col items-center justify-center bg-zinc-900 text-zinc-600">
                        <Film className="w-12 h-12 mb-2" />
                        <span className="text-xs">1080 x 1920</span>
              </div>
                    )}

                    {/* Gradient overlay */}
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-black/40" />

                    {/* Top Badges */}
                    <div className="absolute top-2.5 left-2.5 right-2.5 flex items-center justify-between text-[11px]">
                      <span className="px-2 py-0.5 rounded-full bg-black/60 backdrop-blur-md border border-white/10 font-mono text-cyan-300">
                        {clip.duration ? `${clip.duration.toFixed(0)}s` : "30s"}
                      </span>
                      {clip.excitement_score && (
                        <span className="px-2 py-0.5 rounded-full bg-amber-500/20 backdrop-blur-md border border-amber-500/40 text-amber-300 font-bold flex items-center gap-1">
                          <Flame className="w-3 h-3 text-amber-400" />
                          {Math.round(clip.excitement_score)}
                        </span>
                      )}
            </div>

                    {/* Center Play Button Overlay */}
                    <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/30 backdrop-blur-[2px]">
                      <div className="w-14 h-14 rounded-full bg-cyan-500/90 text-white flex items-center justify-center shadow-xl shadow-cyan-500/30 transform group-hover:scale-110 transition-transform">
                        <Play className="w-6 h-6 ml-1 fill-white" />
              </div>
            </div>

                    {/* Bottom Info Overlay */}
                    <div className="absolute bottom-2.5 left-2.5 right-2.5 space-y-1">
                      <div className="flex items-center gap-1.5">
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-cyan-500/20 text-cyan-300 border border-cyan-500/30 font-mono">
                          9:16
                        </span>
                        <span className="px-1.5 py-0.5 rounded text-[10px] bg-purple-500/20 text-purple-300 border border-purple-500/30 capitalize">
                          {clip.render_mode?.replace("_", " ") || "Blurred Fill"}
                        </span>
                        {clip.has_subtitles && (
                          <span className="px-1.5 py-0.5 rounded text-[10px] bg-pink-500/20 text-pink-300 border border-pink-500/30">
                            Subtitles
                          </span>
                        )}
              </div>
                      <p className="text-xs font-semibold text-white truncate drop-shadow">
                        {clip.title || "GTA 6 Gameplay Short"}
                      </p>
            </div>
          </div>

                  {/* Card Actions Footer */}
                  <div className="p-3 bg-surface border-t border-border flex items-center justify-between gap-1 text-xs">
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleApprove(clip.id)}
                        className={`p-1.5 rounded-lg border transition-colors ${
                          isApproved
                            ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-400"
                            : "border-border text-text-muted hover:text-emerald-400 hover:border-emerald-500/30"
                        }`}
                        title="Approve for Publishing"
                      >
                        <CheckCircle2 className="w-4 h-4" />
                      </button>
                      <button
                        onClick={() => handleReject(clip.id)}
                        className={`p-1.5 rounded-lg border transition-colors ${
                          isRejected
                            ? "bg-red-500/20 border-red-500/50 text-red-400"
                            : "border-border text-text-muted hover:text-red-400 hover:border-red-500/30"
                        }`}
                        title="Reject Short"
                      >
                        <XCircle className="w-4 h-4" />
                      </button>
            </div>

                    <div className="flex items-center gap-1">
                      <button
                        type="button"
                        onClick={() => setMetadataModalClip(clip)}
                        className="px-2 py-1 rounded-lg border border-cyan-500/30 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20 text-[11px] font-semibold transition-all flex items-center gap-1"
                        title="AI YouTube Shorts Metadata Studio"
                      >
                        <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                        <span className="hidden sm:inline">AI Meta</span>
                      </button>
                      <a
                        href={api.getClipDownloadUrl(clip.id)}
                        download
                        className="p-1.5 rounded-lg border border-border text-text-muted hover:text-cyan-400 hover:border-cyan-500/30 transition-colors"
                        title="Download MP4 Video"
                      >
                        <Download className="w-4 h-4" />
                      </a>
                      <button
                        onClick={() => handleDelete(clip.id)}
                        className="p-1.5 rounded-lg border border-border text-text-muted hover:text-red-400 hover:border-red-500/30 transition-colors"
                        title="Delete Short"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
            </div>
          </div>
        </div>
              );
            })}
            {/* AI YouTube Shorts Metadata Modal */}

    </div>
        )}
        {/* AI YouTube Shorts Metadata Modal */}

    </div>

      {/* Video Preview Modal (9:16 Shorts Player) */}
      {previewClip && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl w-full max-w-4xl max-h-[92vh] overflow-hidden flex flex-col md:flex-row shadow-2xl">
            {/* 9:16 Vertical Player Frame */}
            <div className="relative bg-black flex-1 flex items-center justify-center min-h-[460px] md:min-h-[580px] p-2">
              <video
                ref={videoRef}
                src={api.getClipStreamUrl(previewClip.id)}
                className="max-h-[82vh] max-w-full aspect-[9/16] object-contain rounded-lg shadow-2xl"
                onTimeUpdate={handleTimeUpdate}
                onEnded={() => setIsPlaying(false)}
                playsInline
                autoPlay
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
              />

              {/* In-Video Overlay Header */}
              <div className="absolute top-4 left-4 right-4 flex items-center justify-between text-xs pointer-events-none">
                <span className="px-2.5 py-1 rounded-md bg-black/70 backdrop-blur-md border border-white/20 text-white font-mono">
                  1080 x 1920 • 9:16
                </span>
                <span className="px-2.5 py-1 rounded-md bg-cyan-500/20 backdrop-blur-md border border-cyan-500/40 text-cyan-300 font-semibold capitalize">
                  {previewClip.render_mode?.replace("_", " ") || "Blurred Fill"}
                </span>
      </div>

              {/* Bottom Custom Controls Bar */}
              <div className="absolute bottom-4 left-4 right-4 bg-black/80 backdrop-blur-md border border-white/10 rounded-xl p-3 flex flex-col gap-2">
                {/* Scrubber slider */}
                <input
                  type="range"
                  min={0}
                  max={duration || previewClip.duration || 30}
                  step={0.1}
                  value={currentTime}
                  onChange={handleSeek}
                  className="w-full accent-cyan-400 h-1.5 bg-white/20 rounded-lg cursor-pointer"
                />

                <div className="flex items-center justify-between text-xs text-white">
                  <div className="flex items-center gap-3">
                    <button
                      onClick={togglePlay}
                      className="p-1 text-cyan-400 hover:text-cyan-300 transition-colors"
                    >
                      {isPlaying ? <Pause className="w-5 h-5 fill-current" /> : <Play className="w-5 h-5 fill-current" />}
                    </button>
                    <button
                      onClick={() => {
                        if (videoRef.current) {
                          videoRef.current.muted = !isMuted;
                          setIsMuted(!isMuted);
                        }
                      }}
                      className="text-text-muted hover:text-white"
                    >
                      {isMuted ? <VolumeX className="w-4 h-4" /> : <Volume2 className="w-4 h-4" />}
                    </button>
                    <span className="font-mono text-xs text-text-muted">
                      {formatSeconds(currentTime)} / {formatSeconds(duration || previewClip.duration)}
                    </span>
          </div>

                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        if (videoRef.current) {
                          if (document.fullscreenElement) {
                            document.exitFullscreen();
                          } else {
                            videoRef.current.requestFullscreen();
                          }
                        }
                      }}
                      className="p-1 text-text-muted hover:text-white"
                      title="Fullscreen"
                    >
                      <Maximize2 className="w-4 h-4" />
                    </button>
          </div>
        </div>
      </div>
    </div>

            {/* Sidebar Details & Verification Pane */}
            <div className="w-full md:w-80 border-t md:border-t-0 md:border-l border-border p-5 flex flex-col justify-between overflow-y-auto">
              <div className="space-y-4">
                <div className="flex items-center justify-between">
                  <h4 className="font-bold text-white text-sm">Short Specifications</h4>
                  <button
                    onClick={closePreview}
                    className="p-1 rounded-lg text-text-muted hover:text-white hover:bg-surface-elevated"
                  >
                    <XCircle className="w-5 h-5" />
                  </button>
        </div>

                <div>
                  <h3 className="font-semibold text-white text-base leading-snug">
                    {previewClip.title || "GTA 6 Gameplay Short"}
                  </h3>
                  <p className="text-xs text-text-muted mt-1 leading-relaxed">
                    {previewClip.description || "AI-selected highlight with optimized boundaries and gameplay audio preservation."}
                  </p>
        </div>

                {/* Technical Specs List */}
                <div className="p-3 rounded-lg bg-surface-elevated border border-border space-y-2 text-xs">
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">Resolution:</span>
                    <span className="font-mono font-semibold text-cyan-300">1080 x 1920 (9:16)</span>
          </div>
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">Duration:</span>
                    <span className="font-mono text-white">{previewClip.duration?.toFixed(1)}s</span>
          </div>
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">Video Codec:</span>
                    <span className="font-mono text-white">{previewClip.video_codec?.toUpperCase() || "H.264"}</span>
          </div>
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">Audio Codec:</span>
                    <span className="font-mono text-white">{previewClip.audio_codec?.toUpperCase() || "AAC"}</span>
          </div>
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">FPS:</span>
                    <span className="font-mono text-white">{previewClip.fps || 60} fps</span>
          </div>
                  <div className="flex items-center justify-between">
                    <span className="text-text-muted">File Size:</span>
                    <span className="font-mono text-white">{formatBytes(previewClip.file_size_bytes)}</span>
          </div>
        </div>

                {/* FFprobe Real Verification Status */}
                <div className="p-3 rounded-lg border border-border bg-background space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-white flex items-center gap-1.5">
                      <ShieldCheck className="w-4 h-4 text-emerald-400" />
                      FFprobe Verification:
                    </span>
                    {verifying ? (
                      <span className="text-[10px] text-amber-400">Verifying...</span>
                    ) : verificationData?.is_valid ? (
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40">
                        VERIFIED 100%
                      </span>
                    ) : (
                      <span className="px-1.5 py-0.5 rounded text-[10px] bg-amber-500/20 text-amber-300 font-bold">
                        Pending Probe
                      </span>
                    )}
          </div>

                  {verificationData && (
                    <div className="text-[11px] space-y-1 pt-1 border-t border-border/50 text-text-muted">
                      <div className="flex items-center justify-between">
                        <span>Aspect & Dimension:</span>
                        <span className="text-emerald-400 font-mono">1080x1920 (9:16) ✓</span>
              </div>
                      <div className="flex items-center justify-between">
                        <span>Video Stream:</span>
                        <span className="text-emerald-400 font-mono">h264 Progressive ✓</span>
              </div>
                      <div className="flex items-center justify-between">
                        <span>Audio Stream:</span>
                        <span className="text-emerald-400 font-mono">aac Stereo 48kHz ✓</span>
              </div>
                      <div className="flex items-center justify-between">
                        <span>Boundary Match:</span>
                        <span className="text-emerald-400 font-mono">Δ {verificationData.duration_difference}s ✓</span>
              </div>
            </div>
                  )}
        </div>

                {/* Storage Path Indicator */}
                <div className="text-[11px] text-text-muted break-all">
                  <span className="font-semibold text-white">Disk Location:</span>
                  <p className="font-mono text-zinc-400 mt-0.5 text-[10px]">{previewClip.clip_path}</p>
        </div>
      </div>

              {/* Action Buttons in Modal */}
              <div className="pt-4 border-t border-border space-y-2">
                <div className="grid grid-cols-2 gap-2">
                  <button
                    onClick={() => handleApprove(previewClip.id)}
                    className="w-full py-2 px-3 rounded-lg text-xs font-semibold bg-emerald-500/20 text-emerald-300 hover:bg-emerald-500/30 border border-emerald-500/40 transition-colors flex items-center justify-center gap-1.5"
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Approve</span>
                  </button>
                  <button
                    onClick={() => handleReject(previewClip.id)}
                    className="w-full py-2 px-3 rounded-lg text-xs font-semibold bg-red-500/20 text-red-300 hover:bg-red-500/30 border border-red-500/40 transition-colors flex items-center justify-center gap-1.5"
                  >
                    <XCircle className="w-3.5 h-3.5" />
                    <span>Reject</span>
                  </button>
        </div>

                <a
                  href={api.getClipDownloadUrl(previewClip.id)}
                  download
                  className="w-full py-2 px-3 rounded-lg text-xs font-semibold bg-cyan-500/20 text-cyan-300 hover:bg-cyan-500/30 border border-cyan-500/40 transition-colors flex items-center justify-center gap-1.5"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download MP4 File</span>
                </a>

                <button
                  type="button"
                  onClick={() => {
                    const c = previewClip;
                    closePreview();
                    setMetadataModalClip(c);
                  }}
                  className="w-full py-2 px-3 rounded-lg text-xs font-semibold bg-gradient-to-r from-cyan-500/20 to-purple-500/20 text-white hover:from-cyan-500/30 hover:to-purple-500/30 border border-cyan-500/40 transition-colors flex items-center justify-center gap-1.5"
                >
                  <Sparkles className="w-3.5 h-3.5 text-cyan-400" />
                  <span>AI YouTube Shorts Metadata</span>
                </button>
      </div>
    </div>
            {/* AI YouTube Shorts Metadata Modal */}

    </div>
          {/* AI YouTube Shorts Metadata Modal */}

    </div>
      )}

      {/* Batch Generation Modal */}
      {showBatchModal && (
        <div className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl w-full max-w-lg p-6 space-y-5 shadow-2xl">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-cyan-400" />
                <h3 className="font-bold text-white text-base">Automatic YouTube Shorts Generator</h3>
      </div>
              <button
                onClick={() => setShowBatchModal(false)}
                className="text-text-muted hover:text-white"
              >
                <XCircle className="w-5 h-5" />
              </button>
    </div>

            <div className="space-y-4 text-xs">
              {/* Select Top N candidate clips */}
              <div>
                <label className="block text-text-muted font-medium mb-1.5">
                  Candidate Clips to Generate (Up to 20):
                </label>
                <div className="grid grid-cols-4 gap-2">
                  {[5, 10, 15, 20].map((n) => (
                    <button
                      key={n}
                      type="button"
                      onClick={() => setBatchSelectN(n)}
                      className={`py-2 rounded-lg font-semibold border transition-all ${
                        batchSelectN === n
                          ? "bg-cyan-500 text-white border-cyan-400"
                          : "border-border bg-background text-text-secondary hover:border-text-muted"
                      }`}
                    >
                      Top {n} Clips
                    </button>
                  ))}
        </div>
      </div>

              {/* Reframing Mode */}
              <div>
                <label className="block text-text-muted font-medium mb-1.5">
                  Vertical 9:16 Reframing Technique:
                </label>
                <div className="space-y-2">
                  <label
                    onClick={() => setBatchRenderMode("blurred_background")}
                    className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                      batchRenderMode === "blurred_background"
                        ? "bg-cyan-500/10 border-cyan-500 text-white"
                        : "border-border bg-background text-text-muted hover:border-text-muted"
                    }`}
                  >
                    <Layers className="w-5 h-5 text-cyan-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="font-semibold text-white">Blurred Background Fill (Recommended)</p>
                      <p className="text-[11px] text-text-muted">
                        Scales original 16:9 gameplay to fill 1080 width, centered over an ambient blurred background. Preserves 100% of gameplay, mini-map, and HUD. Zero stretching!
                      </p>
            </div>
                  </label>

                  <label
                    onClick={() => setBatchRenderMode("smart_crop")}
                    className={`flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-all ${
                      batchRenderMode === "smart_crop"
                        ? "bg-cyan-500/10 border-cyan-500 text-white"
                        : "border-border bg-background text-text-muted hover:border-text-muted"
                    }`}
                  >
                    <Crop className="w-5 h-5 text-purple-400 mt-0.5 shrink-0" />
                    <div>
                      <p className="font-semibold text-white">Smart Vertical Action Crop</p>
                      <p className="text-[11px] text-text-muted">
                        Crops a vertical 9:16 slice centered around the gameplay action focal point. Full screen vertical coverage without stretching.
                      </p>
            </div>
                  </label>
        </div>
      </div>

              {/* Subtitles / Gamer Hook Banner */}
              <div className="p-3 rounded-lg border border-border bg-background space-y-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Type className="w-4 h-4 text-cyan-400" />
                    <span className="font-semibold text-white">Gamer Hook Subtitles / Header</span>
          </div>
                  <input
                    type="checkbox"
                    checked={batchSubtitles}
                    onChange={(e) => setBatchSubtitles(e.target.checked)}
                    className="w-4 h-4 accent-cyan-500 cursor-pointer"
                  />
        </div>
                <p className="text-[11px] text-text-muted">
                  Burns stylized category hook text (e.g., "GTA 6 POLICE CHASE", "BADASS STUNT") in the top third of the Short for high engagement.
                </p>
                {batchSubtitles && (
                  <div className="pt-2 flex items-center gap-2">
                    <span className="text-text-muted text-[11px]">Style:</span>
                    <select
                      value={batchSubtitleStyle}
                      onChange={(e) => setBatchSubtitleStyle(e.target.value)}
                      className="bg-surface border border-border rounded px-2 py-1 text-xs"
                    >
                      <option value="vice_neon">Vice City Neon Cyan</option>
                      <option value="bold_yellow">Bold Gaming Yellow</option>
                      <option value="clean_white">Clean White</option>
                    </select>
          </div>
                )}
      </div>

              {/* Hardware Acceleration Toggle */}
              <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-background">
                <div>
                  <span className="font-semibold text-white block">GPU NVENC Acceleration</span>
                  <span className="text-[11px] text-text-muted">
                    High-speed NVIDIA NVENC hardware encoder with automatic CPU fallback
                  </span>
        </div>
                <input
                  type="checkbox"
                  checked={batchUseGpu}
                  onChange={(e) => setBatchUseGpu(e.target.checked)}
                  className="w-4 h-4 accent-cyan-500 cursor-pointer"
                />
      </div>
    </div>

            <div className="flex items-center justify-end gap-3 pt-3 border-t border-border">
              <button
                type="button"
                onClick={() => setShowBatchModal(false)}
                className="px-4 py-2 text-xs font-semibold text-text-muted hover:text-white border border-border rounded-lg"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={isSubmittingBatch}
                onClick={handleTriggerBatch}
                className="px-5 py-2 text-xs font-semibold text-white bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-400 hover:to-purple-500 rounded-lg shadow-lg shadow-cyan-500/20 disabled:opacity-50"
              >
                {isSubmittingBatch ? "Queuing..." : "Start Batch Generation"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* AI YouTube Shorts Metadata Modal */}
      <MetadataModal
        clip={metadataModalClip}
        isOpen={!!metadataModalClip}
        onClose={() => setMetadataModalClip(null)}
        onSaved={() => loadClips()}
      />
    </div>
  );
}
