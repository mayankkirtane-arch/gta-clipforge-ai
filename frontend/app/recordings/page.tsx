"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Film,
  Upload,
  FolderOpen,
  RefreshCw,
  Search,
  Trash2,
  Play,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  Clock,
  HardDrive,
  Monitor,
  Eye,
  Pause,
  PlayCircle,
  X,
  FileVideo,
  Hash,
  Info,
  Sparkles,
  Youtube,
  Download,
  ExternalLink,
} from "lucide-react";
import { api, Recording, WatcherSettings, YouTubeVideoInfo, YouTubeTask } from "@/lib/api";
import { formatBytes, formatDuration, formatRelativeTime } from "@/lib/utils";

const statusBadgeVariant: Record<string, "default" | "warning" | "success" | "error"> = {
  pending: "default",
  analyzing: "warning",
  analyzed: "success",
  failed: "error",
};

export default function RecordingsPage() {
  const router = useRouter();
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(10);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedStatus, setSelectedStatus] = useState<string>("all");

  // Watcher state
  const [watcherSettings, setWatcherSettings] = useState<WatcherSettings | null>(null);
  const [scanning, setScanning] = useState(false);
  const [togglingWatcher, setTogglingWatcher] = useState(false);

  // Modals
  const [importModalOpen, setImportModalOpen] = useState(false);
  const [selectedRecording, setSelectedRecording] = useState<Recording | null>(null);
  const [deleteConfirmRec, setDeleteConfirmRec] = useState<Recording | null>(null);
  const [deleteDiskFile, setDeleteDiskFile] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [toastMessage, setToastMessage] = useState<{ text: string; type: "success" | "error" | "info" } | null>(null);

  // Import form state
  const [importTab, setImportTab] = useState<"upload" | "local" | "youtube">("youtube");
  const [localFilePath, setLocalFilePath] = useState("");
  const [localNotes, setLocalNotes] = useState("");
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadNotes, setUploadNotes] = useState("");
  const [uploading, setUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // YouTube link import state
  const [youtubeUrl, setYoutubeUrl] = useState("");
  const [youtubeInfo, setYoutubeInfo] = useState<YouTubeVideoInfo | null>(null);
  const [fetchingYtInfo, setFetchingYtInfo] = useState(false);
  const [autoGenerateShorts, setAutoGenerateShorts] = useState(true);
  const [hasPermission, setHasPermission] = useState(true);
  const [creatorName, setCreatorName] = useState("");
  const [ytTask, setYtTask] = useState<YouTubeTask | null>(null);
  const [ytDownloading, setYtDownloading] = useState(false);

  const showToast = (text: string, type: "success" | "error" | "info" = "info") => {
    setToastMessage({ text, type });
    setTimeout(() => setToastMessage(null), 5000);
  };

  const loadRecordings = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.getRecordings(page, pageSize, selectedStatus, searchQuery);
      setRecordings(res.items);
      setTotal(res.total);
    } catch (err: any) {
      // Backend might be offline
    } finally {
      setLoading(false);
    }
  }, [page, pageSize, selectedStatus, searchQuery]);

  const loadWatcherConfig = useCallback(async () => {
    try {
      const w = await api.getWatcherSettings();
      setWatcherSettings(w);
    } catch {}
  }, []);

  useEffect(() => {
    loadRecordings();
  }, [loadRecordings]);

  useEffect(() => {
    loadWatcherConfig();
    const interval = setInterval(loadWatcherConfig, 10000);
    return () => clearInterval(interval);
  }, [loadWatcherConfig]);

  // Periodic poll for processing recordings status changes
  useEffect(() => {
    const hasActive = recordings.some((r) => r.status === "analyzing" || r.status === "pending");
    if (!hasActive) return;
    const interval = setInterval(loadRecordings, 4000);
    return () => clearInterval(interval);
  }, [recordings, loadRecordings]);

  // Watcher pause/resume
  const handleToggleWatcher = async () => {
    if (!watcherSettings) return;
    setTogglingWatcher(true);
    try {
      if (watcherSettings.monitoring_paused) {
        await api.resumeWatcher();
        showToast("Folder monitoring resumed on GTA6_RECORDINGS", "success");
      } else {
        await api.pauseWatcher();
        showToast("Folder monitoring paused", "info");
      }
      await loadWatcherConfig();
    } catch (err: any) {
      showToast(err.message || "Failed to toggle watcher", "error");
    } finally {
      setTogglingWatcher(false);
    }
  };

  // Manual folder scan
  const handleScanFolder = async () => {
    setScanning(true);
    try {
      const res = await api.scanWatcherFolder();
      showToast(`Scan complete: ${res.new_recordings_found} new recording(s) indexed.`, "success");
      await loadRecordings();
    } catch (err: any) {
      showToast(err.message || "Scan failed", "error");
    } finally {
      setScanning(false);
    }
  };

  // Handle local import
  const handleImportLocal = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!localFilePath.trim()) return;
    setUploading(true);
    try {
      const rec = await api.importLocalRecording(localFilePath.trim(), localNotes.trim());
      showToast(`Successfully imported ${rec.original_filename}!`, "success");
      setImportModalOpen(false);
      setLocalFilePath("");
      setLocalNotes("");
      await loadRecordings();
    } catch (err: any) {
      showToast(err.message || "Failed to import video", "error");
    } finally {
      setUploading(false);
    }
  };

  // Handle file upload
  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!uploadFile) return;
    setUploading(true);
    try {
      const rec = await api.uploadRecording(uploadFile, uploadNotes.trim());
      showToast(`Uploaded ${rec.original_filename} successfully!`, "success");
      setImportModalOpen(false);
      setUploadFile(null);
      setUploadNotes("");
      if (fileInputRef.current) fileInputRef.current.value = "";
      await loadRecordings();
    } catch (err: any) {
      showToast(err.message || "Upload failed", "error");
    } finally {
      setUploading(false);
    }
  };

  // Auto-detect YouTube query param on mount
  useEffect(() => {
    if (typeof window !== "undefined") {
      const params = new URLSearchParams(window.location.search);
      if (params.get("action") === "youtube") {
        setImportTab("youtube");
        setImportModalOpen(true);
      }
    }
  }, []);

  // Fetch YouTube Info Preview
  const handleFetchYouTubeInfo = async (urlToFetch?: string) => {
    const targetUrl = (urlToFetch || youtubeUrl).trim();
    if (!targetUrl) return;
    setFetchingYtInfo(true);
    try {
      const info = await api.getYouTubeInfo(targetUrl);
      setYoutubeInfo(info);
      if (!creatorName) setCreatorName(info.uploader);
      showToast(`Found: "${info.title}" (${info.duration_formatted})`, "info");
    } catch (err: any) {
      showToast(err.message || "Failed to fetch YouTube info", "error");
      setYoutubeInfo(null);
    } finally {
      setFetchingYtInfo(false);
    }
  };

  // Start YouTube Download & Pipeline
  const handleImportYouTube = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!youtubeUrl.trim()) return;
    setYtDownloading(true);
    try {
      const task = await api.importYouTubeVideo({
        url: youtubeUrl.trim(),
        auto_generate_shorts: autoGenerateShorts,
        notes: youtubeInfo?.description ? `YouTube description: ${youtubeInfo.description.slice(0, 150)}...` : undefined,
        has_permission: hasPermission,
        creator_name: creatorName.trim() || undefined,
      });
      setYtTask(task);
      showToast("Download started! Streaming high-quality video from YouTube...", "info");
    } catch (err: any) {
      showToast(err.message || "Failed to start YouTube download", "error");
      setYtDownloading(false);
    }
  };

  // Poll active YouTube task
  useEffect(() => {
    if (!ytDownloading || !ytTask || ytTask.status === "completed" || ytTask.status === "failed" || ytTask.status === "cancelled") {
      return;
    }

    const interval = setInterval(async () => {
      try {
        const updated = await api.getYouTubeTask(ytTask.task_id);
        setYtTask(updated);

        if (updated.status === "completed") {
          setYtDownloading(false);
          showToast(`Downloaded and started Shorts pipeline for "${updated.title}"!`, "success");
          loadRecordings();
        } else if (updated.status === "failed") {
          setYtDownloading(false);
          showToast(`Download failed: ${updated.error || updated.message}`, "error");
        } else if (updated.status === "cancelled") {
          setYtDownloading(false);
          showToast("Download was cancelled.", "info");
        }
      } catch (err) {
        // network glitch
      }
    }, 1500);

    return () => clearInterval(interval);
  }, [ytDownloading, ytTask, loadRecordings]);

  // Cancel YouTube task
  const handleCancelYtTask = async () => {
    if (!ytTask) return;
    try {
      await api.cancelYouTubeTask(ytTask.task_id);
      setYtDownloading(false);
      showToast("Download cancelled", "info");
    } catch (err: any) {
      showToast(err.message || "Failed to cancel", "error");
    }
  };

  // Reprocess recording
  const handleReprocess = async (rec: Recording) => {
    setActionLoading(true);
    try {
      await api.reprocessRecording(rec.id);
      showToast(`Reprocessing queued for ${rec.original_filename}`, "success");
      await loadRecordings();
      if (selectedRecording?.id === rec.id) {
        setSelectedRecording((prev) => (prev ? { ...prev, status: "pending" } : null));
      }
    } catch (err: any) {
      showToast(err.message || "Failed to reprocess", "error");
    } finally {
      setActionLoading(false);
    }
  };

  // Delete recording
  const handleDeleteConfirm = async () => {
    if (!deleteConfirmRec) return;
    setActionLoading(true);
    try {
      await api.deleteRecording(deleteConfirmRec.id, deleteDiskFile);
      showToast(`Deleted ${deleteConfirmRec.original_filename}`, "success");
      setDeleteConfirmRec(null);
      if (selectedRecording?.id === deleteConfirmRec.id) {
        setSelectedRecording(null);
      }
      await loadRecordings();
    } catch (err: any) {
      showToast(err.message || "Failed to delete recording", "error");
    } finally {
      setActionLoading(false);
    }
  };

  return (
    <div>
      <Header
        title="Recordings"
        subtitle="Manual import and automatic GTA6_RECORDINGS watcher management"
      />

      <div className="p-6 space-y-6 max-w-7xl">
        {/* Toast Notification */}
        {toastMessage && (
          <div
            className={`p-3.5 rounded-lg border text-sm flex items-center justify-between transition-all ${
              toastMessage.type === "success"
                ? "bg-green-950/40 border-green-700/50 text-green-300"
                : toastMessage.type === "error"
                ? "bg-red-950/40 border-red-700/50 text-red-300"
                : "bg-blue-950/40 border-blue-700/50 text-blue-300"
            }`}
          >
            <span>{toastMessage.text}</span>
            <button onClick={() => setToastMessage(null)} className="opacity-70 hover:opacity-100">
              <X className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Watcher Banner & Quick Controls */}
        <div className="p-4 rounded-xl bg-surface-2 border border-border flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <div className="p-2.5 rounded-lg bg-surface-3 border border-border/60">
              <FolderOpen className="w-5 h-5 text-primary-light" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-sm font-semibold text-text-primary">
                  Watch Folder: GTA6_RECORDINGS
                </span>
                {watcherSettings?.monitoring_paused ? (
                  <Badge variant="warning">Monitoring Paused</Badge>
                ) : (
                  <Badge variant="success">Watcher Active</Badge>
                )}
              </div>
              <p className="text-xs text-text-muted mt-0.5 font-mono">
                {watcherSettings?.watch_folder_path || "D:\\GTA_CLIPFORGE_AI\\GTA6_RECORDINGS"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2 self-stretch sm:self-auto">
            <Button
              variant="outline"
              size="sm"
              onClick={handleToggleWatcher}
              disabled={togglingWatcher}
            >
              {watcherSettings?.monitoring_paused ? (
                <>
                  <PlayCircle className="w-3.5 h-3.5 mr-1.5 text-success" /> Resume Watcher
                </>
              ) : (
                <>
                  <Pause className="w-3.5 h-3.5 mr-1.5 text-warning" /> Pause Watcher
                </>
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={handleScanFolder}
              disabled={scanning}
            >
              <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${scanning ? "animate-spin" : ""}`} />
              Scan Folder
            </Button>
            <Button
              variant="default"
              size="sm"
              onClick={() => setImportModalOpen(true)}
            >
              <Upload className="w-3.5 h-3.5 mr-1.5" /> Import Video
            </Button>
          </div>
        </div>

        {/* Filter & Search Bar */}
        <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
          <div className="relative w-full sm:w-80">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
            <input
              type="text"
              placeholder="Search recordings by name or notes..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-3 py-2 text-xs rounded-lg bg-surface border border-border text-text-primary focus:outline-none focus:border-primary placeholder:text-text-muted"
            />
          </div>

          <div className="flex items-center gap-2 w-full sm:w-auto">
            <span className="text-xs text-text-muted whitespace-nowrap">Filter Status:</span>
            <select
              value={selectedStatus}
              onChange={(e) => setSelectedStatus(e.target.value)}
              className="px-3 py-2 text-xs rounded-lg bg-surface border border-border text-text-primary focus:outline-none focus:border-primary"
            >
              <option value="all">All Statuses ({total})</option>
              <option value="pending">Pending</option>
              <option value="analyzing">Analyzing</option>
              <option value="analyzed">Analyzed</option>
              <option value="failed">Failed</option>
            </select>
          </div>
        </div>

        {/* Recordings Table */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between w-full">
              <CardTitle>Gameplay Recordings ({total})</CardTitle>
              <span className="text-xs text-text-muted">
                Supported: MP4, MKV, MOV, WebM (Long 1–8h recordings supported)
              </span>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-3">
                {[...Array(4)].map((_, i) => (
                  <div key={i} className="h-16 bg-surface-2 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : recordings.length === 0 ? (
              <div className="text-center py-16 px-4">
                <Film className="w-12 h-12 text-text-muted mx-auto mb-3 opacity-25" />
                <h4 className="text-sm font-semibold text-text-secondary">No recordings found</h4>
                <p className="text-xs text-text-muted mt-1 max-w-sm mx-auto">
                  Import a GTA 6 recording manually, or drop video files directly into{" "}
                  <code className="text-primary-light">GTA6_RECORDINGS</code> to watch them automatically index.
                </p>
                <div className="mt-4 flex items-center justify-center gap-2">
                  <Button size="sm" onClick={() => setImportModalOpen(true)}>
                    <Upload className="w-3.5 h-3.5 mr-1.5" /> Import Video Now
                  </Button>
                  <Button variant="outline" size="sm" onClick={handleScanFolder}>
                    <RefreshCw className="w-3.5 h-3.5 mr-1.5" /> Scan Watch Folder
                  </Button>
                </div>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-surface-2/60 text-text-muted border-b border-border/60 uppercase font-mono text-[10px]">
                    <tr>
                      <th className="py-3 px-4">Filename</th>
                      <th className="py-3 px-3">Duration</th>
                      <th className="py-3 px-3">Resolution</th>
                      <th className="py-3 px-3">FPS</th>
                      <th className="py-3 px-3">File Size</th>
                      <th className="py-3 px-3">Import Date</th>
                      <th className="py-3 px-3">Status</th>
                      <th className="py-3 px-4 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-border/40">
                    {recordings.map((rec) => (
                      <tr
                        key={rec.id}
                        className="hover:bg-surface-2/40 transition-colors group cursor-pointer"
                        onClick={() => setSelectedRecording(rec)}
                      >
                        <td className="py-3.5 px-4 max-w-[220px]">
                          <div className="flex items-center gap-2.5">
                            <div className="p-2 rounded bg-surface-3 flex-shrink-0">
                              <Film className="w-4 h-4 text-primary-light" />
                            </div>
                            <div className="min-w-0">
                              <p className="font-semibold text-text-primary truncate" title={rec.original_filename}>
                                {rec.original_filename}
                              </p>
                              {rec.video_codec && (
                                <span className="text-[10px] text-text-muted font-mono uppercase">
                                  {rec.video_codec}
                                </span>
                              )}
                            </div>
                          </div>
                        </td>

                        <td className="py-3.5 px-3 font-mono text-text-secondary whitespace-nowrap">
                          {rec.duration_seconds ? formatDuration(rec.duration_seconds) : "—"}
                        </td>

                        <td className="py-3.5 px-3 font-mono text-text-secondary whitespace-nowrap">
                          {rec.resolution || "—"}
                        </td>

                        <td className="py-3.5 px-3 font-mono text-text-secondary whitespace-nowrap">
                          {rec.fps ? `${rec.fps} fps` : "—"}
                        </td>

                        <td className="py-3.5 px-3 font-mono text-text-secondary whitespace-nowrap">
                          {rec.file_size_bytes ? formatBytes(rec.file_size_bytes) : "—"}
                        </td>

                        <td className="py-3.5 px-3 text-text-muted whitespace-nowrap">
                          {rec.created_at ? formatRelativeTime(rec.created_at) : "—"}
                        </td>

                        <td className="py-3.5 px-3 whitespace-nowrap">
                          <Badge variant={statusBadgeVariant[rec.status] || "default"}>
                            {rec.status}
                          </Badge>
                        </td>

                        <td className="py-3.5 px-4 text-right whitespace-nowrap" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-end gap-1">
                            <button
                              onClick={() => router.push(`/recordings/${rec.id}`)}
                              title="Open Video Analysis & Timeline"
                              className="p-1.5 rounded hover:bg-surface-3 text-text-muted hover:text-electric transition-colors"
                            >
                              <Sparkles className="w-4 h-4 text-primary-light" />
                            </button>
                            <button
                              onClick={() => setSelectedRecording(rec)}
                              title="View Details"
                              className="p-1.5 rounded hover:bg-surface-3 text-text-muted hover:text-text-primary transition-colors"
                            >
                              <Eye className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => handleReprocess(rec)}
                              title="Reprocess AI Analysis"
                              className="p-1.5 rounded hover:bg-surface-3 text-text-muted hover:text-primary transition-colors"
                            >
                              <RotateCcw className="w-4 h-4" />
                            </button>
                            <button
                              onClick={() => setDeleteConfirmRec(rec)}
                              title="Delete Recording"
                              className="p-1.5 rounded hover:bg-surface-3 text-text-muted hover:text-error transition-colors"
                            >
                              <Trash2 className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* IMPORT VIDEO MODAL */}
        {importModalOpen && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 sm:p-4">
            <div className="bg-surface border border-border rounded-xl w-full max-w-xl max-h-[92vh] flex flex-col overflow-hidden shadow-2xl">
              <div className="p-4 border-b border-border flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Upload className="w-5 h-5 text-primary-light" />
                  <h3 className="text-base font-semibold text-text-primary">Manual Video Import</h3>
                </div>
                <button
                  onClick={() => setImportModalOpen(false)}
                  className="p-1 rounded hover:bg-surface-2 text-text-muted hover:text-text-primary"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              {/* Tabs */}
              <div className="flex border-b border-border bg-surface-2/40 px-4 pt-2 gap-2 overflow-x-auto">
                <button
                  className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                    importTab === "youtube"
                      ? "border-red-500 text-red-400 font-bold"
                      : "border-transparent text-text-muted hover:text-text-primary"
                  }`}
                  onClick={() => setImportTab("youtube")}
                >
                  <Youtube className="w-3.5 h-3.5 text-red-500" />
                  YouTube Link (Auto-Shorts)
                </button>
                <button
                  className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                    importTab === "upload"
                      ? "border-primary text-primary-light"
                      : "border-transparent text-text-muted hover:text-text-primary"
                  }`}
                  onClick={() => setImportTab("upload")}
                >
                  <Upload className="w-3.5 h-3.5" />
                  File Upload (MP4, MKV)
                </button>
                <button
                  className={`pb-2.5 px-3 text-xs font-semibold border-b-2 transition-colors flex items-center gap-1.5 whitespace-nowrap ${
                    importTab === "local"
                      ? "border-primary text-primary-light"
                      : "border-transparent text-text-muted hover:text-text-primary"
                  }`}
                  onClick={() => setImportTab("local")}
                >
                  <HardDrive className="w-3.5 h-3.5" />
                  Local D: Drive (1–8h)
                </button>
              </div>

              <div className="p-4 sm:p-5 overflow-y-auto flex-1">
                {importTab === "youtube" ? (
                  <div className="space-y-4">
                    {ytTask ? (
                      /* Live Download & Pipeline Progress View */
                      <div className="p-4 rounded-xl border border-red-500/30 bg-surface-2 space-y-3">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {ytTask.status === "failed" ? (
                              <AlertTriangle className="w-4 h-4 text-red-500" />
                            ) : ytTask.status === "completed" ? (
                              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                            ) : (
                              <RefreshCw className="w-4 h-4 text-red-400 animate-spin" />
                            )}
                            <span className="text-xs font-semibold text-text-primary">
                              {ytTask.status === "downloading"
                                ? "Downloading YouTube Video..."
                                : ytTask.status === "processing"
                                ? "Merging High-Quality Streams & Validating..."
                                : ytTask.status === "completed"
                                ? "Download Complete & Processing Started!"
                                : ytTask.status === "failed"
                                ? "Download Failed"
                                : "Processing YouTube Task..."}
                            </span>
                          </div>
                          <Badge
                            variant={
                              ytTask.status === "completed"
                                ? "success"
                                : ytTask.status === "failed"
                                ? "error"
                                : "warning"
                            }
                          >
                            {ytTask.status === "failed"
                              ? "Error"
                              : ytTask.status === "completed"
                              ? "100%"
                              : ytTask.speed_str || `${ytTask.progress}%`}
                          </Badge>
                        </div>

                        {/* Progress Bar (visible during downloading / processing / completed) */}
                        {ytTask.status !== "failed" && (
                          <div className="w-full bg-surface-3 rounded-full h-2.5 overflow-hidden">
                            <div
                              className="bg-gradient-to-r from-red-500 to-primary-light h-2.5 rounded-full transition-all duration-300"
                              style={{ width: `${Math.max(5, ytTask.progress)}%` }}
                            />
                          </div>
                        )}

                        {/* Error Message Box */}
                        {ytTask.status === "failed" && (
                          <div className="p-3 rounded-lg border border-red-500/40 bg-red-950/20 text-xs text-red-300 space-y-1">
                            <p className="font-semibold text-red-200">Unable to complete YouTube download:</p>
                            <p className="text-[11px] font-mono break-all text-red-400">
                              {ytTask.error || ytTask.message}
                            </p>
                          </div>
                        )}

                        <div className="flex items-center justify-between text-[11px] text-text-muted">
                          <span className="truncate max-w-sm">{ytTask.message}</span>
                          {ytTask.eta_seconds > 0 && ytTask.status === "downloading" && (
                            <span className="font-mono">ETA: {ytTask.eta_seconds}s</span>
                          )}
                        </div>

                        {/* Completed Success Actions */}
                        {ytTask.status === "completed" && (
                          <div className="pt-2 flex flex-wrap items-center justify-between border-t border-border mt-2 gap-2">
                            <span className="text-xs text-emerald-400 flex items-center gap-1 font-medium">
                              <CheckCircle2 className="w-3.5 h-3.5" /> Video added & Shorts Generator active!
                            </span>
                            <div className="flex gap-2">
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => {
                                  setYtTask(null);
                                  setYoutubeUrl("");
                                  setYoutubeInfo(null);
                                }}
                              >
                                Download Another Video
                              </Button>
                              <Button size="sm" onClick={() => router.push("/generated-shorts")}>
                                <Sparkles className="w-3 h-3 mr-1" /> View Generated Shorts
                              </Button>
                            </div>
                          </div>
                        )}

                        {/* Failed Action */}
                        {ytTask.status === "failed" && (
                          <div className="pt-2 flex justify-end gap-2 border-t border-border mt-2">
                            <Button
                              variant="outline"
                              size="sm"
                              onClick={() => {
                                setYtTask(null);
                              }}
                            >
                              Try Again
                            </Button>
                          </div>
                        )}

                        {/* Downloading In-Flight Cancel Action */}
                        {ytTask.status !== "completed" && ytTask.status !== "failed" && (
                          <div className="pt-2 flex justify-end">
                            <Button variant="outline" size="sm" onClick={handleCancelYtTask}>
                              Cancel Download
                            </Button>
                          </div>
                        )}
                      </div>
                    ) : (
                      /* YouTube Link Input Form */
                      <form onSubmit={handleImportYouTube} className="space-y-4">
                        <div>
                          <label className="block text-xs font-medium text-text-secondary mb-1.5 flex items-center gap-1.5">
                            <Youtube className="w-3.5 h-3.5 text-red-500" />
                            Paste YouTube Video Link
                          </label>
                          <div className="flex gap-2">
                            <input
                              type="url"
                              placeholder="https://www.youtube.com/watch?v=... or https://youtu.be/... or Shorts link"
                              value={youtubeUrl}
                              onChange={(e) => {
                                setYoutubeUrl(e.target.value);
                                if (youtubeInfo) setYoutubeInfo(null);
                              }}
                              className="flex-1 px-3 py-2 text-xs rounded-lg bg-surface-2 border border-border text-text-primary focus:outline-none focus:border-red-500 font-mono"
                              required
                            />
                            <Button
                              type="button"
                              variant="outline"
                              size="sm"
                              disabled={!youtubeUrl.trim() || fetchingYtInfo}
                              onClick={() => handleFetchYouTubeInfo()}
                            >
                              {fetchingYtInfo ? (
                                <RefreshCw className="w-3 h-3 animate-spin" />
                              ) : (
                                "Inspect Preview"
                              )}
                            </Button>
                          </div>
                          <p className="text-[11px] text-text-muted mt-1">
                            Supports full YouTube URLs, shortened youtu.be links, YouTube Shorts, and live VODs.
                          </p>
                        </div>

                        {/* Video Info Preview Card */}
                        {youtubeInfo && (
                          <div className="p-3 rounded-lg border border-border bg-surface-2 flex gap-3 items-center">
                            {youtubeInfo.thumbnail && (
                              <img
                                src={youtubeInfo.thumbnail}
                                alt={youtubeInfo.title}
                                className="w-24 h-14 object-cover rounded border border-border flex-shrink-0"
                              />
                            )}
                            <div className="flex-1 min-w-0">
                              <h4 className="text-xs font-semibold text-text-primary truncate">
                                {youtubeInfo.title}
                              </h4>
                              <p className="text-[11px] text-text-muted truncate mt-0.5">
                                Channel: {youtubeInfo.uploader} • {youtubeInfo.duration_formatted} • {youtubeInfo.resolution}
                              </p>
                              <div className="flex gap-1.5 mt-1.5">
                                <Badge variant="default">{youtubeInfo.duration_formatted}</Badge>
                                <Badge variant="success">HD MP4</Badge>
                                {youtubeInfo.fps && <Badge variant="default">{youtubeInfo.fps} FPS</Badge>}
                              </div>
                            </div>
                          </div>
                        )}

                        {/* Automatic Shorts Pipeline Checkbox */}
                        <div className="p-3 rounded-lg border border-primary/30 bg-primary/5 space-y-2">
                          <label className="flex items-start gap-2.5 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={autoGenerateShorts}
                              onChange={(e) => setAutoGenerateShorts(e.target.checked)}
                              className="mt-0.5 rounded border-border text-primary focus:ring-primary"
                            />
                            <div>
                              <span className="text-xs font-semibold text-text-primary flex items-center gap-1.5">
                                <Sparkles className="w-3.5 h-3.5 text-primary-light" />
                                Automatically Generate YouTube Shorts (9:16 Vertical)
                              </span>
                              <p className="text-[11px] text-text-muted mt-0.5">
                                As soon as the video finishes downloading, AI detects exciting moments, ranks the top candidates, cuts 9:16 vertical Shorts, adds subtitles, and creates AI titles & descriptions.
                              </p>
                            </div>
                          </label>
                        </div>

                        {/* Copyright & Permission Quick Setting */}
                        <div className="p-3 rounded-lg border border-border bg-surface-2 space-y-2">
                          <label className="flex items-start gap-2.5 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={hasPermission}
                              onChange={(e) => setHasPermission(e.target.checked)}
                              className="mt-0.5 rounded border-border text-primary focus:ring-primary"
                            />
                            <div>
                              <span className="text-xs font-medium text-text-primary">
                                I own this gameplay or have creator permission to edit & redistribute
                              </span>
                              <p className="text-[11px] text-text-muted mt-0.5">
                                Pre-populates the Phase 9 Copyright & Monetization Risk Center with creator attribution.
                              </p>
                            </div>
                          </label>
                        </div>

                        <div className="pt-2 flex justify-end gap-2">
                          <Button
                            type="button"
                            variant="outline"
                            onClick={() => setImportModalOpen(false)}
                          >
                            Cancel
                          </Button>
                          <Button
                            type="submit"
                            className="bg-red-600 hover:bg-red-700 text-white font-semibold"
                            disabled={!youtubeUrl.trim() || ytDownloading}
                          >
                            <Download className="w-3.5 h-3.5 mr-1.5" />
                            {autoGenerateShorts ? "Download & Make Shorts" : "Download Video"}
                          </Button>
                        </div>
                      </form>
                    )}
                  </div>
                ) : importTab === "upload" ? (
                  <form onSubmit={handleUploadSubmit} className="space-y-4">
                    <div>
                      <label className="block text-xs font-medium text-text-secondary mb-1.5">
                        Select Video File
                      </label>
                      <input
                        ref={fileInputRef}
                        type="file"
                        accept=".mp4,.mkv,.mov,.webm"
                        onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                        className="w-full text-xs text-text-primary file:mr-3 file:py-2 file:px-3 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-surface-3 file:text-text-primary hover:file:bg-primary/20 cursor-pointer border border-border rounded-lg p-2 bg-surface-2"
                      />
                      <p className="text-[11px] text-text-muted mt-1">
                        Supported containers: MP4, MKV, MOV, WebM. Streamed directly to D: storage.
                      </p>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-text-secondary mb-1.5">
                        Optional Notes / Tags
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. Heist mission playthrough, Vice City Beach stunt run..."
                        value={uploadNotes}
                        onChange={(e) => setUploadNotes(e.target.value)}
                        className="w-full px-3 py-2 text-xs rounded-lg bg-surface-2 border border-border text-text-primary focus:outline-none focus:border-primary"
                      />
                    </div>

                    <div className="pt-2 flex justify-end gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => setImportModalOpen(false)}
                        disabled={uploading}
                      >
                        Cancel
                      </Button>
                      <Button type="submit" disabled={!uploadFile || uploading}>
                        {uploading ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Uploading & Validating...
                          </>
                        ) : (
                          "Import Video"
                        )}
                      </Button>
                    </div>
                  </form>
                ) : (
                  <form onSubmit={handleImportLocal} className="space-y-4">
                    <div>
                      <label className="block text-xs font-medium text-text-secondary mb-1.5">
                        Local File Path on D: Drive
                      </label>
                      <input
                        type="text"
                        placeholder="D:\GTA_CLIPFORGE_AI\GTA6_RECORDINGS\gameplay_01.mp4"
                        value={localFilePath}
                        onChange={(e) => setLocalFilePath(e.target.value)}
                        className="w-full px-3 py-2 text-xs font-mono rounded-lg bg-surface-2 border border-border text-text-primary focus:outline-none focus:border-primary"
                      />
                      <p className="text-[11px] text-text-muted mt-1 flex items-center gap-1">
                        <Info className="w-3 h-3 text-primary-light" />
                        Ideal for multi-gigabyte 1–8 hour long GTA 6 gameplay recordings without browser upload limits.
                      </p>
                    </div>

                    <div>
                      <label className="block text-xs font-medium text-text-secondary mb-1.5">
                        Optional Notes / Tags
                      </label>
                      <input
                        type="text"
                        placeholder="e.g. 4-hour Free Roam & 5-Star Wanted Level Escape"
                        value={localNotes}
                        onChange={(e) => setLocalNotes(e.target.value)}
                        className="w-full px-3 py-2 text-xs rounded-lg bg-surface-2 border border-border text-text-primary focus:outline-none focus:border-primary"
                      />
                    </div>

                    <div className="pt-2 flex justify-end gap-2">
                      <Button
                        type="button"
                        variant="outline"
                        onClick={() => setImportModalOpen(false)}
                        disabled={uploading}
                      >
                        Cancel
                      </Button>
                      <Button type="submit" disabled={!localFilePath.trim() || uploading}>
                        {uploading ? (
                          <>
                            <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> Validating with FFprobe...
                          </>
                        ) : (
                          "Import Local Recording"
                        )}
                      </Button>
                    </div>
                  </form>
                )}
              </div>
            </div>
          </div>
        )}

        {/* RECORDING DETAILS MODAL */}
        {selectedRecording && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-surface border border-border rounded-xl w-full max-w-2xl overflow-hidden shadow-2xl">
              <div className="p-4 border-b border-border flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Film className="w-5 h-5 text-primary-light" />
                  <h3 className="text-sm font-semibold text-text-primary truncate max-w-md">
                    {selectedRecording.original_filename}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedRecording(null)}
                  className="p-1 rounded hover:bg-surface-2 text-text-muted hover:text-text-primary"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="p-5 space-y-4 max-h-[80vh] overflow-y-auto">
                {/* Video Player Preview */}
                <div className="rounded-lg overflow-hidden bg-black aspect-video flex items-center justify-center border border-border">
                  <video
                    controls
                    className="w-full h-full"
                    src={`${api.baseUrl}/api/recordings/${selectedRecording.id}/stream`}
                  >
                    Your browser does not support the video tag.
                  </video>
                </div>

                {/* Metadata Grid */}
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                  <div className="p-3 rounded-lg bg-surface-2 border border-border/40">
                    <span className="text-[11px] text-text-muted block">Duration</span>
                    <span className="text-sm font-semibold text-text-primary font-mono mt-0.5 block">
                      {selectedRecording.duration_seconds
                        ? formatDuration(selectedRecording.duration_seconds)
                        : "—"}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-surface-2 border border-border/40">
                    <span className="text-[11px] text-text-muted block">Resolution</span>
                    <span className="text-sm font-semibold text-text-primary font-mono mt-0.5 block">
                      {selectedRecording.resolution || "—"}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-surface-2 border border-border/40">
                    <span className="text-[11px] text-text-muted block">Frame Rate</span>
                    <span className="text-sm font-semibold text-text-primary font-mono mt-0.5 block">
                      {selectedRecording.fps ? `${selectedRecording.fps} FPS` : "—"}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-surface-2 border border-border/40">
                    <span className="text-[11px] text-text-muted block">File Size</span>
                    <span className="text-sm font-semibold text-text-primary font-mono mt-0.5 block">
                      {selectedRecording.file_size_bytes
                        ? formatBytes(selectedRecording.file_size_bytes)
                        : "—"}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-surface-2 border border-border/40">
                    <span className="text-[11px] text-text-muted block">Video Codec</span>
                    <span className="text-sm font-semibold text-text-primary font-mono uppercase mt-0.5 block">
                      {selectedRecording.video_codec || "—"}
                    </span>
                  </div>

                  <div className="p-3 rounded-lg bg-surface-2 border border-border/40">
                    <span className="text-[11px] text-text-muted block">Status</span>
                    <div className="mt-1">
                      <Badge variant={statusBadgeVariant[selectedRecording.status] || "default"}>
                        {selectedRecording.status}
                      </Badge>
                    </div>
                  </div>
                </div>

                {/* Storage & Hash Info */}
                <div className="p-3 rounded-lg bg-surface-2 border border-border/40 space-y-2 text-xs">
                  <div>
                    <span className="text-text-muted block text-[11px]">Storage Path (D: Drive)</span>
                    <code className="text-electric text-[11px] break-all font-mono">
                      {selectedRecording.file_path}
                    </code>
                  </div>
                  {selectedRecording.file_hash && (
                    <div>
                      <span className="text-text-muted block text-[11px]">SHA-256 Checksum</span>
                      <code className="text-text-secondary text-[11px] break-all font-mono">
                        {selectedRecording.file_hash}
                      </code>
                    </div>
                  )}
                  {selectedRecording.notes && (
                    <div>
                      <span className="text-text-muted block text-[11px]">Notes</span>
                      <p className="text-text-secondary text-xs">{selectedRecording.notes}</p>
                    </div>
                  )}
                </div>

                {/* Modal Footer Actions */}
                <div className="pt-2 flex justify-between items-center">
                  <Button
                    variant="outline"
                    size="sm"
                    className="text-error border-error/30 hover:bg-error/10"
                    onClick={() => {
                      setDeleteConfirmRec(selectedRecording);
                      setSelectedRecording(null);
                    }}
                  >
                    <Trash2 className="w-3.5 h-3.5 mr-1.5" /> Delete
                  </Button>

                  <div className="flex gap-2">
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => router.push(`/recordings/${selectedRecording.id}`)}
                    >
                      <Sparkles className="w-3.5 h-3.5 mr-1.5" /> Open Full Analysis
                    </Button>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleReprocess(selectedRecording)}
                      disabled={actionLoading}
                    >
                      <RotateCcw className="w-3.5 h-3.5 mr-1.5" /> Reprocess
                    </Button>
                    <Button size="sm" onClick={() => setSelectedRecording(null)}>
                      Close
                    </Button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* DELETE CONFIRMATION DIALOG */}
        {deleteConfirmRec && (
          <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
            <div className="bg-surface border border-border rounded-xl w-full max-w-md p-5 shadow-2xl">
              <div className="flex items-center gap-3 mb-3 text-error">
                <AlertTriangle className="w-6 h-6 flex-shrink-0" />
                <h3 className="text-base font-semibold text-text-primary">Delete Recording?</h3>
              </div>
              <p className="text-xs text-text-secondary mb-3">
                Are you sure you want to remove{" "}
                <span className="font-semibold text-text-primary">
                  {deleteConfirmRec.original_filename}
                </span>{" "}
                from GTA CLIPFORGE AI?
              </p>

              <label className="flex items-center gap-2 p-2.5 rounded-lg bg-surface-2 border border-border/60 text-xs text-text-secondary cursor-pointer mb-4">
                <input
                  type="checkbox"
                  checked={deleteDiskFile}
                  onChange={(e) => setDeleteDiskFile(e.target.checked)}
                  className="rounded border-border"
                />
                <span>Also permanently delete physical video file from D: drive</span>
              </label>

              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setDeleteConfirmRec(null)}
                  disabled={actionLoading}
                >
                  Cancel
                </Button>
                <Button
                  variant="default"
                  size="sm"
                  className="bg-error hover:bg-error/90 text-white"
                  onClick={handleDeleteConfirm}
                  disabled={actionLoading}
                >
                  {actionLoading ? "Deleting..." : "Confirm Delete"}
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
