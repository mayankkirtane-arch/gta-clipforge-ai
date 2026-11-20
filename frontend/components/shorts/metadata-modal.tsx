"use client";

import React, { useState, useEffect } from "react";
import {
  api,
  Clip,
  ClipMetadata,
  YouTubePublishPayload,
} from "@/lib/api";
import {
  Sparkles,
  Copy,
  Check,
  Type,
  Hash,
  MessageSquare,
  Image as ImageIcon,
  FileText,
  Youtube,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  X,
  Sliders,
  Share2,
  ArrowRight,
  Bookmark,
} from "lucide-react";

interface MetadataModalProps {
  clip: Clip | null;
  isOpen: boolean;
  onClose: () => void;
  onSaved?: (metadata: ClipMetadata) => void;
}

export function MetadataModal({ clip, isOpen, onClose, onSaved }: MetadataModalProps) {
  const [metadata, setMetadata] = useState<ClipMetadata | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [generating, setGenerating] = useState<boolean>(false);
  const [saving, setSaving] = useState<boolean>(false);
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [publishPayload, setPublishPayload] = useState<YouTubePublishPayload | null>(null);

  // Editable Form State
  const [activeTitle, setActiveTitle] = useState<string>("");
  const [activeDescription, setActiveDescription] = useState<string>("");
  const [activeHook, setActiveHook] = useState<string>("");
  const [activeHashtags, setActiveHashtags] = useState<string>("");
  const [activeThumbText, setActiveThumbText] = useState<string>("");
  const [activePinnedComment, setActivePinnedComment] = useState<string>("");

  // Options
  const [focusKeyword, setFocusKeyword] = useState<string>("");

  useEffect(() => {
    if (isOpen && clip) {
      loadMetadata(clip.id);
    }
  }, [isOpen, clip]);

  const loadMetadata = async (clipId: number) => {
    setLoading(true);
    try {
      const data = await api.getClipMetadata(clipId, true);
      setMetadata(data);
      initFormValues(data);
      loadPayload(clipId);
    } catch (e) {
      console.error("Failed to load clip metadata", e);
    } finally {
      setLoading(false);
    }
  };

  const loadPayload = async (clipId: number) => {
    try {
      const p = await api.getYouTubePublishPayload(clipId);
      setPublishPayload(p);
    } catch (e) {
      console.error("Failed to load publish payload", e);
    }
  };

  const initFormValues = (data: ClipMetadata) => {
    setActiveTitle(data.title || "");
    setActiveDescription(data.description || "");
    setActiveHook(data.hook || "");
    setActiveHashtags(data.hashtags || "");
    setActiveThumbText(data.thumbnail_text || "");
    setActivePinnedComment(data.pinned_comment || "");
  };

  const handleRegenerate = async () => {
    if (!clip) return;
    setGenerating(true);
    try {
      const fresh = await api.generateClipMetadata(clip.id, {
        focus_keyword: focusKeyword.trim() || undefined,
        overwrite: true,
      });
      setMetadata(fresh);
      initFormValues(fresh);
      loadPayload(clip.id);
    } catch (e: any) {
      alert(`Generation failed: ${e.message}`);
    } finally {
      setGenerating(false);
    }
  };

  const handleSave = async () => {
    if (!clip) return;
    setSaving(true);
    try {
      const updated = await api.updateClipMetadata(clip.id, {
        title: activeTitle,
        description: activeDescription,
        hook: activeHook,
        hashtags: activeHashtags,
        thumbnail_text: activeThumbText,
        pinned_comment: activePinnedComment,
      });
      setMetadata(updated);
      loadPayload(clip.id);
      if (onSaved) onSaved(updated);
      copyToClipboard(activeTitle, "saved");
    } catch (e: any) {
      alert(`Save failed: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const copyToClipboard = (text: string, fieldId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldId);
    setTimeout(() => {
      setCopiedField(null);
    }, 2000);
  };

  const copyAllYouTubeData = () => {
    if (!metadata) return;
    const fullBlock = [
      `=== YOUTUBE SHORTS PUBLISH DATA ===`,
      `TITLE (${activeTitle.length}/100 chars):`,
      activeTitle,
      ``,
      `DESCRIPTION:`,
      activeDescription,
      ``,
      `OPENING HOOK (FIRST 3s):`,
      activeHook,
      ``,
      `PINNED COMMENT:`,
      activePinnedComment,
      ``,
      `HASHTAGS:`,
      activeHashtags,
      `==================================`
    ].join("\n");
    copyToClipboard(fullBlock, "all_data");
  };

  if (!isOpen || !clip) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      <div className="relative w-full max-w-4xl max-h-[92vh] bg-surface border border-border rounded-2xl shadow-2xl flex flex-col overflow-hidden text-text-primary">
        {/* Header */}
        <div className="p-5 border-b border-border flex items-center justify-between bg-surface-2/40">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-cyan-500 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-cyan-500/20">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-base font-bold text-white">AI YouTube Shorts Metadata Studio</h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  Phase 8
                </span>
              </div>
              <p className="text-xs text-text-muted mt-0.5">
                Clip #{clip.id} &bull; {clip.title || "GTA 6 Short"} ({clip.duration?.toFixed(1)}s) &bull; Preset: {clip.preset_name || "Raw"}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleRegenerate}
              disabled={generating}
              className="px-3 py-1.5 rounded-lg border border-border bg-background hover:border-cyan-500 text-xs font-semibold text-text-muted hover:text-white transition-all flex items-center gap-1.5 disabled:opacity-50"
            >
              <RefreshCw className={`w-3.5 h-3.5 ${generating ? "animate-spin text-cyan-400" : ""}`} />
              <span>Regenerate Suggestions</span>
            </button>
            <button
              type="button"
              onClick={onClose}
              className="p-1.5 rounded-lg text-text-muted hover:text-white hover:bg-background transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Body Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {loading ? (
            <div className="py-20 flex flex-col items-center justify-center space-y-3">
              <RefreshCw className="w-8 h-8 animate-spin text-cyan-400" />
              <p className="text-xs font-medium text-text-muted">Generating AI Shorts Metadata from gameplay footage...</p>
            </div>
          ) : (
            <>
              {/* Quick Keyword Customization */}
              <div className="p-3 rounded-xl border border-border bg-background flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2 flex-1 min-w-[200px]">
                  <span className="text-xs text-text-muted shrink-0">Custom Focus / Car / Event:</span>
                  <input
                    type="text"
                    placeholder="e.g. Infernus, 5 Stars, Highway Jump"
                    value={focusKeyword}
                    onChange={(e) => setFocusKeyword(e.target.value)}
                    className="w-full bg-surface border border-border rounded-lg px-2.5 py-1 text-xs text-white focus:outline-none focus:border-cyan-500"
                  />
                </div>
                <button
                  type="button"
                  onClick={handleRegenerate}
                  disabled={generating}
                  className="px-3 py-1 rounded-lg bg-cyan-500 hover:bg-cyan-400 text-white text-xs font-semibold shadow transition-all"
                >
                  Apply &amp; Refresh
                </button>
              </div>

              {/* 1. Five Title Suggestions */}
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-white flex items-center gap-2">
                    <Type className="w-4 h-4 text-cyan-400" />
                    5 AI Title Suggestions (Click to Select)
                  </span>
                  <span className="text-[11px] text-text-muted">Footage-faithful &bull; High CTR &bull; No Clickbait</span>
                </div>

                <div className="space-y-2">
                  {metadata?.title_suggestions?.map((t, idx) => {
                    const isSelected = activeTitle === t;
                    return (
                      <div
                        key={idx}
                        onClick={() => setActiveTitle(t)}
                        className={`p-3 rounded-xl border cursor-pointer transition-all flex items-center justify-between gap-3 ${
                          isSelected
                            ? "bg-cyan-950/30 border-cyan-400 ring-1 ring-cyan-400/30 text-white"
                            : "bg-background border-border hover:border-zinc-500 text-text-secondary"
                        }`}
                      >
                        <div className="flex items-center gap-2.5 min-w-0">
                          <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold shrink-0 ${
                            isSelected ? "bg-cyan-500 text-black" : "bg-surface border border-border text-text-muted"
                          }`}>
                            {idx + 1}
                          </span>
                          <span className="text-xs font-semibold truncate">{t}</span>
                        </div>

                        <div className="flex items-center gap-2 shrink-0">
                          <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded ${
                            t.length <= 70 ? "text-emerald-400 bg-emerald-500/10" : "text-amber-400 bg-amber-500/10"
                          }`}>
                            {t.length}/100
                          </span>
                          <button
                            type="button"
                            onClick={(e) => {
                              e.stopPropagation();
                              copyToClipboard(t, `title_${idx}`);
                            }}
                            className="p-1 rounded text-text-muted hover:text-white"
                            title="Copy Title"
                          >
                            {copiedField === `title_${idx}` ? (
                              <Check className="w-3.5 h-3.5 text-emerald-400" />
                            ) : (
                              <Copy className="w-3.5 h-3.5" />
                            )}
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>

                {/* Active Title Input & Copy Title */}
                <div className="pt-1 space-y-1.5">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-medium text-text-muted">Selected YouTube Shorts Title:</span>
                    <div className="flex items-center gap-2">
                      <span className={`font-mono text-[11px] ${
                        activeTitle.length > 70 ? "text-amber-400" : "text-emerald-400"
                      }`}>
                        {activeTitle.length} / 100 chars
                      </span>
                      <button
                        type="button"
                        onClick={() => copyToClipboard(activeTitle, "active_title")}
                        className="px-2 py-0.5 rounded text-[11px] font-semibold bg-cyan-500/10 text-cyan-300 border border-cyan-500/30 hover:bg-cyan-500/20 transition-all flex items-center gap-1"
                      >
                        {copiedField === "active_title" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                        <span>Copy Title</span>
                      </button>
                    </div>
                  </div>
                  <input
                    type="text"
                    value={activeTitle}
                    onChange={(e) => setActiveTitle(e.target.value)}
                    className="w-full bg-background border border-border rounded-lg px-3 py-2 text-xs text-white focus:outline-none focus:border-cyan-500 font-semibold"
                  />
                </div>
              </div>

              {/* 2. Opening Hooks & Thumbnail Texts Grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* 3 Opening Hooks */}
                <div className="p-4 rounded-xl border border-border bg-background space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white flex items-center gap-1.5">
                      <MessageSquare className="w-3.5 h-3.5 text-purple-400" />
                      3 Opening Hooks (First 3-5s)
                    </span>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(activeHook, "active_hook")}
                      className="text-[11px] text-purple-400 hover:underline flex items-center gap-1"
                    >
                      {copiedField === "active_hook" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>Copy Hook</span>
                    </button>
                  </div>

                  <div className="space-y-2">
                    {metadata?.hook_suggestions?.map((h, i) => (
                      <div
                        key={i}
                        onClick={() => setActiveHook(h)}
                        className={`p-2.5 rounded-lg border text-xs cursor-pointer transition-all ${
                          activeHook === h
                            ? "bg-purple-950/30 border-purple-400 text-white font-medium"
                            : "bg-surface border-border hover:border-zinc-500 text-text-muted"
                        }`}
                      >
                        &ldquo;{h}&rdquo;
                      </div>
                    ))}
                  </div>
                </div>

                {/* Thumbnail Text Suggestions */}
                <div className="p-4 rounded-xl border border-border bg-background space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-bold text-white flex items-center gap-1.5">
                      <ImageIcon className="w-3.5 h-3.5 text-amber-400" />
                      Thumbnail Text Overlays
                    </span>
                    <span className="text-[10px] text-text-muted">Punchy &bull; High Contrast</span>
                  </div>

                  <div className="grid grid-cols-2 gap-2">
                    {metadata?.thumbnail_text_suggestions?.map((txt, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => setActiveThumbText(txt)}
                        className={`p-2 rounded-lg border text-xs font-bold tracking-wide transition-all ${
                          activeThumbText === txt
                            ? "bg-amber-500 text-black border-amber-400 shadow-md shadow-amber-500/20"
                            : "bg-surface border-border text-text-secondary hover:border-amber-400"
                        }`}
                      >
                        {txt}
                      </button>
                    ))}
                  </div>

                  <input
                    type="text"
                    value={activeThumbText}
                    onChange={(e) => setActiveThumbText(e.target.value)}
                    placeholder="Custom Thumbnail Text..."
                    className="w-full bg-surface border border-border rounded px-2.5 py-1 text-xs text-white"
                  />
                </div>
              </div>

              {/* 3. Description & Copy Description */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-xs">
                  <span className="font-bold text-white flex items-center gap-2">
                    <FileText className="w-4 h-4 text-emerald-400" />
                    YouTube Shorts Description
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-[11px] text-text-muted">
                      {activeDescription.length} / 5000 chars
                    </span>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(activeDescription, "active_desc")}
                      className="px-2.5 py-1 rounded text-xs font-semibold bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 hover:bg-emerald-500/20 transition-all flex items-center gap-1"
                    >
                      {copiedField === "active_desc" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                      <span>Copy Description</span>
                    </button>
                  </div>
                </div>

                <textarea
                  rows={5}
                  value={activeDescription}
                  onChange={(e) => setActiveDescription(e.target.value)}
                  className="w-full bg-background border border-border rounded-xl p-3 text-xs text-text-primary focus:outline-none focus:border-cyan-500 font-mono leading-relaxed"
                />
              </div>

              {/* 4. Hashtags & Pinned Comments */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
                {/* Hashtags */}
                <div className="p-4 rounded-xl border border-border bg-background space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-white flex items-center gap-1.5">
                      <Hash className="w-3.5 h-3.5 text-cyan-400" />
                      Curated Hashtags ({activeHashtags.split(/\s+/).filter(Boolean).length})
                    </span>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(activeHashtags, "active_hashtags")}
                      className="text-[11px] text-cyan-400 hover:underline flex items-center gap-1"
                    >
                      {copiedField === "active_hashtags" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>Copy Tags</span>
                    </button>
                  </div>
                  <input
                    type="text"
                    value={activeHashtags}
                    onChange={(e) => setActiveHashtags(e.target.value)}
                    className="w-full bg-surface border border-border rounded px-2.5 py-1.5 text-xs text-white font-mono"
                  />
                  <p className="text-[10px] text-text-muted">
                    Curated to 4-5 relevant tags. Avoids YouTube spam filters while maximizing reach.
                  </p>
                </div>

                {/* Pinned Comment */}
                <div className="p-4 rounded-xl border border-border bg-background space-y-2">
                  <div className="flex items-center justify-between text-xs">
                    <span className="font-bold text-white flex items-center gap-1.5">
                      <MessageSquare className="w-3.5 h-3.5 text-rose-400" />
                      Pinned Engagement Comment
                    </span>
                    <button
                      type="button"
                      onClick={() => copyToClipboard(activePinnedComment, "active_pinned")}
                      className="text-[11px] text-rose-400 hover:underline flex items-center gap-1"
                    >
                      {copiedField === "active_pinned" ? <Check className="w-3 h-3 text-emerald-400" /> : <Copy className="w-3 h-3" />}
                      <span>Copy Comment</span>
                    </button>
                  </div>
                  <input
                    type="text"
                    value={activePinnedComment}
                    onChange={(e) => setActivePinnedComment(e.target.value)}
                    className="w-full bg-surface border border-border rounded px-2.5 py-1.5 text-xs text-white"
                  />
                  <div className="flex gap-1 overflow-x-auto pt-1">
                    {metadata?.pinned_comment_suggestions?.map((c, i) => (
                      <button
                        key={i}
                        type="button"
                        onClick={() => setActivePinnedComment(c)}
                        className="text-[10px] px-2 py-0.5 rounded bg-surface border border-border text-text-muted hover:text-white shrink-0 truncate max-w-[140px]"
                      >
                        Option {i + 1}
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* YouTube Shorts Publishing Readiness Checklist */}
              {publishPayload && (
                <div className="p-4 rounded-xl bg-surface-2/30 border border-border flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
                  <div className="flex items-center gap-3">
                    <div className="p-2 rounded-lg bg-red-500/10 text-red-400 border border-red-500/30">
                      <Youtube className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-bold text-white">YouTube Shorts Compliance:</span>
                        {publishPayload.is_valid_for_youtube ? (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/40">
                            Ready to Publish
                          </span>
                        ) : (
                          <span className="px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/40">
                            Needs Review
                          </span>
                        )}
                      </div>
                      <p className="text-[11px] text-text-muted mt-0.5 font-mono">
                        9:16 vertical &bull; Category: Gaming &bull; Title: {publishPayload.char_count_title} chars &bull; Description: {publishPayload.char_count_description} chars
                      </p>
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={copyAllYouTubeData}
                    className="px-3 py-1.5 rounded-lg border border-border bg-surface hover:border-cyan-500 text-xs font-semibold text-white transition-all flex items-center gap-1.5 shrink-0"
                  >
                    {copiedField === "all_data" ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5 text-cyan-400" />}
                    <span>Copy All YouTube Data</span>
                  </button>
                </div>
              )}
            </>
          )}
        </div>

        {/* Footer Actions */}
        <div className="p-4 border-t border-border bg-surface-2/60 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2">
            {copiedField === "saved" && (
              <span className="text-xs text-emerald-400 flex items-center gap-1 animate-pulse">
                <CheckCircle2 className="w-3.5 h-3.5" />
                Saved to SQLite!
              </span>
            )}
          </div>

          <div className="flex items-center gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold text-text-muted hover:text-white transition-colors"
            >
              Close
            </button>
            <button
              type="button"
              disabled={saving || loading}
              onClick={handleSave}
              className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-gradient-to-r from-cyan-500 to-purple-600 hover:from-cyan-400 hover:to-purple-500 shadow-lg shadow-cyan-500/20 transition-all flex items-center gap-1.5 disabled:opacity-50"
            >
              {saving ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Bookmark className="w-3.5 h-3.5" />}
              <span>Save Metadata in SQLite</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
