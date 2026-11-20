"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import {
  api,
  Clip,
  ClipMetadata,
  PublishingItem,
  PublishingStatus,
  PublishingWorkspaceSummary,
  ExportPackageResult,
} from "@/lib/api";
import { MetadataModal } from "@/components/shorts/metadata-modal";
import {
  Download,
  Folder,
  CheckCircle2,
  HardDrive,
  Film,
  ExternalLink,
  ShieldCheck,
  AlertTriangle,
  RefreshCw,
  Clock,
  Sparkles,
  Copy,
  Check,
  Youtube,
  Type,
  Hash,
  MessageSquare,
  FileCode,
  FileText,
  Archive,
  BarChart2,
  Calendar,
  Save,
  TrendingUp,
  Share2,
  Eye,
  ThumbsUp,
  FileCheck,
  Zap,
} from "lucide-react";

export default function ExportCenterPage() {
  const [activeTab, setActiveTab] = useState<"exports" | "publishing">("exports");
  const [clips, setClips] = useState<Clip[]>([]);
  const [metadataMap, setMetadataMap] = useState<Record<number, ClipMetadata>>({});
  const [statusMap, setStatusMap] = useState<Record<number, { can_export: boolean; block_reason: string | null }>>({});
  const [publishingItems, setPublishingItems] = useState<PublishingItem[]>([]);
  const [pubSummary, setPubSummary] = useState<PublishingWorkspaceSummary | null>(null);

  const [loading, setLoading] = useState<boolean>(true);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [selectedMetaClip, setSelectedMetaClip] = useState<Clip | null>(null);
  const [exportingZip, setExportingZip] = useState<boolean>(false);
  const [lastZipResult, setLastZipResult] = useState<ExportPackageResult | null>(null);
  const [selectedStatusFilter, setSelectedStatusFilter] = useState<string>("all");
  const [exportingMoments, setExportingMoments] = useState<boolean>(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);

  // Quick edit state for publishing item
  const [savingItemClipId, setSavingItemClipId] = useState<number | null>(null);

  useEffect(() => {
    loadAllData();
  }, []);

  const loadAllData = async () => {
    setLoading(true);
    try {
      // 1. Load clips
      const clipsData = await api.getClips({ page_size: 50 });
      const readyClips = (clipsData || []).filter(
        (c) => c.status === "approved" || c.status === "generated" || c.is_approved
      );
      setClips(readyClips);

      // 2. Load metadata & copyright status in parallel
      const metaEntries: Record<number, ClipMetadata> = {};
      const statusEntries: Record<number, { can_export: boolean; block_reason: string | null }> = {};
      await Promise.all(
        readyClips.map(async (c) => {
          try {
            const m = await api.getClipMetadata(c.id, true);
            metaEntries[c.id] = m;
          } catch (err) {
            console.error(`Failed to load meta for clip ${c.id}`, err);
          }

          try {
            const s = await api.checkClipExportStatus(c.id);
            statusEntries[c.id] = { can_export: s.can_export, block_reason: s.block_reason };
          } catch {
            statusEntries[c.id] = { can_export: false, block_reason: "Unable to verify copyright status" };
          }
        })
      );
      setMetadataMap(metaEntries);
      setStatusMap(statusEntries);

      // 3. Load publishing workspace items & summary
      const [pubItems, summary] = await Promise.all([
        api.getPublishingItems().catch(() => []),
        api.getPublishingSummary().catch(() => null),
      ]);
      setPublishingItems(pubItems);
      setPubSummary(summary);
    } catch (e) {
      console.error("Failed to load export data", e);
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = (text: string, fieldId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldId);
    setTimeout(() => {
      setCopiedField(null);
    }, 2000);
  };

  const handleCreateZipPackage = async () => {
    setExportingZip(true);
    setFeedbackMsg(null);
    try {
      const res = await api.createExportPackageZip({
        include_subtitles_srt: true,
        include_transcripts_txt: true,
        include_metadata_csv: true,
        include_copyright_reports: true,
        include_thumbnails: true,
      });
      setLastZipResult(res);
      setFeedbackMsg({
        type: "success",
        text: `Successfully packaged ${res.clips_exported_count} Shorts into ${res.zip_filename} (${(res.zip_size_bytes / (1024 * 1024)).toFixed(1)} MB)!`,
      });
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err?.message || "Failed to create ZIP package." });
    } finally {
      setExportingZip(false);
    }
  };

  const handleExportBestMoments = async () => {
    if (clips.length === 0) return;
    setExportingMoments(true);
    setFeedbackMsg(null);
    try {
      const recId = clips[0].recording_id;
      const res = await api.exportBestMoments(recId);
      setFeedbackMsg({
        type: "success",
        text: `Exported ${res.exported_count} raw climax segments into GTA6_BEST_MOMENTS folder!`,
      });
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err?.message || "Failed to export best moments." });
    } finally {
      setExportingMoments(false);
    }
  };

  const handleSavePublishingItem = async (item: PublishingItem) => {
    setSavingItemClipId(item.clip_id);
    try {
      await api.updatePublishingItem(item.clip_id, {
        active_title: item.active_title,
        description: item.description,
        hashtags: item.hashtags,
        hook: item.hook || "",
        thumbnail_text: item.thumbnail_text || "",
        status: item.status,
        planned_publish_date: item.planned_publish_date,
        checklist_updates: item.checklist,
      });

      // Refresh items
      const updatedList = await api.getPublishingItems();
      setPublishingItems(updatedList);
      const sum = await api.getPublishingSummary();
      setPubSummary(sum);
      setFeedbackMsg({ type: "success", text: `Publishing details saved for Clip #${item.clip_id}!` });
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err?.message || "Failed to save publishing item." });
    } finally {
      setSavingItemClipId(null);
    }
  };

  const handleSyncAnalytics = async (clipId: number) => {
    try {
      const updated = await api.syncYouTubeAnalytics(clipId);
      setPublishingItems((prev) => prev.map((it) => (it.clip_id === clipId ? updated : it)));
      const sum = await api.getPublishingSummary();
      setPubSummary(sum);
      setFeedbackMsg({
        type: "success",
        text: `Synchronized analytics for Clip #${clipId} (${updated.metrics.views_count.toLocaleString()} views, ${updated.metrics.likes_count.toLocaleString()} likes)!`,
      });
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err?.message || "Failed to sync analytics." });
    }
  };

  const formatBytes = (bytes?: number | null) => {
    if (!bytes) return "0 MB";
    const mb = bytes / (1024 * 1024);
    if (mb < 1024) return `${mb.toFixed(1)} MB`;
    return `${(mb / 1024).toFixed(2)} GB`;
  };

  const filteredPublishingItems = publishingItems.filter((it) => {
    if (selectedStatusFilter === "all") return true;
    return it.status === selectedStatusFilter;
  });

  return (
    <div className="min-h-screen bg-background text-text-primary pb-16">
      <Header
        title="Export Center & Publishing Workspace"
        subtitle="Individual MP4s, bulk ZIP packages, SRT subtitles, TXT transcripts, CSV metadata, and YouTube Shorts publishing tracking."
      />

      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Navigation Tabs */}
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-border pb-3">
          <div className="flex items-center gap-2">
            <button
              onClick={() => setActiveTab("exports")}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
                activeTab === "exports"
                  ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
                  : "text-text-muted hover:text-white"
              }`}
            >
              <Download className="w-4 h-4 text-cyan-400" />
              <span>Production Export Center</span>
            </button>
            <button
              onClick={() => setActiveTab("publishing")}
              className={`px-4 py-2 rounded-xl text-xs font-bold transition-all flex items-center gap-2 ${
                activeTab === "publishing"
                  ? "bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm"
                  : "text-text-muted hover:text-white"
              }`}
            >
              <Youtube className="w-4 h-4 text-red-400" />
              <span>Publishing Workspace ({publishingItems.length})</span>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={loadAllData}
              className="p-2 rounded-xl border border-border bg-surface text-text-muted hover:text-white hover:border-cyan-500 transition-all"
              title="Refresh all data"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin text-cyan-400" : ""}`} />
            </button>
            <Link
              href="/generated-shorts"
              className="px-3 py-1.5 rounded-xl border border-border bg-surface hover:border-cyan-500 text-xs font-semibold text-text-muted hover:text-white transition-all flex items-center gap-1.5"
            >
              <Film className="w-3.5 h-3.5 text-cyan-400" />
              <span>Shorts Player</span>
            </Link>
          </div>
        </div>

        {/* Feedback Message Alert */}
        {feedbackMsg && (
          <div
            className={`p-3.5 rounded-xl border text-xs flex items-center justify-between ${
              feedbackMsg.type === "success"
                ? "border-emerald-500/40 bg-emerald-950/30 text-emerald-300"
                : "border-red-500/40 bg-red-950/30 text-red-300"
            }`}
          >
            <span>{feedbackMsg.text}</span>
            <button onClick={() => setFeedbackMsg(null)} className="text-xs underline ml-4">
              Dismiss
            </button>
          </div>
        )}

        {/* Organized Folders Card */}
        <div className="p-4 rounded-2xl border border-border bg-surface space-y-3 shadow-md">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2.5">
              <Folder className="w-4 h-4 text-amber-400" />
              <h3 className="font-bold text-white text-xs uppercase tracking-wider">
                Organized File System Directories (D:\GTA_CLIPFORGE_AI)
              </h3>
            </div>
            <button
              onClick={handleExportBestMoments}
              disabled={exportingMoments || clips.length === 0}
              className="px-3 py-1.5 rounded-xl border border-amber-500/30 bg-amber-500/10 hover:bg-amber-500/20 text-xs font-semibold text-amber-300 transition-all flex items-center gap-1.5 disabled:opacity-50"
            >
              <Film className="w-3.5 h-3.5 text-amber-400" />
              <span>{exportingMoments ? "Extracting..." : "Export Climax to GTA6_BEST_MOMENTS"}</span>
            </button>
          </div>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
            <div className="p-2.5 rounded-xl bg-background border border-border">
              <span className="text-[10px] text-text-muted block font-sans">Vertical Shorts</span>
              <strong className="text-cyan-400">GTA6_SHORTS/</strong>
            </div>
            <div className="p-2.5 rounded-xl bg-background border border-border">
              <span className="text-[10px] text-text-muted block font-sans">Horizontal Climax Cuts</span>
              <strong className="text-amber-400">GTA6_BEST_MOMENTS/</strong>
            </div>
            <div className="p-2.5 rounded-xl bg-background border border-border">
              <span className="text-[10px] text-text-muted block font-sans">Copyright & Compliance</span>
              <strong className="text-purple-400">GTA6_REPORTS/</strong>
            </div>
            <div className="p-2.5 rounded-xl bg-background border border-border">
              <span className="text-[10px] text-text-muted block font-sans">Packages, ZIPs & CSVs</span>
              <strong className="text-emerald-400">GTA6_EXPORTS/</strong>
            </div>
          </div>
        </div>

        {/* TAB 1: PRODUCTION EXPORT CENTER */}
        {activeTab === "exports" && (
          <div className="space-y-6">
            {/* Export Actions Banner */}
            <div className="p-6 rounded-2xl border border-cyan-500/30 bg-gradient-to-r from-cyan-950/40 via-surface to-surface flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-xl">
              <div className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <Archive className="w-5 h-5 text-cyan-400" />
                  <h3 className="text-base font-bold text-white">Production Shorts Export Engine</h3>
                </div>
                <p className="text-xs text-text-muted max-w-2xl leading-relaxed">
                  Export individual Shorts, extract synchronized <code>.srt</code> subtitles and <code>.txt</code> transcripts, download complete CSV catalog metadata, or package everything into a single ready-to-publish production ZIP archive.
                </p>
              </div>

              <div className="flex flex-wrap items-center gap-2.5 shrink-0">
                <a
                  href="/api/exports/metadata.csv"
                  download
                  className="px-3.5 py-2 rounded-xl border border-border bg-background hover:border-cyan-500 text-xs font-semibold text-white transition-all flex items-center gap-2 shadow-sm"
                >
                  <FileCode className="w-4 h-4 text-emerald-400" />
                  <span>Download Metadata CSV</span>
                </a>

                <button
                  onClick={handleCreateZipPackage}
                  disabled={exportingZip || clips.length === 0}
                  className="px-4 py-2 rounded-xl text-xs font-bold bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-400 hover:to-purple-500 text-white shadow-lg shadow-cyan-500/20 transition-all flex items-center gap-2 disabled:opacity-50"
                >
                  <Archive className="w-4 h-4" />
                  <span>{exportingZip ? "Packaging ZIP..." : "Create Production ZIP Package"}</span>
                </button>
              </div>
            </div>

            {/* Last ZIP Result Callout */}
            {lastZipResult && (
              <div className="p-4 rounded-xl border border-emerald-500/40 bg-emerald-950/20 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 shadow-md">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <h4 className="font-bold text-emerald-300 text-xs">Production ZIP Ready for Download</h4>
                  </div>
                  <span className="text-[11px] text-text-muted font-mono">
                    {lastZipResult.zip_filename} &bull; {formatBytes(lastZipResult.zip_size_bytes)} &bull; {lastZipResult.files_included.length} bundled files
                  </span>
                </div>

                <a
                  href={lastZipResult.zip_download_url}
                  download
                  className="px-4 py-1.5 rounded-lg bg-emerald-500 text-black font-bold text-xs hover:bg-emerald-400 transition-all flex items-center gap-1.5 shadow"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download Archive</span>
                </a>
              </div>
            )}

            {/* Shorts List */}
            <div className="rounded-2xl border border-border bg-surface p-5 space-y-4 shadow-xl">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2">
                  <Film className="w-4 h-4 text-cyan-400" />
                  <h3 className="font-bold text-white text-sm">
                    Generated Shorts Ready for Export ({clips.length})
                  </h3>
                </div>
                <span className="text-xs text-text-muted">
                  Default: <strong className="text-white">1080x1920 (9:16) H.264 AAC</strong>
                </span>
              </div>

              {clips.length === 0 && !loading && (
                <div className="text-center py-12 text-zinc-600 space-y-3">
                  <Film className="w-12 h-12 mx-auto" />
                  <p className="text-sm text-text-muted">No generated shorts found yet.</p>
                  <Link
                    href="/generated-shorts"
                    className="inline-block text-xs text-cyan-400 hover:underline font-semibold"
                  >
                    Go to Generated Shorts to generate clips &rarr;
                  </Link>
                </div>
              )}

              <div className="space-y-4">
                {clips.map((c) => {
                  const meta = metadataMap[c.id];
                  const activeTitle = meta?.title || c.title || "GTA 6 Short";
                  const activeDesc = meta?.description || "";
                  const activeHashtags = meta?.hashtags || "#GTA6 #GTA6Shorts #ViceCity";
                  const activePinned = meta?.pinned_comment || "";
                  const exportStatus = statusMap[c.id];

                  return (
                    <div
                      key={c.id}
                      className="p-5 rounded-2xl border border-border bg-background space-y-4 hover:border-cyan-500/40 transition-all shadow-md"
                    >
                      {/* Top Row: Details & Actions */}
                      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
                        <div className="flex items-center gap-3.5 min-w-0">
                          <div className="w-14 h-20 bg-black rounded-xl overflow-hidden shrink-0 border border-border relative flex items-center justify-center shadow">
                            {c.thumbnail_path ? (
                              <img
                                src={api.getClipThumbnailUrl(c.id)}
                                alt={c.title || "Thumb"}
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <Film className="w-6 h-6 text-zinc-600" />
                            )}
                          </div>

                          <div className="min-w-0 space-y-1">
                            <div className="flex items-center gap-2 flex-wrap">
                              <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300 border border-cyan-500/30">
                                #{c.id}
                              </span>
                              <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 border border-purple-500/30 capitalize">
                                {c.preset_name || c.render_mode?.replace("_", " ") || "Short"}
                              </span>

                              {exportStatus && (
                                exportStatus.can_export ? (
                                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 flex items-center gap-1">
                                    <ShieldCheck className="w-3 h-3 text-emerald-400" />
                                    <span>Export Authorized</span>
                                  </span>
                                ) : (
                                  <Link
                                    href="/copyright-center"
                                    className="text-[10px] font-semibold px-2 py-0.5 rounded bg-red-500/20 text-red-300 border border-red-500/30 flex items-center gap-1 hover:underline"
                                    title={exportStatus.block_reason || "Creator permissions required"}
                                  >
                                    <AlertTriangle className="w-3 h-3 text-red-400" />
                                    <span>Export Blocked</span>
                                  </Link>
                                )
                              )}
                            </div>

                            <h4 className="text-sm font-bold text-white truncate max-w-lg">
                              {activeTitle}
                            </h4>
                            <div className="flex items-center gap-2 text-[11px] text-text-muted font-mono">
                              <span>1080x1920 (9:16)</span>
                              <span>&bull;</span>
                              <span>{c.duration?.toFixed(1)}s</span>
                              <span>&bull;</span>
                              <span>{formatBytes(c.file_size_bytes)}</span>
                            </div>
                          </div>
                        </div>

                        {/* Direct File Download Buttons */}
                        <div className="flex flex-wrap items-center gap-2 shrink-0 self-end sm:self-center">
                          <button
                            type="button"
                            onClick={() => setSelectedMetaClip(c)}
                            className="px-2.5 py-1.5 rounded-lg border border-purple-500/40 bg-purple-500/10 hover:bg-purple-500/20 text-xs font-semibold text-purple-300 transition-all flex items-center gap-1"
                          >
                            <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                            <span>Metadata</span>
                          </button>

                          <a
                            href={`/api/exports/clips/${c.id}/subtitles.srt?download=true`}
                            download
                            className="px-2.5 py-1.5 rounded-lg border border-border bg-surface hover:border-cyan-500 text-xs font-semibold text-text-muted hover:text-white transition-all flex items-center gap-1"
                            title="Download SRT Subtitle File"
                          >
                            <FileCode className="w-3.5 h-3.5 text-cyan-400" />
                            <span>SRT</span>
                          </a>

                          <a
                            href={`/api/exports/clips/${c.id}/transcript.txt?download=true`}
                            download
                            className="px-2.5 py-1.5 rounded-lg border border-border bg-surface hover:border-cyan-500 text-xs font-semibold text-text-muted hover:text-white transition-all flex items-center gap-1"
                            title="Download TXT Transcript"
                          >
                            <FileText className="w-3.5 h-3.5 text-amber-400" />
                            <span>TXT</span>
                          </a>

                          <a
                            href={api.getClipDownloadUrl(c.id)}
                            download
                            className="px-3 py-1.5 rounded-lg border border-cyan-500/40 bg-cyan-500/10 hover:bg-cyan-500/20 text-xs font-semibold text-cyan-300 transition-all flex items-center gap-1.5"
                          >
                            <Download className="w-3.5 h-3.5" />
                            <span>Download MP4</span>
                          </a>
                        </div>
                      </div>

                      {/* Quick-Copy Grid */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3 pt-2 border-t border-border/60">
                        <div className="p-3 rounded-xl border border-border bg-surface/60 flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted block">
                              YouTube Title ({activeTitle.length}/100)
                            </span>
                            <p className="text-xs font-semibold text-white truncate mt-0.5">
                              {activeTitle}
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => copyToClipboard(activeTitle, `title_${c.id}`)}
                            className="px-2.5 py-1 rounded-lg bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 hover:bg-cyan-500/20 text-xs font-semibold transition-all flex items-center gap-1 shrink-0"
                          >
                            {copiedField === `title_${c.id}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                            <span>Copy Title</span>
                          </button>
                        </div>

                        <div className="p-3 rounded-xl border border-border bg-surface/60 flex items-center justify-between gap-3">
                          <div className="min-w-0">
                            <span className="text-[10px] font-bold uppercase tracking-wider text-text-muted block">
                              Hashtags
                            </span>
                            <p className="text-xs font-semibold text-cyan-400 truncate mt-0.5">
                              {activeHashtags}
                            </p>
                          </div>
                          <button
                            type="button"
                            onClick={() => copyToClipboard(activeHashtags, `tags_${c.id}`)}
                            className="px-2.5 py-1 rounded-lg bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 hover:bg-cyan-500/20 text-xs font-semibold transition-all flex items-center gap-1 shrink-0"
                          >
                            {copiedField === `tags_${c.id}` ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                            <span>Copy Tags</span>
                          </button>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: PUBLISHING WORKSPACE */}
        {activeTab === "publishing" && (
          <div className="space-y-6">
            {/* Global Workspace Summary Bar */}
            {pubSummary && (
              <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-3">
                <div className="p-3.5 rounded-xl border border-border bg-surface shadow-sm">
                  <span className="text-[10px] text-text-muted block font-semibold uppercase">Total Shorts</span>
                  <strong className="text-lg text-white font-mono">{pubSummary.total_items}</strong>
                </div>
                <div className="p-3.5 rounded-xl border border-zinc-500/30 bg-surface shadow-sm">
                  <span className="text-[10px] text-zinc-400 block font-semibold uppercase">Draft</span>
                  <strong className="text-lg text-zinc-300 font-mono">{pubSummary.draft_count}</strong>
                </div>
                <div className="p-3.5 rounded-xl border border-emerald-500/30 bg-surface shadow-sm">
                  <span className="text-[10px] text-emerald-400 block font-semibold uppercase">Ready</span>
                  <strong className="text-lg text-emerald-400 font-mono">{pubSummary.ready_count}</strong>
                </div>
                <div className="p-3.5 rounded-xl border border-purple-500/30 bg-surface shadow-sm">
                  <span className="text-[10px] text-purple-400 block font-semibold uppercase">Scheduled</span>
                  <strong className="text-lg text-purple-400 font-mono">{pubSummary.scheduled_count}</strong>
                </div>
                <div className="p-3.5 rounded-xl border border-red-500/30 bg-surface shadow-sm">
                  <span className="text-[10px] text-red-400 block font-semibold uppercase">Published</span>
                  <strong className="text-lg text-red-400 font-mono">{pubSummary.published_count}</strong>
                </div>
                <div className="p-3.5 rounded-xl border border-cyan-500/30 bg-surface shadow-sm">
                  <span className="text-[10px] text-cyan-400 block font-semibold uppercase">Total Views</span>
                  <strong className="text-lg text-cyan-400 font-mono">{pubSummary.total_views.toLocaleString()}</strong>
                </div>
                <div className="p-3.5 rounded-xl border border-amber-500/30 bg-surface shadow-sm">
                  <span className="text-[10px] text-amber-400 block font-semibold uppercase">Watch Time (h)</span>
                  <strong className="text-lg text-amber-400 font-mono">{pubSummary.total_watch_hours.toFixed(1)}h</strong>
                </div>
              </div>
            )}

            {/* Filter Bar */}
            <div className="p-4 rounded-xl border border-border bg-surface flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 shadow-md">
              <div className="flex items-center gap-2 overflow-x-auto pb-1 sm:pb-0 w-full sm:w-auto">
                <span className="text-xs font-semibold text-text-muted shrink-0">Filter Status:</span>
                {(["all", "draft", "ready", "scheduled", "published", "archived"] as const).map((st) => (
                  <button
                    key={st}
                    onClick={() => setSelectedStatusFilter(st)}
                    className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all capitalize ${
                      selectedStatusFilter === st
                        ? "bg-cyan-500 text-black font-bold shadow-sm"
                        : "bg-background border border-border text-text-muted hover:text-white"
                    }`}
                  >
                    {st}
                  </button>
                ))}
              </div>

              <span className="text-xs text-text-muted font-mono">
                Showing {filteredPublishingItems.length} of {publishingItems.length} items
              </span>
            </div>

            {/* Publishing Items List */}
            <div className="space-y-6">
              {filteredPublishingItems.length === 0 && (
                <div className="p-12 text-center border border-border rounded-2xl bg-surface text-text-muted text-xs">
                  No publishing items found for status filter &ldquo;{selectedStatusFilter}&rdquo;.
                </div>
              )}

              {filteredPublishingItems.map((item) => (
                <div
                  key={item.id}
                  className="p-6 rounded-2xl border border-border bg-surface space-y-5 shadow-xl hover:border-cyan-500/30 transition-all"
                >
                  {/* Top Bar: Title, Status, Planned Schedule */}
                  <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4 border-b border-border/60 pb-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-16 bg-black rounded-lg overflow-hidden shrink-0 border border-border relative flex items-center justify-center shadow">
                        {item.thumbnail_url ? (
                          <img
                            src={item.thumbnail_url}
                            alt={item.active_title}
                            className="w-full h-full object-cover"
                          />
                        ) : (
                          <Film className="w-5 h-5 text-zinc-600" />
                        )}
                      </div>

                      <div className="space-y-1">
                        <div className="flex items-center gap-2">
                          <span className="text-[10px] font-mono font-bold px-1.5 py-0.5 rounded bg-cyan-500/20 text-cyan-300">
                            Clip #{item.clip_id}
                          </span>
                          <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-purple-500/20 text-purple-300">
                            {item.preset_name || "Short"}
                          </span>
                          <span
                            className={`text-[10px] uppercase font-bold px-2 py-0.5 rounded ${
                              item.status === "published"
                                ? "bg-red-500/20 text-red-300 border border-red-500/30"
                                : item.status === "ready"
                                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30"
                                : item.status === "scheduled"
                                ? "bg-purple-500/20 text-purple-300 border border-purple-500/30"
                                : "bg-zinc-700/30 text-zinc-300 border border-zinc-600/30"
                            }`}
                          >
                            {item.status}
                          </span>
                        </div>

                        <h3 className="font-bold text-white text-sm max-w-xl truncate">
                          {item.active_title}
                        </h3>
                      </div>
                    </div>

                    {/* Status & Schedule Selectors */}
                    <div className="flex flex-wrap items-center gap-3 self-end lg:self-center text-xs">
                      <div>
                        <label className="text-[10px] text-text-muted block font-semibold mb-0.5">Status</label>
                        <select
                          value={item.status}
                          onChange={(e) => {
                            const newStatus = e.target.value as PublishingStatus;
                            setPublishingItems((prev) =>
                              prev.map((it) => (it.id === item.id ? { ...it, status: newStatus } : it))
                            );
                          }}
                          className="px-2.5 py-1.5 rounded-lg bg-background border border-border text-white text-xs focus:outline-none focus:border-cyan-500"
                        >
                          <option value="draft">Draft</option>
                          <option value="ready">Ready to Publish</option>
                          <option value="scheduled">Scheduled</option>
                          <option value="published">Published</option>
                          <option value="archived">Archived</option>
                        </select>
                      </div>

                      <div>
                        <label className="text-[10px] text-text-muted block font-semibold mb-0.5">Publish Date</label>
                        <input
                          type="datetime-local"
                          value={item.planned_publish_date ? new Date(item.planned_publish_date).toISOString().substring(0, 16) : ""}
                          onChange={(e) => {
                            const val = e.target.value ? new Date(e.target.value).toISOString() : null;
                            setPublishingItems((prev) =>
                              prev.map((it) => (it.id === item.id ? { ...it, planned_publish_date: val } : it))
                            );
                          }}
                          className="px-2.5 py-1.5 rounded-lg bg-background border border-border text-white text-xs focus:outline-none focus:border-cyan-500"
                        />
                      </div>

                      <button
                        onClick={() => handleSavePublishingItem(item)}
                        disabled={savingItemClipId === item.clip_id}
                        className="px-3.5 py-1.5 rounded-lg bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white font-bold text-xs shadow-md transition-all flex items-center gap-1.5 mt-3 self-end disabled:opacity-50"
                      >
                        <Save className="w-3.5 h-3.5" />
                        <span>{savingItemClipId === item.clip_id ? "Saving..." : "Save"}</span>
                      </button>
                    </div>
                  </div>

                  {/* 3-Column Content & Metrics Grid */}
                  <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
                    {/* Left 5 Cols: Draft Titles Selector & Metadata */}
                    <div className="lg:col-span-5 space-y-3 text-xs">
                      {/* Draft Titles Selector */}
                      <div>
                        <label className="text-text-muted font-semibold block mb-1">
                          Draft Titles ({item.draft_titles.length} Suggestions)
                        </label>
                        <select
                          value={item.active_title}
                          onChange={(e) => {
                            const newTitle = e.target.value;
                            setPublishingItems((prev) =>
                              prev.map((it) => (it.id === item.id ? { ...it, active_title: newTitle } : it))
                            );
                          }}
                          className="w-full px-3 py-2 rounded-lg bg-background border border-border text-white text-xs focus:outline-none focus:border-cyan-500"
                        >
                          {item.draft_titles.map((t, idx) => (
                            <option key={idx} value={t}>
                              #{idx + 1}: {t}
                            </option>
                          ))}
                        </select>
                      </div>

                      {/* Custom Active Title */}
                      <div>
                        <div className="flex items-center justify-between text-[10px] text-text-muted mb-1">
                          <span>Active YouTube Title</span>
                          <span className={item.active_title.length > 100 ? "text-red-400" : "text-cyan-400"}>
                            {item.active_title.length}/100 chars
                          </span>
                        </div>
                        <input
                          type="text"
                          value={item.active_title}
                          onChange={(e) => {
                            const val = e.target.value;
                            setPublishingItems((prev) =>
                              prev.map((it) => (it.id === item.id ? { ...it, active_title: val } : it))
                            );
                          }}
                          className="w-full px-3 py-2 rounded-lg bg-background border border-border text-white text-xs focus:outline-none focus:border-cyan-500"
                        />
                      </div>

                      {/* Hashtags */}
                      <div>
                        <label className="text-text-muted font-semibold block mb-1">Hashtags</label>
                        <input
                          type="text"
                          value={item.hashtags}
                          onChange={(e) => {
                            const val = e.target.value;
                            setPublishingItems((prev) =>
                              prev.map((it) => (it.id === item.id ? { ...it, hashtags: val } : it))
                            );
                          }}
                          className="w-full px-3 py-2 rounded-lg bg-background border border-border text-cyan-300 text-xs focus:outline-none focus:border-cyan-500"
                        />
                      </div>

                      {/* Spoken Hook */}
                      <div>
                        <label className="text-text-muted font-semibold block mb-1">Spoken Opening Hook</label>
                        <input
                          type="text"
                          value={item.hook || ""}
                          onChange={(e) => {
                            const val = e.target.value;
                            setPublishingItems((prev) =>
                              prev.map((it) => (it.id === item.id ? { ...it, hook: val } : it))
                            );
                          }}
                          className="w-full px-3 py-2 rounded-lg bg-background border border-border text-white text-xs focus:outline-none focus:border-cyan-500"
                        />
                      </div>
                    </div>

                    {/* Middle 4 Cols: Publishing Checklist */}
                    <div className="lg:col-span-4 p-4 rounded-xl border border-border bg-background space-y-3">
                      <div className="flex items-center justify-between border-b border-border/60 pb-2">
                        <div className="flex items-center gap-1.5">
                          <FileCheck className="w-4 h-4 text-cyan-400" />
                          <h4 className="font-bold text-white text-xs">Publishing Checklist</h4>
                        </div>
                        <span className="text-[10px] font-mono text-cyan-300 font-bold">
                          {item.checklist_completion_pct}% Complete
                        </span>
                      </div>

                      {/* Checklist items */}
                      <div className="space-y-2 text-xs">
                        {Object.entries(item.checklist).map(([key, val]) => (
                          <label key={key} className="flex items-center gap-2 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={val}
                              onChange={(e) => {
                                const newChecked = e.target.checked;
                                setPublishingItems((prev) =>
                                  prev.map((it) => {
                                    if (it.id !== item.id) return it;
                                    const nextChk = { ...it.checklist, [key]: newChecked };
                                    const passed = Object.values(nextChk).filter(Boolean).length;
                                    const pct = Math.round((passed / Object.keys(nextChk).length) * 100);
                                    return { ...it, checklist: nextChk, checklist_completion_pct: pct };
                                  })
                                );
                              }}
                              className="rounded border-border text-cyan-500 focus:ring-0"
                            />
                            <span className={`text-[11px] ${val ? "text-text-primary" : "text-text-muted"}`}>
                              {key.replace(/_/g, " ").replace(/\b\w/g, (l) => l.toUpperCase())}
                            </span>
                          </label>
                        ))}
                      </div>
                    </div>

                    {/* Right 3 Cols: Performance Metrics */}
                    <div className="lg:col-span-3 p-4 rounded-xl border border-border bg-background space-y-3">
                      <div className="flex items-center justify-between border-b border-border/60 pb-2">
                        <div className="flex items-center gap-1.5">
                          <BarChart2 className="w-4 h-4 text-emerald-400" />
                          <h4 className="font-bold text-white text-xs">Performance Metrics</h4>
                        </div>
                        <button
                          onClick={() => handleSyncAnalytics(item.clip_id)}
                          className="text-[10px] text-cyan-400 hover:text-cyan-300 flex items-center gap-1 underline font-semibold"
                          title="Simulate / sync realistic YouTube analytics"
                        >
                          <Zap className="w-3 h-3 text-cyan-400" />
                          <span>Sync Data</span>
                        </button>
                      </div>

                      <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                        <div className="p-2 rounded-lg bg-surface border border-border/60">
                          <span className="text-[10px] text-text-muted block font-sans">Views</span>
                          <strong className="text-white">{item.metrics.views_count.toLocaleString()}</strong>
                        </div>
                        <div className="p-2 rounded-lg bg-surface border border-border/60">
                          <span className="text-[10px] text-text-muted block font-sans">Likes</span>
                          <strong className="text-emerald-400">{item.metrics.likes_count.toLocaleString()}</strong>
                        </div>
                        <div className="p-2 rounded-lg bg-surface border border-border/60">
                          <span className="text-[10px] text-text-muted block font-sans">Comments</span>
                          <strong className="text-cyan-400">{item.metrics.comments_count.toLocaleString()}</strong>
                        </div>
                        <div className="p-2 rounded-lg bg-surface border border-border/60">
                          <span className="text-[10px] text-text-muted block font-sans">Retention</span>
                          <strong className="text-purple-400">{item.metrics.avg_view_duration_pct.toFixed(0)}%</strong>
                        </div>
                      </div>

                      <div className="pt-2 text-[10px] text-text-muted font-mono flex items-center justify-between">
                        <span>Source: <strong>{item.analytics_source}</strong></span>
                        <span>Watch: <strong>{item.metrics.watch_time_hours.toFixed(1)}h</strong></span>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Metadata Edit Modal */}
      {selectedMetaClip && (
        <MetadataModal
          clip={selectedMetaClip}
          isOpen={Boolean(selectedMetaClip)}
          onClose={() => setSelectedMetaClip(null)}
          onSaved={(updated) => {
            setMetadataMap((prev) => ({ ...prev, [selectedMetaClip.id]: updated }));
            setSelectedMetaClip(null);
          }}
        />
      )}
    </div>
  );
}
