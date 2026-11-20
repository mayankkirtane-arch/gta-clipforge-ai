"use client";

import React, { useState, useEffect } from "react";
import { Header } from "@/components/layout/header";
import {
  api,
  Recording,
  RecordingPermission,
  RiskCheckItem,
  OfficialPolicyInfo,
  CopyrightSummary,
  AudioTrackInfo,
  PermissionStatus,
  RiskLevel,
} from "@/lib/api";
import {
  ShieldCheck,
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  XCircle,
  HelpCircle,
  Clock,
  ExternalLink,
  Save,
  RefreshCw,
  FileText,
  UserCheck,
  Lock,
  Unlock,
  Radio,
  Music,
  Play,
  Pause,
  Info,
  Sparkles,
  Scale,
  Ban,
  FileCheck,
} from "lucide-react";

export default function CopyrightCenterPage() {
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [selectedRecordingId, setSelectedRecordingId] = useState<number | null>(null);
  const [permission, setPermission] = useState<RecordingPermission | null>(null);
  const [summary, setSummary] = useState<CopyrightSummary | null>(null);
  const [policies, setPolicies] = useState<OfficialPolicyInfo[]>([]);
  const [musicTracks, setMusicTracks] = useState<AudioTrackInfo[]>([]);
  const [sfxTracks, setSfxTracks] = useState<AudioTrackInfo[]>([]);
  const [playingTrackId, setPlayingTrackId] = useState<string | null>(null);
  const [audioElement, setAudioElement] = useState<HTMLAudioElement | null>(null);

  // Form state
  const [originalCreator, setOriginalCreator] = useState<string>("");
  const [sourceUrl, setSourceUrl] = useState<string>("");
  const [writtenEvidence, setWrittenEvidence] = useState<string>("");
  const [permStatus, setPermStatus] = useState<PermissionStatus>("Not Requested");
  const [editingPerm, setEditingPerm] = useState<boolean>(false);
  const [redistribPerm, setRedistribPerm] = useState<boolean>(false);
  const [commercialPerm, setCommercialPerm] = useState<boolean>(false);
  const [expiryDate, setExpiryDate] = useState<string>("");
  const [disclaimerAck, setDisclaimerAck] = useState<boolean>(false);

  // Manual review state
  const [reviewStatus, setReviewStatus] = useState<"approved_by_user" | "rejected_by_user">("approved_by_user");
  const [reviewNotes, setReviewNotes] = useState<string>("");
  const [reviewerName, setReviewerName] = useState<string>("Lead Editor");

  // UI state
  const [loading, setLoading] = useState<boolean>(true);
  const [saving, setSaving] = useState<boolean>(false);
  const [reviewing, setReviewing] = useState<boolean>(false);
  const [feedbackMsg, setFeedbackMsg] = useState<{ type: "success" | "error"; text: string } | null>(null);
  const [activeTab, setActiveTab] = useState<"checks" | "policies" | "audio">("checks");

  useEffect(() => {
    initData();
  }, []);

  useEffect(() => {
    if (selectedRecordingId) {
      loadRecordingPermission(selectedRecordingId);
    }
  }, [selectedRecordingId]);

  const initData = async () => {
    setLoading(true);
    try {
      const [recsRes, summaryRes, policiesRes, musicRes, sfxRes] = await Promise.all([
        api.getRecordings(1, 50).catch(() => ({ items: [] } as any)),
        api.getCopyrightSummary().catch(() => null),
        api.getOfficialPolicies().catch(() => []),
        api.getMusicTracks().catch(() => []),
        api.getSfxTracks().catch(() => []),
      ]);

      const items = recsRes.items || [];
      setRecordings(items);
      setSummary(summaryRes);
      setPolicies(policiesRes);
      setMusicTracks(musicRes);
      setSfxTracks(sfxRes);

      if (items.length > 0) {
        setSelectedRecordingId(items[0].id);
      }
    } catch (e) {
      console.error("Failed to initialize Copyright Center", e);
    } finally {
      setLoading(false);
    }
  };

  const loadRecordingPermission = async (recordingId: number) => {
    try {
      const perm = await api.getRecordingPermission(recordingId);
      setPermission(perm);

      // Populate form fields
      setOriginalCreator(perm.original_creator || "");
      setSourceUrl(perm.source_url || "");
      setWrittenEvidence(perm.written_permission_evidence || "");
      setPermStatus(perm.permission_status);
      setEditingPerm(perm.editing_permission);
      setRedistribPerm(perm.redistribution_permission);
      setCommercialPerm(perm.commercial_monetization_permission);
      setDisclaimerAck(perm.disclaimer_acknowledged);

      if (perm.permission_expiry_date) {
        const d = new Date(perm.permission_expiry_date);
        setExpiryDate(d.toISOString().substring(0, 10));
      } else {
        setExpiryDate("");
      }

      if (perm.manual_review_notes) {
        setReviewNotes(perm.manual_review_notes);
      }
      if (perm.reviewer_name) {
        setReviewerName(perm.reviewer_name);
      }
    } catch (e) {
      console.error(`Failed to load permission for recording #${recordingId}`, e);
    }
  };

  const handleSavePermission = async () => {
    if (!selectedRecordingId) return;
    setSaving(true);
    setFeedbackMsg(null);
    try {
      const updateData = {
        original_creator: originalCreator,
        source_url: sourceUrl,
        written_permission_evidence: writtenEvidence,
        permission_status: permStatus,
        editing_permission: editingPerm,
        redistribution_permission: redistribPerm,
        commercial_monetization_permission: commercialPerm,
        permission_expiry_date: expiryDate ? new Date(expiryDate).toISOString() : null,
        disclaimer_acknowledged: disclaimerAck,
      };

      const updated = await api.updateRecordingPermission(selectedRecordingId, updateData);
      setPermission(updated);
      setFeedbackMsg({ type: "success", text: "Permissions saved & 9 risk checks re-evaluated successfully!" });

      // Refresh global summary metrics
      const newSummary = await api.getCopyrightSummary().catch(() => null);
      if (newSummary) setSummary(newSummary);
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err?.message || "Failed to save permissions." });
    } finally {
      setSaving(false);
    }
  };

  const handleManualReview = async () => {
    if (!selectedRecordingId) return;
    if (!reviewNotes.trim()) {
      alert("Please provide human review justification notes before submitting an override.");
      return;
    }
    setReviewing(true);
    setFeedbackMsg(null);
    try {
      const updated = await api.submitManualReview(selectedRecordingId, {
        status: reviewStatus,
        notes: reviewNotes,
        reviewer_name: reviewerName,
      });
      setPermission(updated);
      setFeedbackMsg({
        type: "success",
        text: `Manual review recorded: ${reviewStatus === "approved_by_user" ? "APPROVED FOR EXPORT" : "REJECTED"}.`,
      });

      const newSummary = await api.getCopyrightSummary().catch(() => null);
      if (newSummary) setSummary(newSummary);
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err?.message || "Failed to submit manual review." });
    } finally {
      setReviewing(false);
    }
  };

  const handleForceReassess = async () => {
    if (!selectedRecordingId) return;
    try {
      const updated = await api.assessRecordingRisk(selectedRecordingId);
      setPermission(updated);
      setFeedbackMsg({ type: "success", text: "Risk checks re-assessed against current policy baseline." });
    } catch (err: any) {
      setFeedbackMsg({ type: "error", text: err?.message || "Failed to reassess risk." });
    }
  };

  const togglePlay = (track: AudioTrackInfo) => {
    if (playingTrackId === track.id && audioElement) {
      audioElement.pause();
      setPlayingTrackId(null);
      return;
    }

    if (audioElement) {
      audioElement.pause();
    }

    const audio = new Audio(`${api["baseUrl"]}${track.stream_url}`);
    audio.play();
    audio.onended = () => setPlayingTrackId(null);
    setAudioElement(audio);
    setPlayingTrackId(track.id);
  };

  const getRiskBadge = (level: RiskLevel) => {
    switch (level) {
      case "LOW":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" /> LOW RISK
          </span>
        );
      case "MEDIUM":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-amber-500/20 text-amber-400 border border-amber-500/40 flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> MEDIUM RISK
          </span>
        );
      case "HIGH":
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-red-500/20 text-red-400 border border-red-500/40 flex items-center gap-1">
            <XCircle className="w-3 h-3" /> HIGH RISK
          </span>
        );
      default:
        return (
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-zinc-500/20 text-zinc-400 border border-zinc-500/40 flex items-center gap-1">
            <HelpCircle className="w-3 h-3" /> UNKNOWN
          </span>
        );
    }
  };

  const getStatusBadge = (status: PermissionStatus) => {
    switch (status) {
      case "Granted":
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
            Granted
          </span>
        );
      case "Pending":
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-amber-500/20 text-amber-300 border border-amber-500/30">
            Pending
          </span>
        );
      case "Rejected":
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-red-500/20 text-red-300 border border-red-500/30">
            Rejected
          </span>
        );
      case "Expired":
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-purple-500/20 text-purple-300 border border-purple-500/30">
            Expired
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-zinc-600/30 text-zinc-300 border border-zinc-500/30">
            Not Requested
          </span>
        );
    }
  };

  return (
    <div className="min-h-screen bg-background text-text-primary pb-16">
      <Header
        title="Copyright & Monetization Risk Center"
        subtitle="Creator permission management, 9-point risk evaluation, Take-Two IP boundaries, and YouTube reused-content safeguards."
      />

      <div className="p-6 max-w-7xl mx-auto space-y-6">
        {/* Prominent Legal Disclaimer Banner */}
        <div className="p-4 rounded-2xl border border-amber-500/40 bg-gradient-to-r from-amber-950/40 via-surface to-surface flex items-start gap-3.5 shadow-lg">
          <Scale className="w-6 h-6 text-amber-400 shrink-0 mt-0.5" />
          <div className="space-y-1 text-xs">
            <h4 className="font-bold text-amber-300 text-sm flex items-center gap-2">
              <span>Legal Advisory & Compliance Notice</span>
              <span className="text-[10px] px-2 py-0.5 rounded bg-amber-500/20 text-amber-200 border border-amber-500/30 font-normal">
                Not Legal Advice
              </span>
            </h4>
            <p className="text-text-muted leading-relaxed">
              GTA CLIPFORGE AI risk classifications, permission checks, and policy evaluations are <strong>advisory and educational tools only</strong> and <strong>do not constitute legal advice or formal IP clearance</strong>.
              Neither copyright safety nor YouTube monetization can ever be unconditionally guaranteed.
              Take-Two Interactive and YouTube retain unilateral enforcement authority. <strong>A creator&apos;s permission to use their recording only waives the creator&apos;s recording copyright; it does NOT grant Take-Two or Rockstar&apos;s underlying commercial rights.</strong>
            </p>
          </div>
        </div>

        {/* Global Summary Metrics */}
        {summary && (
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
            <div className="p-3.5 rounded-xl border border-border bg-surface shadow-sm">
              <span className="text-[10px] text-text-muted block font-semibold uppercase">Total Recordings</span>
              <strong className="text-lg text-white font-mono">{summary.total_recordings}</strong>
            </div>
            <div className="p-3.5 rounded-xl border border-emerald-500/30 bg-surface shadow-sm">
              <span className="text-[10px] text-emerald-400 block font-semibold uppercase">Permissions Granted</span>
              <strong className="text-lg text-emerald-400 font-mono">{summary.status_breakdown.granted}</strong>
            </div>
            <div className="p-3.5 rounded-xl border border-amber-500/30 bg-surface shadow-sm">
              <span className="text-[10px] text-amber-400 block font-semibold uppercase">Pending / Unrequested</span>
              <strong className="text-lg text-amber-400 font-mono">
                {summary.status_breakdown.pending + summary.status_breakdown.not_requested}
              </strong>
            </div>
            <div className="p-3.5 rounded-xl border border-red-500/30 bg-surface shadow-sm">
              <span className="text-[10px] text-red-400 block font-semibold uppercase">Rejected / Expired</span>
              <strong className="text-lg text-red-400 font-mono">
                {summary.status_breakdown.rejected + summary.status_breakdown.expired}
              </strong>
            </div>
            <div className="p-3.5 rounded-xl border border-emerald-500/40 bg-surface shadow-sm">
              <span className="text-[10px] text-emerald-300 block font-semibold uppercase">Export Authorized</span>
              <strong className="text-lg text-emerald-300 font-mono">{summary.can_export_count}</strong>
            </div>
            <div className="p-3.5 rounded-xl border border-red-500/40 bg-surface shadow-sm">
              <span className="text-[10px] text-red-300 block font-semibold uppercase">Export Blocked</span>
              <strong className="text-lg text-red-300 font-mono">{summary.blocked_export_count}</strong>
            </div>
          </div>
        )}

        {/* Recording Selector & Controls Bar */}
        <div className="p-4 rounded-xl border border-border bg-surface flex flex-col md:flex-row items-start md:items-center justify-between gap-4 shadow-md">
          <div className="flex flex-col sm:flex-row items-start sm:items-center gap-3 w-full md:w-auto">
            <label className="text-xs font-semibold text-text-muted shrink-0">
              Active Recording:
            </label>
            <select
              value={selectedRecordingId || ""}
              onChange={(e) => setSelectedRecordingId(Number(e.target.value))}
              className="w-full sm:w-80 px-3 py-2 rounded-lg bg-background border border-border text-white text-xs focus:outline-none focus:border-cyan-500"
            >
              {recordings.map((r) => (
                <option key={r.id} value={r.id}>
                  #{r.id} &bull; {r.original_filename} ({r.duration_seconds?.toFixed(0)}s)
                </option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-2 self-end md:self-center">
            <button
              onClick={handleForceReassess}
              className="px-3 py-1.5 rounded-lg border border-border bg-background hover:border-cyan-500 text-xs font-semibold text-text-muted hover:text-white transition-all flex items-center gap-1.5"
            >
              <RefreshCw className="w-3.5 h-3.5 text-cyan-400" />
              <span>Re-Scan Policies</span>
            </button>
          </div>
        </div>

        {/* Feedback Alert */}
        {feedbackMsg && (
          <div
            className={`p-3 rounded-xl border text-xs flex items-center justify-between ${
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

        {/* Export Authorization Status Banner */}
        {permission && (
          <div
            className={`p-5 rounded-2xl border transition-all shadow-xl flex flex-col md:flex-row items-start md:items-center justify-between gap-4 ${
              permission.can_export
                ? "border-emerald-500/40 bg-gradient-to-r from-emerald-950/40 via-surface to-surface"
                : "border-red-500/40 bg-gradient-to-r from-red-950/40 via-surface to-surface"
            }`}
          >
            <div className="flex items-center gap-3.5">
              <div
                className={`p-3 rounded-xl border ${
                  permission.can_export
                    ? "bg-emerald-500/10 border-emerald-500/30 text-emerald-400"
                    : "bg-red-500/10 border-red-500/30 text-red-400"
                }`}
              >
                {permission.can_export ? <ShieldCheck className="w-7 h-7" /> : <ShieldAlert className="w-7 h-7" />}
              </div>
              <div className="space-y-1">
                <div className="flex items-center gap-2">
                  <h3 className="text-base font-bold text-white">
                    {permission.can_export ? "EXPORT AUTHORIZED" : "EXPORT BLOCKED"}
                  </h3>
                  {getRiskBadge(permission.overall_risk_level)}
                  {getStatusBadge(permission.permission_status)}
                </div>
                <p className="text-xs text-text-muted max-w-2xl">
                  {permission.can_export
                    ? permission.manual_review_status === "approved_by_user"
                      ? "Shorts from this recording are authorized for export via human manual review override."
                      : "Creator permission is verified and scope checks are satisfied for video export."
                    : permission.export_block_reason || "Export blocked due to unverified creator permissions or copyright conflict."}
                </p>
              </div>
            </div>

            <div className="text-right shrink-0">
              <span className="text-[10px] text-text-muted block">Approval Gate</span>
              <strong
                className={`text-xs font-mono font-bold ${
                  permission.can_export ? "text-emerald-400" : "text-red-400"
                }`}
              >
                {permission.can_export ? "CAN APPROVE SHORTS" : "APPROVALS LOCKED"}
              </strong>
            </div>
          </div>
        )}

        {/* Tabs: Risk Checks / Policy Sources / DMCA Audio Assets */}
        <div className="flex items-center gap-2 border-b border-border pb-2">
          <button
            onClick={() => setActiveTab("checks")}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 ${
              activeTab === "checks"
                ? "bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-sm"
                : "text-text-muted hover:text-white"
            }`}
          >
            <ShieldCheck className="w-4 h-4 text-cyan-400" />
            <span>9-Point Risk Checks & Permissions</span>
          </button>
          <button
            onClick={() => setActiveTab("policies")}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 ${
              activeTab === "policies"
                ? "bg-purple-500/20 text-purple-300 border border-purple-500/40 shadow-sm"
                : "text-text-muted hover:text-white"
            }`}
          >
            <Scale className="w-4 h-4 text-purple-400" />
            <span>Official Policy Baselines ({policies.length})</span>
          </button>
          <button
            onClick={() => setActiveTab("audio")}
            className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all flex items-center gap-2 ${
              activeTab === "audio"
                ? "bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 shadow-sm"
                : "text-text-muted hover:text-white"
            }`}
          >
            <Music className="w-4 h-4 text-emerald-400" />
            <span>Verified DMCA-Safe Audio</span>
          </button>
        </div>

        {/* TAB 1: 9-Point Risk Checks & Creator Permission Management */}
        {activeTab === "checks" && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
            {/* Left 5 Cols: Permission Management Form */}
            <div className="lg:col-span-5 space-y-5">
              <div className="p-5 rounded-2xl border border-border bg-surface space-y-4 shadow-lg">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <div className="flex items-center gap-2">
                    <UserCheck className="w-4 h-4 text-cyan-400" />
                    <h3 className="font-bold text-white text-sm">Creator Permission System</h3>
                  </div>
                  {permission && getStatusBadge(permStatus)}
                </div>

                <div className="space-y-3.5 text-xs">
                  {/* Original Creator */}
                  <div>
                    <label className="text-text-muted font-semibold block mb-1">
                      Original Creator / Channel Handle
                    </label>
                    <input
                      type="text"
                      value={originalCreator}
                      onChange={(e) => setOriginalCreator(e.target.value)}
                      placeholder="e.g. ViceCityRacer / @ViceCityClips"
                      className="w-full px-3 py-2 rounded-lg bg-background border border-border text-white text-xs focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  {/* Source URL */}
                  <div>
                    <label className="text-text-muted font-semibold block mb-1">
                      Original Source Recording URL
                    </label>
                    <input
                      type="url"
                      value={sourceUrl}
                      onChange={(e) => setSourceUrl(e.target.value)}
                      placeholder="https://youtube.com/watch?v=... or Twitch VOD"
                      className="w-full px-3 py-2 rounded-lg bg-background border border-border text-white text-xs focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  {/* Permission Status & Expiry */}
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    <div>
                      <label className="text-text-muted font-semibold block mb-1">
                        Permission Status
                      </label>
                      <select
                        value={permStatus}
                        onChange={(e) => setPermStatus(e.target.value as PermissionStatus)}
                        className="w-full px-3 py-2 rounded-lg bg-background border border-border text-white text-xs focus:outline-none focus:border-cyan-500"
                      >
                        <option value="Not Requested">Not Requested</option>
                        <option value="Pending">Pending</option>
                        <option value="Granted">Granted</option>
                        <option value="Rejected">Rejected</option>
                        <option value="Expired">Expired</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-text-muted font-semibold block mb-1">
                        Expiry Date (Optional)
                      </label>
                      <input
                        type="date"
                        value={expiryDate}
                        onChange={(e) => setExpiryDate(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-background border border-border text-white text-xs focus:outline-none focus:border-cyan-500"
                      />
                    </div>
                  </div>

                  {/* Written Permission Evidence */}
                  <div>
                    <label className="text-text-muted font-semibold block mb-1">
                      Written Permission Evidence
                    </label>
                    <textarea
                      rows={3}
                      value={writtenEvidence}
                      onChange={(e) => setWrittenEvidence(e.target.value)}
                      placeholder="Paste email quote, Twitter/Discord DM transcript, or signed authorization agreement..."
                      className="w-full px-3 py-2 rounded-lg bg-background border border-border text-white text-xs focus:outline-none focus:border-cyan-500"
                    />
                  </div>

                  {/* Permission Scope Toggles */}
                  <div className="p-3.5 rounded-xl border border-border bg-background space-y-2.5">
                    <span className="text-[11px] font-bold text-text-primary block">
                      Authorized Permission Scopes
                    </span>

                    <label className="flex items-center gap-2.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={editingPerm}
                        onChange={(e) => setEditingPerm(e.target.checked)}
                        className="rounded border-border text-cyan-500 focus:ring-0"
                      />
                      <span className="text-xs text-text-muted">
                        <strong>Editing Permission:</strong> Creator allows cutting, speed ramping & reframing
                      </span>
                    </label>

                    <label className="flex items-center gap-2.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={redistribPerm}
                        onChange={(e) => setRedistribPerm(e.target.checked)}
                        className="rounded border-border text-cyan-500 focus:ring-0"
                      />
                      <span className="text-xs text-text-muted">
                        <strong>Redistribution Permission:</strong> Creator allows public sharing on YouTube Shorts
                      </span>
                    </label>

                    <label className="flex items-center gap-2.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={commercialPerm}
                        onChange={(e) => setCommercialPerm(e.target.checked)}
                        className="rounded border-border text-cyan-500 focus:ring-0"
                      />
                      <span className="text-xs text-text-muted">
                        <strong>Commercial Monetization:</strong> Creator allows monetizing resulting shorts
                      </span>
                    </label>
                  </div>

                  {/* Disclaimer Acknowledgement */}
                  <div className="p-3 rounded-xl border border-amber-500/30 bg-amber-950/20">
                    <label className="flex items-start gap-2.5 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={disclaimerAck}
                        onChange={(e) => setDisclaimerAck(e.target.checked)}
                        className="rounded border-amber-500 text-amber-500 focus:ring-0 mt-0.5"
                      />
                      <span className="text-[11px] text-amber-200 leading-tight">
                        I acknowledge that creator permission waives only their recording performance rights and <strong>never grants Take-Two/Rockstar commercial rights</strong>.
                      </span>
                    </label>
                  </div>

                  <button
                    onClick={handleSavePermission}
                    disabled={saving}
                    className="w-full py-2.5 rounded-xl text-xs font-bold bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    <Save className="w-4 h-4" />
                    <span>{saving ? "Saving..." : "Save Permissions & Evaluate Risk"}</span>
                  </button>
                </div>
              </div>

              {/* Manual Review Override Panel */}
              <div className="p-5 rounded-2xl border border-purple-500/30 bg-surface space-y-4 shadow-lg">
                <div className="flex items-center justify-between border-b border-border pb-3">
                  <div className="flex items-center gap-2">
                    <FileCheck className="w-4 h-4 text-purple-400" />
                    <h3 className="font-bold text-white text-sm">Human Manual Review</h3>
                  </div>
                  <span className="text-[10px] px-2 py-0.5 rounded bg-purple-500/20 text-purple-300 font-mono">
                    {permission?.manual_review_status || "pending_review"}
                  </span>
                </div>

                <p className="text-[11px] text-text-muted">
                  For edge cases where automated risk rules flag a clip but direct offline authorization or unique fair-use rationale exists.
                </p>

                <div className="space-y-3 text-xs">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="text-text-muted font-semibold block mb-1">Decision</label>
                      <select
                        value={reviewStatus}
                        onChange={(e) => setReviewStatus(e.target.value as any)}
                        className="w-full px-3 py-2 rounded-lg bg-background border border-border text-white text-xs focus:outline-none focus:border-purple-500"
                      >
                        <option value="approved_by_user">Approve for Export</option>
                        <option value="rejected_by_user">Reject & Block Export</option>
                      </select>
                    </div>

                    <div>
                      <label className="text-text-muted font-semibold block mb-1">Reviewer Name</label>
                      <input
                        type="text"
                        value={reviewerName}
                        onChange={(e) => setReviewerName(e.target.value)}
                        className="w-full px-3 py-2 rounded-lg bg-background border border-border text-white text-xs focus:outline-none focus:border-purple-500"
                      />
                    </div>
                  </div>

                  <div>
                    <label className="text-text-muted font-semibold block mb-1">
                      Justification & Evidence Notes (Required)
                    </label>
                    <textarea
                      rows={2}
                      value={reviewNotes}
                      onChange={(e) => setReviewNotes(e.target.value)}
                      placeholder="e.g. Verified explicit Discord DM license agreement with original streamer on 2026-11-16..."
                      className="w-full px-3 py-2 rounded-lg bg-background border border-border text-white text-xs focus:outline-none focus:border-purple-500"
                    />
                  </div>

                  <button
                    onClick={handleManualReview}
                    disabled={reviewing}
                    className="w-full py-2 rounded-xl text-xs font-semibold bg-purple-500/20 hover:bg-purple-500/30 text-purple-300 border border-purple-500/40 transition-all flex items-center justify-center gap-2 disabled:opacity-50"
                  >
                    <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                    <span>{reviewing ? "Applying..." : "Submit Manual Review Decision"}</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Right 7 Cols: 9-Point Risk Checks Matrix */}
            <div className="lg:col-span-7 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <ShieldCheck className="w-4 h-4 text-cyan-400" />
                  <h3 className="font-bold text-white text-sm">
                    9-Point Risk Assessment Matrix
                  </h3>
                </div>
                <span className="text-xs text-text-muted">
                  Overall: <strong className="text-white">{permission?.overall_risk_level || "UNKNOWN"}</strong>
                </span>
              </div>

              {(!permission || !permission.risk_checks || permission.risk_checks.length === 0) && (
                <div className="p-8 text-center border border-border rounded-2xl bg-surface text-text-muted text-xs">
                  No risk checks evaluated yet. Save permissions or click Re-Scan.
                </div>
              )}

              {permission?.risk_checks?.map((check: RiskCheckItem) => (
                <div
                  key={check.id}
                  className="p-4 rounded-xl border border-border bg-surface hover:border-cyan-500/30 transition-all space-y-2.5 shadow-sm"
                >
                  <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2">
                    <div className="flex items-center gap-2">
                      <span className="w-6 h-6 rounded-full bg-cyan-500/10 border border-cyan-500/30 text-cyan-400 text-xs font-mono font-bold flex items-center justify-center">
                        {check.number}
                      </span>
                      <h4 className="font-bold text-white text-xs">
                        {check.title}
                      </h4>
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-center">
                      <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-zinc-800 text-zinc-400">
                        {check.category.replace("_", " ")}
                      </span>
                      {getRiskBadge(check.risk_level)}
                    </div>
                  </div>

                  <p className="text-xs text-text-primary font-medium">
                    {check.summary}
                  </p>

                  <p className="text-[11px] text-text-muted leading-relaxed">
                    {check.details}
                  </p>

                  <div className="pt-2 border-t border-border/60 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 text-[11px]">
                    <div className="flex items-center gap-1.5 text-cyan-300">
                      <Info className="w-3.5 h-3.5 shrink-0" />
                      <span>{check.recommendation}</span>
                    </div>

                    {check.policy_url && (
                      <a
                        href={check.policy_url}
                        target="_blank"
                        rel="noreferrer"
                        className="text-[10px] text-purple-400 hover:text-purple-300 flex items-center gap-1 shrink-0 font-mono"
                      >
                        <span>Official Policy</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 2: Official Policy Sources & Legal Explainer */}
        {activeTab === "policies" && (
          <div className="space-y-6">
            {/* 4 Pillars of Enforcement Explainer */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <div className="p-4 rounded-xl border border-blue-500/30 bg-surface space-y-2 shadow-sm">
                <div className="flex items-center gap-2 text-blue-400">
                  <Radio className="w-4 h-4" />
                  <h4 className="font-bold text-xs uppercase">Content ID Claims</h4>
                </div>
                <p className="text-[11px] text-text-muted leading-relaxed">
                  Automated audio/video matching by YouTube. Ad revenue is redirected to the copyright owner (e.g., music labels). <strong>Does not issue a channel strike.</strong>
                </p>
              </div>

              <div className="p-4 rounded-xl border border-red-500/30 bg-surface space-y-2 shadow-sm">
                <div className="flex items-center gap-2 text-red-400">
                  <ShieldAlert className="w-4 h-4" />
                  <h4 className="font-bold text-xs uppercase">DMCA Strikes</h4>
                </div>
                <p className="text-[11px] text-text-muted leading-relaxed">
                  Formal legal takedown notice by copyright holder. Video is taken down; 1 channel strike issued. <strong>3 strikes leads to channel termination.</strong>
                </p>
              </div>

              <div className="p-4 rounded-xl border border-purple-500/30 bg-surface space-y-2 shadow-sm">
                <div className="flex items-center gap-2 text-purple-400">
                  <Scale className="w-4 h-4" />
                  <h4 className="font-bold text-xs uppercase">Legal Injunctions</h4>
                </div>
                <p className="text-[11px] text-text-muted leading-relaxed">
                  Take-Two legal enforcement against leaked builds, unauthorized asset sales, or commercial exploitation. Take-Two reserves absolute IP ownership.
                </p>
              </div>

              <div className="p-4 rounded-xl border border-amber-500/30 bg-surface space-y-2 shadow-sm">
                <div className="flex items-center gap-2 text-amber-400">
                  <AlertTriangle className="w-4 h-4" />
                  <h4 className="font-bold text-xs uppercase">Reused Content</h4>
                </div>
                <p className="text-[11px] text-text-muted leading-relaxed">
                  Internal YouTube Partner Program (YPP) policy. Mass unedited compilation of clips is demonetized for lack of transformative commentary.
                </p>
              </div>
            </div>

            {/* Official Policies List */}
            <div className="rounded-2xl border border-border bg-surface p-5 space-y-4 shadow-xl">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Scale className="w-4 h-4 text-cyan-400" />
                <span>Verified Official Publisher & Platform Policies</span>
              </h3>

              <div className="space-y-4">
                {policies.map((p) => (
                  <div
                    key={p.id}
                    className="p-4 rounded-xl border border-border bg-background space-y-3"
                  >
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 border-b border-border/60 pb-2">
                      <div>
                        <h4 className="font-bold text-white text-xs">{p.name}</h4>
                        <span className="text-[10px] text-text-muted font-mono">
                          {p.publisher_or_platform} &bull; Last Checked: {p.last_checked_date}
                        </span>
                      </div>
                      <a
                        href={p.policy_url}
                        target="_blank"
                        rel="noreferrer"
                        className="px-3 py-1 rounded-lg border border-cyan-500/40 bg-cyan-500/10 hover:bg-cyan-500/20 text-xs font-semibold text-cyan-300 flex items-center gap-1.5"
                      >
                        <span>Official Source Link</span>
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>

                    <div className="space-y-1.5 text-xs">
                      <span className="text-[11px] font-bold text-text-muted uppercase">Key Rules:</span>
                      <ul className="list-disc list-inside space-y-1 text-text-muted text-[11px]">
                        {p.key_rules.map((rule, idx) => (
                          <li key={idx}>{rule}</li>
                        ))}
                      </ul>
                    </div>

                    <div className="p-3 rounded-xl bg-surface border border-border/60 text-xs space-y-1">
                      <strong className="text-white block text-[11px]">Commercial Stance:</strong>
                      <p className="text-text-muted text-[11px]">{p.commercial_use_stance}</p>
                      <strong className="text-amber-300 block text-[11px] mt-1.5">Legal Distinction:</strong>
                      <p className="text-amber-200/80 text-[11px]">{p.legal_distinction_notes}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* TAB 3: Verified DMCA-Safe Audio Assets */}
        {activeTab === "audio" && (
          <div className="space-y-6">
            <div className="p-6 rounded-2xl border border-emerald-500/30 bg-gradient-to-r from-emerald-950/40 via-surface to-surface flex flex-col md:flex-row items-start md:items-center justify-between gap-6 shadow-xl">
              <div className="flex items-center gap-4">
                <div className="p-3.5 rounded-2xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-400">
                  <ShieldCheck className="w-8 h-8" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white">DMCA Safe Audio Engine Active</h3>
                  <p className="text-xs text-text-muted mt-1 max-w-xl">
                    Commercial radio music is strictly prohibited. All background tracks and sound effects below are procedurally synthesized or licensed under CC0 (Royalty-Free).
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-4 text-xs font-mono">
                <div className="px-3 py-2 rounded-xl bg-background border border-border text-center">
                  <span className="text-text-muted block text-[10px]">Verified Music</span>
                  <strong className="text-emerald-400 text-sm">{musicTracks.length} Tracks</strong>
                </div>
                <div className="px-3 py-2 rounded-xl bg-background border border-border text-center">
                  <span className="text-text-muted block text-[10px]">Verified SFX</span>
                  <strong className="text-cyan-400 text-sm">{sfxTracks.length} Effects</strong>
                </div>
              </div>
            </div>

            {/* Audio Track List */}
            <div className="rounded-2xl border border-border bg-surface p-5 space-y-4 shadow-xl">
              <h3 className="font-bold text-white text-sm flex items-center gap-2">
                <Music className="w-4 h-4 text-cyan-400" />
                <span>Verified DMCA-Free Music Tracks</span>
              </h3>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                {musicTracks.map((track) => {
                  const isPlaying = playingTrackId === track.id;
                  return (
                    <div
                      key={track.id}
                      className="p-3.5 rounded-xl border border-border bg-background hover:border-cyan-500/40 transition-all flex items-center justify-between gap-3 shadow-sm"
                    >
                      <div className="flex items-center gap-3">
                        <button
                          onClick={() => togglePlay(track)}
                          className={`p-2 rounded-lg border transition-all ${
                            isPlaying
                              ? "bg-cyan-500 text-black border-cyan-400 shadow-md shadow-cyan-500/30"
                              : "bg-surface border-border text-white hover:border-cyan-500"
                          }`}
                        >
                          {isPlaying ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                        </button>
                        <div>
                          <h4 className="font-bold text-white text-xs">{track.title}</h4>
                          <span className="text-[10px] text-text-muted font-mono">
                            {track.genre || "Procedural"} &bull; {track.duration_seconds?.toFixed(0)}s &bull; {track.license}
                          </span>
                        </div>
                      </div>

                      <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/20 text-emerald-300 font-mono">
                        Safe
                      </span>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
