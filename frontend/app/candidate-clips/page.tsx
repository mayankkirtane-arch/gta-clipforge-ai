"use client";

import React, { useEffect, useState, useCallback, useRef, useMemo } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Sparkles,
  Play,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  RotateCcw,
  Sliders,
  Filter,
  Film,
  Flame,
  Volume2,
  Clock,
  ChevronRight,
  Check,
  X,
  Scissors,
  Layers,
  Info,
  RefreshCw,
  Search,
  CheckSquare,
  Square,
  Award,
  Video,
  Download,
  ListOrdered,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import {
  api,
  Recording,
  CandidateClip,
  ClipCategoryInfo,
  CandidateClipSummary,
} from "@/lib/api";
import { formatDuration } from "@/lib/utils";

// 8 Category Themes
const CATEGORY_THEMES: Record<string, { bg: string; text: string; border: string; glow: string }> = {
  badass_moments: { bg: "bg-red-500/15", text: "text-red-400", border: "border-red-500/30", glow: "#ef4444" },
  police_chase: { bg: "bg-blue-500/15", text: "text-blue-400", border: "border-blue-500/30", glow: "#3b82f6" },
  car_stunts: { bg: "bg-purple-500/15", text: "text-purple-400", border: "border-purple-500/30", glow: "#a855f7" },
  explosions: { bg: "bg-orange-500/15", text: "text-orange-400", border: "border-orange-500/30", glow: "#f97316" },
  funny_npc: { bg: "bg-yellow-500/15", text: "text-yellow-400", border: "border-yellow-500/30", glow: "#eab308" },
  shootouts: { bg: "bg-rose-500/15", text: "text-rose-400", border: "border-rose-500/30", glow: "#e11d48" },
  cinematic_scenes: { bg: "bg-cyan-500/15", text: "text-cyan-400", border: "border-cyan-500/30", glow: "#06b6d4" },
  unexpected_events: { bg: "bg-violet-500/15", text: "text-violet-400", border: "border-violet-500/30", glow: "#8b5cf6" },
};

function formatTimestamp(seconds: number): string {
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m.toString().padStart(2, "0")}:${s.toString().padStart(2, "0")}`;
}

function getScoreTier(score: number): { label: string; color: string; badgeVariant: "purple" | "success" | "info" | "default" } {
  if (score >= 90) return { label: "Legendary Short", color: "text-amber-400 border-amber-500/40 bg-amber-500/15", badgeVariant: "purple" };
  if (score >= 80) return { label: "Epic Short", color: "text-purple-400 border-purple-500/40 bg-purple-500/15", badgeVariant: "purple" };
  if (score >= 65) return { label: "Great Pick", color: "text-blue-400 border-blue-500/40 bg-blue-500/15", badgeVariant: "info" };
  return { label: "Good Candidate", color: "text-text-muted border-border bg-surface-2", badgeVariant: "default" };
}

export default function CandidateClipsPage() {
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [selectedRecId, setSelectedRecId] = useState<number | null>(null);
  const [categories, setCategories] = useState<ClipCategoryInfo[]>([]);
  const [targetLengths, setTargetLengths] = useState<number[]>([15, 20, 30, 45, 60]);
  const [candidates, setCandidates] = useState<CandidateClip[]>([]);
  const [summary, setSummary] = useState<CandidateClipSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [ranking, setRanking] = useState(false);
  const [rankProgress, setRankProgress] = useState<string | null>(null);

  // Filters & Sorting
  const [selectedCategory, setSelectedCategory] = useState<string>("all");
  const [selectedDuration, setSelectedDuration] = useState<number>(0);
  const [selectionFilter, setSelectionFilter] = useState<"all" | "selected" | "unselected">("all");
  const [sortBy, setSortBy] = useState<string>("score");
  const [sortOrder, setSortOrder] = useState<string>("desc");
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedBreakdownId, setExpandedBreakdownId] = useState<number | null>(null);

  // Video Preview Modal State
  const [previewClip, setPreviewClip] = useState<CandidateClip | null>(null);
  const [currentTime, setCurrentTime] = useState(0);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  // Load recordings and category definitions
  useEffect(() => {
    async function init() {
      try {
        const [recsRes, catsRes, lengthsRes] = await Promise.all([
          api.getRecordings(1, 50),
          api.getClipCategories().catch(() => []),
          api.getTargetLengths().catch(() => [15, 20, 30, 45, 60]),
        ]);
        setRecordings(recsRes.items);
        if (recsRes.items.length > 0) {
          setSelectedRecId(recsRes.items[0].id);
        }
        if (catsRes.length > 0) setCategories(catsRes);
        if (lengthsRes.length > 0) setTargetLengths(lengthsRes);
      } catch (e) {
        console.error("Init candidate clips error", e);
      } finally {
        setLoading(false);
      }
    }
    init();
  }, []);

  // Fetch candidate clips for selected recording
  const loadCandidates = useCallback(async () => {
    if (!selectedRecId) {
      setCandidates([]);
      setSummary(null);
      return;
    }
    setLoading(true);
    try {
      const res = await api.getCandidateClips({
        recording_id: selectedRecId,
        category: selectedCategory !== "all" ? selectedCategory : undefined,
        target_length: selectedDuration > 0 ? selectedDuration : undefined,
        is_selected: selectionFilter === "selected" ? true : selectionFilter === "unselected" ? false : undefined,
        sort_by: sortBy,
        sort_order: sortOrder,
        page_size: 150,
      });
      setCandidates(res.items);
      setSummary(res.summary || null);
    } catch (e) {
      console.error("Error loading candidate clips", e);
    } finally {
      setLoading(false);
    }
  }, [selectedRecId, selectedCategory, selectedDuration, selectionFilter, sortBy, sortOrder]);

  useEffect(() => {
    loadCandidates();
  }, [loadCandidates]);

  const activeRecording = useMemo(() => {
    return recordings.find((r) => r.id === selectedRecId) || null;
  }, [recordings, selectedRecId]);

  // Trigger Clip Ranking Pipeline
  const handleRunRanking = async () => {
    if (!selectedRecId) return;
    setRanking(true);
    setRankProgress("Starting AI Clip Ranking & Boundary Optimization (15s, 20s, 30s, 45s, 60s)...");

    try {
      const res = await api.triggerClipRanking(selectedRecId, {
        target_lengths: [15, 20, 30, 45, 60],
      });

      // Poll job progress
      const pollInterval = setInterval(async () => {
        try {
          const jobs = await api.getJobs("all", 10);
          const currentJob = jobs.find((j) => j.id === res.job_id);
          if (currentJob) {
            setRankProgress(currentJob.message || `Ranking clips... ${currentJob.progress}%`);
            if (currentJob.status === "completed" || currentJob.status === "failed") {
              clearInterval(pollInterval);
              setRanking(false);
              setRankProgress(null);
              loadCandidates();
            }
          }
        } catch {
          clearInterval(pollInterval);
          setRanking(false);
          setRankProgress(null);
          loadCandidates();
        }
      }, 1500);
    } catch (e: any) {
      alert(`Ranking failed: ${e.message}`);
      setRanking(false);
      setRankProgress(null);
    }
  };

  // Quick Selection Controls (Top 5, 10, 15, 20, Deselect All)
  const handleQuickSelect = async (n: number) => {
    if (!selectedRecId) return;
    try {
      await api.batchSelectClips(selectedRecId, { select_top_n: n });
      loadCandidates();
    } catch (e: any) {
      alert(`Selection failed: ${e.message}`);
    }
  };

  const handleDeselectAll = async () => {
    if (!selectedRecId) return;
    try {
      await api.batchSelectClips(selectedRecId, { deselect_all: true });
      loadCandidates();
    } catch (e: any) {
      alert(`Deselection failed: ${e.message}`);
    }
  };

  // Toggle single clip selection
  const handleToggleSelect = async (clip: CandidateClip, e?: React.MouseEvent) => {
    if (e) e.stopPropagation();
    const newSelected = !clip.is_selected;
    try {
      await api.updateCandidateClip(clip.id, { is_selected: newSelected });
      setCandidates((prev) =>
        prev.map((c) => (c.id === clip.id ? { ...c, is_selected: newSelected } : c))
      );
      if (summary) {
        setSummary({
          ...summary,
          selected_count: summary.selected_count + (newSelected ? 1 : -1),
        });
      }
    } catch (err: any) {
      alert(`Failed to update selection: ${err.message}`);
    }
  };

  // Batch approve selected
  const handleBatchApprove = async () => {
    if (!selectedRecId) return;
    try {
      const res = await api.batchApproveCandidateClips(selectedRecId);
      alert(`Successfully approved ${res.approved_count} candidate clips!`);
      loadCandidates();
    } catch (e: any) {
      alert(`Batch approval failed: ${e.message}`);
    }
  };

  // Export selected to Shorts Pipeline
  const handleExportSelected = async () => {
    if (!selectedRecId) return;
    try {
      const res = await api.exportSelectedClips(selectedRecId);
      loadCandidates();
      if (confirm(`Successfully queued ${res.exported_count} candidate clips for 9:16 YouTube Shorts generation!\n\nWould you like to open the Generated Shorts page now?`)) {
        window.location.href = "/generated-shorts";
      }
    } catch (e: any) {
      alert(`Export failed: ${e.message}`);
    }
  };

  // Video Preview Modal
  const openPreview = (c: CandidateClip) => {
    setPreviewClip(c);
    setCurrentTime(c.start_time);
  };

  const closePreview = () => {
    setPreviewClip(null);
    if (videoRef.current) {
      videoRef.current.pause();
    }
  };

  // Search filtering
  const filteredCandidates = useMemo(() => {
    return candidates.filter((c) => {
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchTitle = c.title.toLowerCase().includes(q);
        const matchCat = c.category_label.toLowerCase().includes(q);
        const matchReason = c.score_reason.toLowerCase().includes(q);
        if (!matchTitle && !matchCat && !matchReason) return false;
      }
      return true;
    });
  }, [candidates, searchQuery]);

  const selectedCount = useMemo(() => {
    return candidates.filter((c) => c.is_selected).length;
  }, [candidates]);

  return (
    <div className="min-h-screen pb-24">
      <Header
        title="Candidate Clips"
        subtitle="Phase 5 — AI Clip Ranking and Intelligent Selection for YouTube Shorts (1–100 Heuristic Score)"
      />

      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        {/* Prominent Disclaimer Alert */}
        <div className="p-3.5 rounded-xl bg-surface-2 border border-border/80 flex items-center justify-between text-xs text-text-muted">
          <div className="flex items-center gap-2.5">
            <Info className="w-4 h-4 text-primary-light flex-shrink-0" />
            <span>
              <strong className="text-white">Heuristic Scoring Notice:</strong> AI scores are algorithmic estimates
              evaluating visual motion, audio peaks, cinematic framing, and boundary quality — not guaranteed viral predictions.
            </span>
          </div>
          <Badge variant="purple" className="text-[10px] hidden sm:inline-flex">
            Heuristic Model v1.0
          </Badge>
        </div>

        {/* Top Control Bar: Recording Selector & Main Ranking Trigger */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 bg-surface p-4 rounded-xl border border-border">
          <div className="flex items-center gap-3 w-full md:w-auto">
            <Film className="w-5 h-5 text-primary-light flex-shrink-0" />
            <div className="flex flex-col">
              <span className="text-xs text-text-muted">Gameplay Recording</span>
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
            <Button
              onClick={handleRunRanking}
              disabled={ranking || !selectedRecId}
              className="bg-gradient-to-r from-primary to-electric text-white shadow-lg shadow-primary/25 hover:brightness-110"
            >
              {ranking ? (
                <>
                  <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  Ranking Candidates...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2 fill-current" />
                  Run AI Clip Ranking (1–100)
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Progress Alert Banner when running */}
        {rankProgress && (
          <div className="p-4 rounded-xl bg-primary/10 border border-primary/30 flex items-center justify-between animate-pulse">
            <div className="flex items-center gap-3">
              <RefreshCw className="w-5 h-5 text-primary-light animate-spin" />
              <div>
                <h4 className="text-sm font-semibold text-white">Boundary Optimization & Ranking in Progress</h4>
                <p className="text-xs text-text-muted">{rankProgress}</p>
              </div>
            </div>
            <Badge variant="warning">Analyzing</Badge>
          </div>
        )}

        {/* Summary KPI Metrics */}
        {summary && (
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Card className="bg-surface-2/60 border-border">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-primary/20 text-primary-light">
                  <ListOrdered className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-text-muted block">Total Candidates</span>
                  <span className="text-xl font-bold text-white">{summary.total_candidates}</span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-surface-2/60 border-border">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-electric/20 text-electric">
                  <Award className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-text-muted block">Highest AI Score</span>
                  <span className="text-xl font-bold text-amber-400">{summary.top_score}/100</span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-surface-2/60 border-border">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-emerald-500/20 text-emerald-400">
                  <CheckSquare className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-text-muted block">Selected for Shorts</span>
                  <span className="text-xl font-bold text-emerald-400">{selectedCount}</span>
                </div>
              </CardContent>
            </Card>

            <Card className="bg-surface-2/60 border-border">
              <CardContent className="p-4 flex items-center gap-3">
                <div className="p-2.5 rounded-lg bg-blue-500/20 text-blue-400">
                  <CheckCircle2 className="w-5 h-5" />
                </div>
                <div>
                  <span className="text-xs text-text-muted block">Approved Clips</span>
                  <span className="text-xl font-bold text-white">{summary.approved_count}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Smart Selection & Filter Bar */}
        <div className="bg-surface p-4 rounded-xl border border-border space-y-3">
          {/* Quick Selection Buttons Row */}
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-border/60 pb-3">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-xs font-semibold text-text-secondary flex items-center gap-1.5 mr-1">
                <CheckSquare className="w-3.5 h-3.5 text-primary-light" />
                Quick Select:
              </span>
              {[5, 10, 15, 20].map((n) => (
                <button
                  key={n}
                  onClick={() => handleQuickSelect(n)}
                  className="px-2.5 py-1 rounded-md text-xs font-medium bg-surface-2 hover:bg-primary/20 text-text-secondary hover:text-white border border-border transition-all"
                >
                  Top {n}
                </button>
              ))}
              <button
                onClick={handleDeselectAll}
                className="px-2.5 py-1 rounded-md text-xs font-medium bg-surface-2 hover:bg-red-500/10 text-text-muted hover:text-red-400 border border-border transition-all"
              >
                Deselect All
              </button>
            </div>

            <div className="text-xs text-text-muted font-medium">
              <span className="text-white font-bold">{selectedCount}</span> of {candidates.length} candidate clips selected
            </div>
          </div>

          {/* Filter Controls Row */}
          <div className="flex flex-col md:flex-row items-stretch md:items-center justify-between gap-3 pt-1">
            <div className="flex flex-wrap items-center gap-2">
              {/* Category Filter */}
              <select
                value={selectedCategory}
                onChange={(e) => setSelectedCategory(e.target.value)}
                className="bg-surface-2 border border-border text-white text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-primary"
              >
                <option value="all">All 8 Shorts Categories</option>
                {categories.map((cat) => (
                  <option key={cat.id} value={cat.id}>
                    {cat.label}
                  </option>
                ))}
              </select>

              {/* Target Duration Filter */}
              <select
                value={selectedDuration}
                onChange={(e) => setSelectedDuration(Number(e.target.value))}
                className="bg-surface-2 border border-border text-white text-xs rounded-lg px-2.5 py-1.5 focus:outline-none focus:border-primary"
              >
                <option value={0}>All Target Durations</option>
                {targetLengths.map((dur) => (
                  <option key={dur} value={dur}>
                    {dur}s Duration
                  </option>
                ))}
              </select>

              {/* Selection Status Filter */}
              <div className="flex rounded-lg bg-surface-2 p-0.5 border border-border">
                {[
                  { id: "all", label: "All" },
                  { id: "selected", label: "Selected" },
                  { id: "unselected", label: "Unselected" },
                ].map((item) => (
                  <button
                    key={item.id}
                    onClick={() => setSelectionFilter(item.id as any)}
                    className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                      selectionFilter === item.id
                        ? "bg-primary text-white shadow-sm"
                        : "text-text-muted hover:text-white"
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Sorting & Search */}
            <div className="flex items-center gap-2">
              <div className="flex items-center gap-1.5 text-xs text-text-muted">
                <span>Sort:</span>
                <select
                  value={sortBy}
                  onChange={(e) => setSortBy(e.target.value)}
                  className="bg-surface-2 border border-border text-white text-xs rounded-lg px-2 py-1.5 focus:outline-none focus:border-primary"
                >
                  <option value="score">AI Score (1–100)</option>
                  <option value="duration">Target Duration</option>
                  <option value="timestamp">Timeline Order</option>
                  <option value="category">Category</option>
                </select>
              </div>

              <div className="relative min-w-[170px]">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-text-muted" />
                <input
                  type="text"
                  placeholder="Filter clips..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="w-full bg-surface-2 border border-border rounded-lg pl-8 pr-3 py-1.5 text-xs text-white placeholder-text-muted focus:outline-none focus:border-primary"
                />
              </div>
            </div>
          </div>
        </div>

        {/* Candidate Clips Grid */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-20 text-text-muted">
            <RefreshCw className="w-8 h-8 animate-spin mb-3 text-primary-light" />
            <p className="text-sm">Loading and evaluating candidate clips...</p>
          </div>
        ) : filteredCandidates.length === 0 ? (
          <div className="rounded-xl border border-border bg-surface flex flex-col items-center justify-center py-20 text-center p-6">
            <Award className="w-16 h-16 text-text-muted opacity-20 mb-4" />
            <h3 className="text-lg font-semibold text-text-secondary">No Candidate Clips Found</h3>
            <p className="text-sm text-text-muted mt-2 max-w-md">
              {candidates.length === 0
                ? "No ranked candidate clips generated yet for this recording. Click 'Run AI Clip Ranking (1–100)' to score and optimize boundaries for YouTube Shorts."
                : "No clips match your current filter settings. Try resetting filters."}
            </p>
            {candidates.length === 0 && (
              <Button onClick={handleRunRanking} disabled={ranking} className="mt-5 bg-primary hover:bg-primary-dark text-white">
                <Sparkles className="w-4 h-4 mr-2" />
                Generate Candidate Clips Now
              </Button>
            )}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {filteredCandidates.map((clip) => {
              const theme = CATEGORY_THEMES[clip.category] || {
                bg: "bg-surface-2",
                text: "text-primary-light",
                border: "border-border",
                glow: "#a855f7",
              };
              const tier = getScoreTier(clip.ai_score);
              const isExpanded = expandedBreakdownId === clip.id;

              return (
                <div
                  key={clip.id}
                  onClick={() => handleToggleSelect(clip)}
                  className={`rounded-xl border transition-all duration-200 cursor-pointer overflow-hidden flex flex-col justify-between group ${
                    clip.is_selected
                      ? "bg-surface border-primary shadow-lg shadow-primary/10 ring-1 ring-primary/40"
                      : "bg-surface border-border hover:border-border/80"
                  }`}
                >
                  <div>
                    {/* Thumbnail Section */}
                    <div className="relative aspect-video w-full bg-black/40 overflow-hidden">
                      {clip.thumbnail_url ? (
                        <img
                          src={clip.thumbnail_url}
                          alt={clip.title}
                          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                        />
                      ) : (
                        <div className="w-full h-full flex items-center justify-center bg-surface-2 text-text-muted">
                          <Film className="w-8 h-8 opacity-40" />
                        </div>
                      )}

                      {/* Select Checkbox Top Left */}
                      <div className="absolute top-2.5 left-2.5 z-10">
                        <button
                          onClick={(e) => handleToggleSelect(clip, e)}
                          className={`w-6 h-6 rounded flex items-center justify-center backdrop-blur-md transition-all ${
                            clip.is_selected
                              ? "bg-primary text-white shadow-md shadow-primary/30"
                              : "bg-black/60 text-white/60 hover:text-white border border-white/20"
                          }`}
                        >
                          {clip.is_selected ? (
                            <Check className="w-4 h-4 stroke-[3]" />
                          ) : (
                            <div className="w-2.5 h-2.5 rounded-sm" />
                          )}
                        </button>
                      </div>

                      {/* Rank Position Badge Top Left (after checkbox) */}
                      {clip.selection_rank && (
                        <div className="absolute top-2.5 left-10 z-10">
                          <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-black/70 text-text-secondary border border-white/10 backdrop-blur-md">
                            #{clip.selection_rank}
                          </span>
                        </div>
                      )}

                      {/* AI Score Badge Top Right (Glowing 1-100 score) */}
                      <div className="absolute top-2.5 right-2.5 z-10">
                        <div className={`px-2.5 py-1 rounded-lg border backdrop-blur-md flex items-center gap-1.5 shadow-md ${tier.color}`}>
                          <Sparkles className="w-3.5 h-3.5 fill-current" />
                          <span className="text-xs font-black font-mono tracking-tight">{clip.ai_score}/100</span>
                        </div>
                      </div>

                      {/* Target Duration Pill Bottom Right */}
                      <div className="absolute bottom-2.5 right-2.5">
                        <span className="text-[11px] font-bold font-mono px-2 py-0.5 rounded bg-black/80 text-white border border-white/10 backdrop-blur-md">
                          {clip.target_length}s Short
                        </span>
                      </div>

                      {/* Timestamp interval Bottom Left */}
                      <div className="absolute bottom-2.5 left-2.5">
                        <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-black/80 text-text-secondary backdrop-blur-md flex items-center gap-1">
                          <Clock className="w-3 h-3 text-primary-light" />
                          {formatTimestamp(clip.start_time)} - {formatTimestamp(clip.end_time)} ({clip.duration}s)
                        </span>
                      </div>

                      {/* Play Preview Overlay */}
                      <div
                        onClick={(e) => {
                          e.stopPropagation();
                          openPreview(clip);
                        }}
                        className="absolute inset-0 bg-black/35 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center z-0"
                      >
                        <div className="w-10 h-10 rounded-full bg-primary text-white flex items-center justify-center shadow-lg hover:scale-110 transition-transform">
                          <Play className="w-4 h-4 ml-0.5 fill-current" />
                        </div>
                      </div>
                    </div>

                    {/* Card Body */}
                    <div className="p-4 space-y-3">
                      {/* Category & Tier Label */}
                      <div className="flex items-center justify-between gap-2">
                        <span className={`text-[11px] font-bold px-2 py-0.5 rounded-md border ${theme.bg} ${theme.text} ${theme.border}`}>
                          {clip.category_label}
                        </span>
                        <span className="text-[10px] text-text-muted font-medium">{tier.label}</span>
                      </div>

                      {/* Title & Setup Boundaries */}
                      <div>
                        <h4 className="text-sm font-bold text-white group-hover:text-primary-light transition-colors line-clamp-1">
                          {clip.title}
                        </h4>
                        <div className="flex items-center gap-2 mt-1 text-[11px] text-text-muted font-mono">
                          <span>Setup: {clip.pre_roll_sec}s</span>
                          <span>•</span>
                          <span>Climax @ {formatTimestamp(clip.climax_time)}</span>
                          <span>•</span>
                          <span>Resolution: {clip.post_roll_sec}s</span>
                        </div>
                      </div>

                      {/* Reason for Score */}
                      <p className="text-xs text-text-secondary leading-relaxed line-clamp-2">
                        {clip.score_reason}
                      </p>

                      {/* Expandable 9-Factor Breakdown Toggle */}
                      {clip.score_breakdown && (
                        <div className="pt-1">
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              setExpandedBreakdownId(isExpanded ? null : clip.id);
                            }}
                            className="text-[11px] text-primary-light hover:underline flex items-center gap-1 font-medium"
                          >
                            {isExpanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                            {isExpanded ? "Hide Factor Breakdown" : "View 9-Factor Scoring Details"}
                          </button>

                          {isExpanded && (
                            <div className="mt-2.5 p-2.5 rounded-lg bg-surface-2 border border-border/80 grid grid-cols-2 gap-1.5 text-[10px] animate-fadeIn">
                              <div>
                                <span className="text-text-muted block">Visual Excitement</span>
                                <span className="font-bold text-white">{clip.score_breakdown.visual_excitement}/100</span>
                              </div>
                              <div>
                                <span className="text-text-muted block">Unexpectedness</span>
                                <span className="font-bold text-white">{clip.score_breakdown.unexpectedness}/100</span>
                              </div>
                              <div>
                                <span className="text-text-muted block">Action Intensity</span>
                                <span className="font-bold text-white">{clip.score_breakdown.action_intensity}/100</span>
                              </div>
                              <div>
                                <span className="text-text-muted block">Cinematic Quality</span>
                                <span className="font-bold text-white">{clip.score_breakdown.cinematic_quality}/100</span>
                              </div>
                              <div>
                                <span className="text-text-muted block">Entertainment Value</span>
                                <span className="font-bold text-white">{clip.score_breakdown.entertainment_value}/100</span>
                              </div>
                              <div>
                                <span className="text-text-muted block">Audio Excitement</span>
                                <span className="font-bold text-white">{clip.score_breakdown.audio_excitement}/100</span>
                              </div>
                              <div>
                                <span className="text-text-muted block">Arc Completeness</span>
                                <span className="font-bold text-emerald-400">{clip.score_breakdown.event_completeness}/100</span>
                              </div>
                              <div>
                                <span className="text-text-muted block">Boundary Quality</span>
                                <span className="font-bold text-emerald-400">{clip.score_breakdown.boundary_quality}/100</span>
                              </div>
                              {clip.score_breakdown.duplicate_penalty < 0 && (
                                <div className="col-span-2 text-warning">
                                  <span>Duplicate Similarity Penalty: {clip.score_breakdown.duplicate_penalty} pts</span>
                                </div>
                              )}
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Card Action Footer */}
                  <div className="p-3 border-t border-border/50 bg-surface-2/30 flex items-center justify-between gap-2">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        openPreview(clip);
                      }}
                      className="text-xs text-text-muted hover:text-white flex items-center gap-1 font-medium"
                    >
                      <Play className="w-3.5 h-3.5" />
                      Preview
                    </button>

                    <div className="flex items-center gap-1.5">
                      <Button
                        size="sm"
                        variant={clip.is_selected ? "primary" : "outline"}
                        onClick={(e) => handleToggleSelect(clip, e)}
                        className={`h-7 px-2.5 text-xs ${
                          clip.is_selected ? "bg-primary text-white" : "border-border text-text-secondary"
                        }`}
                      >
                        {clip.is_selected ? "Selected" : "Select"}
                      </Button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Floating Selection Drawer / Sticky Action Bar */}
      {selectedCount > 0 && (
        <div className="fixed bottom-4 left-1/2 -translate-x-1/2 z-40 bg-surface/95 border border-primary/40 backdrop-blur-md rounded-2xl shadow-2xl px-6 py-3.5 flex items-center gap-6 max-w-2xl w-[90%] justify-between">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-full bg-primary/20 text-primary-light flex items-center justify-center font-bold text-sm">
              {selectedCount}
            </div>
            <div>
              <span className="text-xs font-bold text-white block">Candidate Clips Selected</span>
              <span className="text-[11px] text-text-muted">Ready for approval and Shorts pipeline</span>
            </div>
          </div>

          <div className="flex items-center gap-2.5">
            <Button
              size="sm"
              variant="outline"
              onClick={handleBatchApprove}
              className="text-xs border-border text-emerald-400 hover:bg-emerald-500/10"
            >
              <Check className="w-3.5 h-3.5 mr-1" />
              Approve All
            </Button>
            <Button
              size="sm"
              onClick={handleExportSelected}
              className="text-xs bg-gradient-to-r from-primary to-electric text-white shadow-md hover:brightness-110"
            >
              <Video className="w-3.5 h-3.5 mr-1.5" />
              Export to Shorts
            </Button>
          </div>
        </div>
      )}

      {/* Video Preview Modal */}
      {previewClip && activeRecording && (
        <div className="fixed inset-0 z-50 bg-black/85 backdrop-blur-md flex items-center justify-center p-4">
          <div className="bg-surface border border-border rounded-2xl max-w-3xl w-full overflow-hidden shadow-2xl space-y-0">
            {/* Modal Header */}
            <div className="p-4 bg-surface-2 flex items-center justify-between border-b border-border">
              <div className="flex items-center gap-2">
                <span className={`text-xs font-bold px-2 py-0.5 rounded border ${
                  (CATEGORY_THEMES[previewClip.category] || {}).bg
                } ${(CATEGORY_THEMES[previewClip.category] || {}).text} ${
                  (CATEGORY_THEMES[previewClip.category] || {}).border
                }`}>
                  {previewClip.category_label}
                </span>
                <span className="text-xs text-text-muted font-mono">
                  {formatTimestamp(previewClip.start_time)} - {formatTimestamp(previewClip.end_time)} ({previewClip.duration}s)
                </span>
                <span className="text-xs font-bold text-amber-400 font-mono ml-2">
                  Score: {previewClip.ai_score}/100
                </span>
              </div>
              <button onClick={closePreview} className="text-text-muted hover:text-white">
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Video Player (Scrubbed to clip range) */}
            <div className="relative aspect-video bg-black flex items-center justify-center">
              <video
                ref={videoRef}
                src={`/api/recordings/${activeRecording.id}/proxy`}
                controls
                autoPlay
                onLoadedMetadata={() => {
                  if (videoRef.current) {
                    videoRef.current.currentTime = previewClip.start_time;
                  }
                }}
                onTimeUpdate={() => {
                  if (videoRef.current) {
                    setCurrentTime(videoRef.current.currentTime);
                    if (videoRef.current.currentTime >= previewClip.end_time + 0.3) {
                      videoRef.current.currentTime = previewClip.start_time;
                    }
                  }
                }}
                className="w-full h-full object-contain"
              />
            </div>

            {/* Modal Body & Details */}
            <div className="p-4 space-y-3 bg-surface">
              <p className="text-xs text-text-secondary leading-relaxed">{previewClip.score_reason}</p>

              <div className="flex items-center justify-between pt-2 border-t border-border">
                <div className="text-xs text-text-muted">
                  Setup: <span className="text-white font-mono">{previewClip.pre_roll_sec}s</span> | Resolution:{" "}
                  <span className="text-white font-mono">{previewClip.post_roll_sec}s</span>
                </div>
                <Button
                  size="sm"
                  onClick={() => {
                    handleToggleSelect(previewClip);
                    closePreview();
                  }}
                  className={`text-xs ${previewClip.is_selected ? "bg-surface-3 text-text-secondary" : "bg-primary text-white"}`}
                >
                  {previewClip.is_selected ? "Deselect" : "Select for Shorts"}
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
