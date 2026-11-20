const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export interface DashboardStats {
  total_recordings: number;
  total_clips_generated: number;
  processing_jobs: number;
  approved_clips: number;
}

export interface SystemStatus {
  database: string;
  storage_recordings: string;
  storage_exports: string;
  storage_temp: string;
  free_space_gb: number | null;
  total_space_gb: number | null;
  version: string;
}

export interface Recording {
  id: number;
  filename: string;
  original_filename: string;
  file_path: string;
  file_size_bytes: number | null;
  duration_seconds: number | null;
  resolution: string | null;
  fps: number | null;
  file_hash?: string | null;
  video_codec?: string | null;
  audio_codec?: string | null;
  bitrate?: number | null;
  status: "pending" | "analyzing" | "analyzed" | "failed";
  notes: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface RecordingList {
  items: Recording[];
  total: number;
  page: number;
  page_size: number;
}

export interface Clip {
  id: number;
  recording_id: number;
  candidate_clip_id?: number | null;
  detected_moment_id?: number | null;
  title: string | null;
  description: string | null;
  moment_type: string;
  start_time: number | null;
  end_time: number | null;
  duration: number | null;
  resolution?: string | null;
  aspect_ratio?: string | null;
  fps?: number | null;
  video_codec?: string | null;
  audio_codec?: string | null;
  render_mode?: string | null;
  has_subtitles?: boolean;
  subtitle_text?: string | null;
  subtitle_style?: string | null;
  clip_path?: string | null;
  stream_url?: string | null;
  thumbnail_path?: string | null;
  thumbnail_url?: string | null;
  file_size_bytes?: number | null;
  excitement_score: number | null;
  ai_tags?: string | null;
  status: string;
  is_approved: boolean;
  error_message?: string | null;
  // Phase 7 Cinematic fields
  edit_mode?: string | null;
  preset_name?: string | null;
  zoom_intensity?: number | null;
  slowmo_speed?: number | null;
  color_grading_intensity?: number | null;
  audio_volume?: number | null;
  music_volume?: number | null;
  music_track_id?: string | null;
  sfx_track_id?: string | null;
  transition_duration?: number | null;
  effects_applied?: string | null;
  created_at: string | null;
  updated_at?: string | null;
}

export interface CinematicPresetInfo {
  id: string;
  name: string;
  description: string;
  tagline: string;
  icon: string;
  color: string;
  default_zoom: number;
  default_slowmo: number;
  color_grade_desc: string;
  audio_profile: string;
  suggested_music: string;
  suggested_sfx: string;
}

export interface AudioTrackInfo {
  id: string;
  title: string;
  category: "music" | "sfx";
  genre: string;
  duration_seconds: number;
  license: string;
  copyright_safe: boolean;
  stream_url: string;
}

export interface CinematicPreviewOptions {
  recording_id: number;
  start_time: number;
  end_time: number;
  edit_mode?: "raw" | "cinematic";
  preset_name?: string;
  render_mode?: "blurred_background" | "smart_crop" | "action_hybrid";
  zoom_intensity?: number;
  slowmo_speed?: number;
  color_grading_intensity?: number;
  audio_volume?: number;
  music_volume?: number;
  music_track_id?: string | null;
  sfx_track_id?: string | null;
  preview_duration?: number;
}

export interface CinematicPreviewResult {
  status: string;
  preview_url: string;
  file_path: string;
  duration: number;
  preset_name: string;
  edit_mode: string;
}

export interface CinematicEditOptions {
  recording_id: number;
  clip_id?: number;
  candidate_clip_id?: number;
  title?: string;
  start_time?: number;
  end_time?: number;
  edit_mode?: "raw" | "cinematic";
  preset_name?: string;
  render_mode?: "blurred_background" | "smart_crop" | "action_hybrid";
  target_length?: number;
  zoom_intensity?: number;
  slowmo_speed?: number;
  color_grading_intensity?: number;
  audio_volume?: number;
  music_volume?: number;
  music_track_id?: string | null;
  sfx_track_id?: string | null;
  transition_duration?: number;
  subtitles?: boolean;
  subtitle_text?: string;
  subtitle_style?: string;
  fps?: number;
  use_gpu?: boolean;
}

export interface CinematicRenderResult {
  success: boolean;
  clip: {
    clip_id: number;
    title: string;
    preset_name: string;
    edit_mode: string;
    file_path: string;
    thumbnail_path?: string | null;
    stream_url: string;
    thumbnail_url?: string | null;
    resolution: string;
    aspect_ratio: string;
    duration: number;
    fps: number;
    file_size_bytes: number;
    verification?: ShortVerificationResult;
  };
  verification?: ShortVerificationResult;
}

// Phase 8: AI YouTube Shorts Metadata Generator Interfaces
export interface ClipMetadata {
  id: number;
  clip_id: number;
  title: string;
  description: string;
  hook?: string | null;
  hashtags: string;
  thumbnail_text?: string | null;
  pinned_comment?: string | null;
  title_suggestions: string[];
  hook_suggestions: string[];
  hashtag_suggestions: string[];
  thumbnail_text_suggestions: string[];
  pinned_comment_suggestions: string[];
  generation_context?: Record<string, any> | null;
  is_user_edited: boolean;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ClipMetadataUpdateOptions {
  title?: string;
  description?: string;
  hook?: string;
  hashtags?: string;
  thumbnail_text?: string;
  pinned_comment?: string;
}

export interface ClipMetadataGenerateOptions {
  tone?: "viral" | "cinematic" | "humorous" | "dramatic";
  focus_keyword?: string;
  overwrite?: boolean;
}

export interface YouTubePublishPayload {
  clip_id: number;
  title: string;
  description: string;
  tags: string[];
  privacy_status: string;
  made_for_kids: boolean;
  category_id: string;
  pinned_comment?: string | null;
  thumbnail_text?: string | null;
  opening_hook?: string | null;
  video_path?: string | null;
  resolution: string;
  aspect_ratio: string;
  duration_seconds?: number | null;
  char_count_title: number;
  char_count_description: number;
  is_valid_for_youtube: boolean;
  validation_warnings: string[];
}

export interface ShortVerificationResult {
  is_valid: boolean;
  clip_id: number;
  file_path: string;
  width: number;
  height: number;
  aspect_ratio: string;
  duration: number;
  expected_duration: number;
  duration_difference: number;
  video_codec: string;
  audio_codec: string;
  fps: number;
  file_size_bytes: number;
  checks: Record<string, boolean>;
  error?: string | null;
}

export interface ShortGenerationOptions {
  recording_id: number;
  candidate_clip_id?: number;
  detected_moment_id?: number;
  title?: string;
  start_time?: number;
  end_time?: number;
  target_length?: number;
  render_mode?: "blurred_background" | "smart_crop" | "action_hybrid";
  subtitles?: boolean;
  subtitle_text?: string;
  subtitle_style?: string;
  fps?: number;
  use_gpu?: boolean;
}

export interface BatchShortGenerationOptions {
  recording_id: number;
  candidate_clip_ids?: number[];
  select_top_n?: number;
  target_length?: number;
  render_mode?: "blurred_background" | "smart_crop" | "action_hybrid";
  subtitles?: boolean;
  subtitle_style?: string;
  use_gpu?: boolean;
}

export interface Job {
  id: number;
  recording_id: number | null;
  recording_filename?: string | null;
  job_type: "analysis" | "moment_detection" | "clip_ranking" | "clip_generation" | "export";
  status: "pending" | "queued" | "processing" | "running" | "completed" | "failed" | "cancelled";
  progress: number;
  message: string | null;
  error: string | null;
  started_at?: string | null;
  completed_at?: string | null;
  created_at: string | null;
}

export interface DetectedMoment {
  id: number;
  recording_id: number;
  event_type: string;
  event_label: string;
  start_time: number;
  end_time: number;
  duration: number;
  confidence_score: number;
  explanation: string;
  is_uncertain: boolean;
  uncertainty_reason?: string | null;
  thumbnail_path?: string | null;
  thumbnail_url?: string | null;
  keyframe_timestamp?: number | null;
  visual_features?: Record<string, any> | null;
  detection_sensitivity?: string;
  status: "detected" | "approved" | "rejected" | "converted";
  is_approved: boolean;
  notes?: string | null;
  clip_id?: number | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface DetectedMomentSummary {
  total_moments: number;
  approved_moments: number;
  uncertain_moments: number;
  high_confidence_moments: number;
  event_counts: Record<string, number>;
}

export interface DetectedMomentList {
  items: DetectedMoment[];
  total: number;
  page: number;
  page_size: number;
  summary?: DetectedMomentSummary;
}

export interface EventTypeInfo {
  id: string;
  label: string;
  description: string;
  color: string;
  icon: string;
}

export interface MomentDetectionOptions {
  sensitivity?: "low" | "medium" | "high";
  min_confidence?: number;
  min_duration_sec?: number;
  max_duration_sec?: number;
  merge_gap_sec?: number;
  enabled_event_types?: string[];
  use_vlm?: boolean;
  force_redetect?: boolean;
}

// --- Phase 5: Candidate Clips & AI Ranking ---
export interface CandidateClip {
  id: number;
  recording_id: number;
  detected_moment_id?: number | null;
  category: string;
  category_label: string;
  title: string;
  start_time: number;
  end_time: number;
  duration: number;
  target_length: number;
  climax_time: number;
  pre_roll_sec: number;
  post_roll_sec: number;
  ai_score: number;
  score_breakdown?: {
    visual_excitement: number;
    unexpectedness: number;
    action_intensity: number;
    cinematic_quality: number;
    entertainment_value: number;
    audio_excitement: number;
    event_completeness: number;
    boundary_quality: number;
    duplicate_penalty: number;
  } | null;
  score_reason: string;
  is_selected: boolean;
  selection_rank?: number | null;
  thumbnail_path?: string | null;
  thumbnail_url?: string | null;
  status: "candidate" | "selected" | "approved" | "rejected" | "exported";
  is_approved: boolean;
  notes?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface CandidateClipSummary {
  total_candidates: number;
  selected_count: number;
  approved_count: number;
  top_score: number;
  category_counts: Record<string, number>;
  duration_counts: Record<number, number>;
}

export interface CandidateClipList {
  items: CandidateClip[];
  total: number;
  page: number;
  page_size: number;
  summary?: CandidateClipSummary | null;
}

export interface ClipCategoryInfo {
  id: string;
  label: string;
  description: string;
  color: string;
  icon: string;
}

export interface ClipRankingTriggerOptions {
  target_lengths?: number[];
  categories?: string[];
  min_score?: number;
  force_rerank?: boolean;
}

export interface SceneSummary {
  scene_number: number;
  start_time: number;
  end_time: number;
  duration: number;
}

export interface RecordingAnalysis {
  id?: number;
  recording_id: number;
  status: "pending" | "processing" | "completed" | "failed";
  progress: number;
  current_chunk: number;
  total_chunks: number;
  total_scenes: number;
  total_keyframes: number;
  audio_peaks_count: number;
  black_frames_count: number;
  silence_count: number;
  waveform_data: number[];
  scenes_data: SceneSummary[];
  has_proxy: boolean;
  has_thumbnail: boolean;
  gpu_accelerated?: boolean;
  chunk_duration_sec?: number;
  error?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface TimelineSegment {
  id: number;
  timestamp: number;
  timestamp_formatted: string;
  scene_number: number;
  keyframe_url: string | null;
  keyframe_filename: string | null;
  audio_peak_db: number | null;
  is_audio_peak: boolean;
  is_scene_change: boolean;
  is_black_frame: boolean;
  is_silence: boolean;
  excitement_score: number;
  chunk_index: number;
}

export interface TimelineList {
  items: TimelineSegment[];
  total: number;
  page: number;
  page_size: number;
}

export interface WatcherSettings {
  enable_auto_mode: boolean;
  monitoring_paused: boolean;
  auto_analyze: boolean;
  auto_generate_clips: boolean;
  require_approval: boolean;
  watch_folder_path: string;
  watcher_running?: boolean;
  active_watch_path?: string;
}

export interface HealthCheck {
  status: string;
  app: string;
  version: string;
  database: string;
}

// --- Phase 9: Copyright and Monetization Risk Center ---
export type RiskLevel = "LOW" | "MEDIUM" | "HIGH" | "UNKNOWN";
export type PermissionStatus = "Not Requested" | "Pending" | "Granted" | "Rejected" | "Expired";
export type ManualReviewStatus = "pending_review" | "approved_by_user" | "rejected_by_user" | "not_required";

export interface RiskCheckItem {
  id: string;
  number: number;
  title: string;
  category: string;
  risk_level: RiskLevel;
  summary: string;
  details: string;
  recommendation: string;
  policy_url?: string | null;
  last_checked_date?: string | null;
}

export interface RecordingPermission {
  id: number;
  recording_id: number;
  original_creator: string | null;
  source_url: string | null;
  written_permission_evidence: string | null;
  permission_status: PermissionStatus;
  editing_permission: boolean;
  redistribution_permission: boolean;
  commercial_monetization_permission: boolean;
  permission_expiry_date: string | null;
  is_expired: boolean;
  overall_risk_level: RiskLevel;
  can_export: boolean;
  export_block_reason: string | null;
  risk_checks: RiskCheckItem[];
  manual_review_status: ManualReviewStatus;
  manual_review_notes: string | null;
  reviewer_name: string | null;
  reviewed_at: string | null;
  disclaimer_acknowledged: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface RecordingPermissionUpdateOptions {
  original_creator?: string | null;
  source_url?: string | null;
  written_permission_evidence?: string | null;
  permission_status?: PermissionStatus;
  editing_permission?: boolean;
  redistribution_permission?: boolean;
  commercial_monetization_permission?: boolean;
  permission_expiry_date?: string | null;
  disclaimer_acknowledged?: boolean;
}

export interface ManualReviewOptions {
  status: "approved_by_user" | "rejected_by_user";
  notes: string;
  reviewer_name?: string;
}

export interface OfficialPolicyInfo {
  id: string;
  name: string;
  publisher_or_platform: string;
  policy_url: string;
  last_checked_date: string;
  key_rules: string[];
  commercial_use_stance: string;
  legal_distinction_notes: string;
}

export interface CopyrightSummary {
  total_recordings: number;
  status_breakdown: {
    not_requested: number;
    pending: number;
    granted: number;
    rejected: number;
    expired: number;
  };
  risk_breakdown: {
    low: number;
    medium: number;
    high: number;
    unknown: number;
  };
  can_export_count: number;
  blocked_export_count: number;
  last_policy_check: string;
  legal_notice: string;
}

// --- Phase 10: Publishing Workspace & Production Export ---
export type PublishingStatus = "draft" | "ready" | "scheduled" | "published" | "archived";

export interface PublishingMetrics {
  views_count: number;
  likes_count: number;
  comments_count: number;
  shares_count: number;
  watch_time_hours: number;
  avg_view_duration_pct: number;
  ctr_pct?: number;
}

export interface PublishingItem {
  id: number;
  clip_id: number;
  recording_id?: number | null;
  active_title: string;
  description: string;
  hashtags: string;
  hook?: string | null;
  thumbnail_text?: string | null;
  pinned_comment?: string | null;
  draft_titles: string[];
  status: PublishingStatus;
  planned_publish_date?: string | null;
  published_at?: string | null;
  youtube_video_id?: string | null;
  youtube_video_url?: string | null;
  checklist: Record<string, boolean>;
  checklist_completion_pct: number;
  metrics: PublishingMetrics;
  analytics_source: string;
  last_analytics_sync?: string | null;
  notes?: string | null;
  duration?: number | null;
  preset_name?: string | null;
  thumbnail_url?: string | null;
  clip_download_url?: string | null;
  srt_download_url?: string | null;
  txt_download_url?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface PublishingItemUpdateOptions {
  active_title?: string;
  description?: string;
  hashtags?: string;
  hook?: string;
  thumbnail_text?: string;
  pinned_comment?: string;
  status?: PublishingStatus;
  planned_publish_date?: string | null;
  youtube_video_id?: string;
  youtube_video_url?: string;
  checklist_updates?: Record<string, boolean>;
  notes?: string;
}

export interface PublishingMetricsUpdateOptions {
  views_count?: number;
  likes_count?: number;
  comments_count?: number;
  shares_count?: number;
  watch_time_hours?: number;
  avg_view_duration_pct?: number;
  analytics_source?: string;
}

export interface PublishingWorkspaceSummary {
  total_items: number;
  draft_count: number;
  ready_count: number;
  scheduled_count: number;
  published_count: number;
  archived_count: number;
  total_views: number;
  total_likes: number;
  total_watch_hours: number;
  avg_performance_ctr: number;
}

export interface ExportPackageOptions {
  clip_ids?: number[];
  include_subtitles_srt?: boolean;
  include_transcripts_txt?: boolean;
  include_metadata_csv?: boolean;
  include_copyright_reports?: boolean;
  include_thumbnails?: boolean;
  package_name?: string;
}

export interface ExportPackageResult {
  status: string;
  zip_filename: string;
  zip_path: string;
  zip_size_bytes: number;
  zip_download_url: string;
  clips_exported_count: number;
  files_included: string[];
}

class ApiClient {
  private _configuredBaseUrl: string;

  constructor(baseUrl: string) {
    this._configuredBaseUrl = baseUrl;
  }

  get baseUrl(): string {
    if (typeof window !== "undefined") {
      return "";
    }
    return this._configuredBaseUrl;
  }

  private async fetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      cache: "no-store",
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers || {}),
      },
    });
    if (!response.ok) {
      let detail = `${response.status} ${response.statusText}`;
      try {
        const errJson = await response.json();
        if (errJson && errJson.detail) {
          detail = typeof errJson.detail === "string" ? errJson.detail : JSON.stringify(errJson.detail);
        }
      } catch {}
      throw new Error(detail);
    }
    return response.json();
  }

  async health(): Promise<HealthCheck> {
    return this.fetch<HealthCheck>("/health");
  }

  async getDashboardStats(): Promise<DashboardStats> {
    return this.fetch<DashboardStats>("/api/stats/dashboard");
  }

  async getSystemStatus(): Promise<SystemStatus> {
    return this.fetch<SystemStatus>("/api/stats/system");
  }

  async getRecordings(page = 1, pageSize = 10, status?: string, q?: string): Promise<RecordingList> {
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) });
    if (status && status !== "all") params.append("status", status);
    if (q && q.trim()) params.append("q", q.trim());
    return this.fetch<RecordingList>(`/api/recordings?${params.toString()}`);
  }

  async getRecording(id: number): Promise<Recording> {
    return this.fetch<Recording>(`/api/recordings/${id}`);
  }

  async importLocalRecording(filePath: string, notes?: string): Promise<Recording> {
    return this.fetch<Recording>("/api/recordings/import-local", {
      method: "POST",
      body: JSON.stringify({ file_path: filePath, notes }),
    });
  }

  async uploadRecording(file: File, notes?: string): Promise<Recording> {
    const formData = new FormData();
    formData.append("file", file);
    if (notes) formData.append("notes", notes);

    const response = await fetch(`${this.baseUrl}/api/recordings/upload`, {
      method: "POST",
      body: formData,
    });
    if (!response.ok) {
      let detail = `${response.status} ${response.statusText}`;
      try {
        const err = await response.json();
        if (err.detail) detail = typeof err.detail === "string" ? err.detail : JSON.stringify(err.detail);
      } catch {}
      throw new Error(detail);
    }
    return response.json();
  }

  async reprocessRecording(id: number): Promise<Recording> {
    return this.fetch<Recording>(`/api/recordings/${id}/reprocess`, {
      method: "POST",
    });
  }

  async deleteRecording(id: number, deleteFile = false): Promise<any> {
    return this.fetch(`/api/recordings/${id}?delete_file=${deleteFile}`, {
      method: "DELETE",
    });
  }

  async getClips(params?: {
    recording_id?: number;
    status?: string;
    render_mode?: string;
    page?: number;
    page_size?: number;
    sort_by?: string;
    sort_order?: string;
  }): Promise<Clip[]> {
    const q = new URLSearchParams();
    if (params?.recording_id) q.append("recording_id", String(params.recording_id));
    if (params?.status && params.status !== "all") q.append("status", params.status);
    if (params?.render_mode && params.render_mode !== "all") q.append("render_mode", params.render_mode);
    if (params?.page) q.append("page", String(params.page));
    if (params?.page_size) q.append("page_size", String(params.page_size));
    if (params?.sort_by) q.append("sort_by", params.sort_by);
    if (params?.sort_order) q.append("sort_order", params.sort_order);
    return this.fetch<Clip[]>(`/api/clips?${q.toString()}`);
  }

  async getClip(clipId: number): Promise<Clip> {
    return this.fetch<Clip>(`/api/clips/${clipId}`);
  }

  async generateShort(options: ShortGenerationOptions): Promise<Clip> {
    return this.fetch<Clip>("/api/clips/generate", {
      method: "POST",
      body: JSON.stringify(options),
    });
  }

  async batchGenerateShorts(options: BatchShortGenerationOptions): Promise<{ status: string; job_id: number; recording_id: number; message: string }> {
    return this.fetch("/api/clips/batch-generate", {
      method: "POST",
      body: JSON.stringify(options),
    });
  }

  async approveClip(clipId: number): Promise<Clip> {
    return this.fetch<Clip>(`/api/clips/${clipId}/approve`, {
      method: "PATCH",
    });
  }

  async rejectClip(clipId: number): Promise<Clip> {
    return this.fetch<Clip>(`/api/clips/${clipId}/reject`, {
      method: "PATCH",
    });
  }

  async deleteClip(clipId: number, deleteFile = false): Promise<any> {
    return this.fetch(`/api/clips/${clipId}?delete_file=${deleteFile}`, {
      method: "DELETE",
    });
  }

  async verifyClip(clipId: number): Promise<ShortVerificationResult> {
    return this.fetch<ShortVerificationResult>(`/api/clips/${clipId}/verify`);
  }

  getClipStreamUrl(clipId: number): string {
    return `${this.baseUrl}/api/clips/${clipId}/stream`;
  }

  getClipThumbnailUrl(clipId: number): string {
    return `${this.baseUrl}/api/clips/${clipId}/thumbnail`;
  }

  getClipDownloadUrl(clipId: number): string {
    return `${this.baseUrl}/api/clips/${clipId}/download`;
  }

  async getJobs(status?: string, limit = 50): Promise<Job[]> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (status && status !== "all") params.append("status", status);
    return this.fetch<Job[]>(`/api/jobs?${params.toString()}`);
  }

  async retryJob(jobId: number): Promise<Job> {
    return this.fetch<Job>(`/api/jobs/${jobId}/retry`, {
      method: "POST",
    });
  }

  async cancelJob(jobId: number): Promise<Job> {
    return this.fetch<Job>(`/api/jobs/${jobId}/cancel`, {
      method: "POST",
    });
  }

  async deleteJob(jobId: number): Promise<any> {
    return this.fetch(`/api/jobs/${jobId}`, {
      method: "DELETE",
    });
  }

  async getWatcherSettings(): Promise<WatcherSettings> {
    return this.fetch<WatcherSettings>("/api/settings/watcher");
  }

  async updateWatcherSettings(settings: Partial<WatcherSettings>): Promise<WatcherSettings> {
    return this.fetch<WatcherSettings>("/api/settings/watcher", {
      method: "POST",
      body: JSON.stringify(settings),
    });
  }

  async pauseWatcher(): Promise<any> {
    return this.fetch("/api/settings/watcher/pause", { method: "POST" });
  }

  async resumeWatcher(): Promise<any> {
    return this.fetch("/api/settings/watcher/resume", { method: "POST" });
  }

  async scanWatcherFolder(): Promise<{ status: string; new_recordings_found: number }> {
    return this.fetch("/api/settings/watcher/scan", { method: "POST" });
  }

  async getRecordingAnalysis(recordingId: number): Promise<RecordingAnalysis> {
    return this.fetch<RecordingAnalysis>(`/api/recordings/${recordingId}/analysis`);
  }

  async getRecordingTimeline(
    recordingId: number,
    page = 1,
    pageSize = 50,
    onlyPeaks = false,
    onlyCuts = false
  ): Promise<TimelineList> {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
      only_peaks: String(onlyPeaks),
      only_cuts: String(onlyCuts),
    });
    return this.fetch<TimelineList>(`/api/recordings/${recordingId}/timeline?${params.toString()}`);
  }

  async triggerAnalysis(recordingId: number, forceReanalyze = false): Promise<any> {
    return this.fetch(`/api/recordings/${recordingId}/analyze?force_reanalyze=${forceReanalyze}`, {
      method: "POST",
    });
  }

  // --- Phase 4: GTA 6 Specialized Gameplay Moment Detection ---
  async getEventTypes(): Promise<EventTypeInfo[]> {
    return this.fetch<EventTypeInfo[]>("/api/moments/event-types");
  }

  async getDetectedMoments(params?: {
    recording_id?: number;
    event_type?: string;
    status?: string;
    is_uncertain?: boolean;
    min_confidence?: number;
    page?: number;
    page_size?: number;
  }): Promise<DetectedMomentList> {
    const q = new URLSearchParams();
    if (params?.recording_id) q.append("recording_id", String(params.recording_id));
    if (params?.event_type && params.event_type !== "all") q.append("event_type", params.event_type);
    if (params?.status && params.status !== "all") q.append("status", params.status);
    if (params?.is_uncertain !== undefined) q.append("is_uncertain", String(params.is_uncertain));
    if (params?.min_confidence) q.append("min_confidence", String(params.min_confidence));
    if (params?.page) q.append("page", String(params.page));
    if (params?.page_size) q.append("page_size", String(params.page_size));
    return this.fetch<DetectedMomentList>(`/api/moments?${q.toString()}`);
  }

  async getDetectedMoment(id: number): Promise<DetectedMoment> {
    return this.fetch<DetectedMoment>(`/api/moments/${id}`);
  }

  async triggerMomentDetection(
    recordingId: number,
    options?: MomentDetectionOptions
  ): Promise<{ status: string; job_id: number; recording_id: number }> {
    return this.fetch(`/api/moments/recordings/${recordingId}/detect`, {
      method: "POST",
      body: JSON.stringify(options || {}),
    });
  }

  async updateDetectedMoment(
    id: number,
    update: Partial<DetectedMoment>
  ): Promise<DetectedMoment> {
    return this.fetch<DetectedMoment>(`/api/moments/${id}`, {
      method: "PATCH",
      body: JSON.stringify(update),
    });
  }

  async convertMomentToClip(id: number): Promise<{ status: string; moment_id: number; clip_id: number; title: string }> {
    return this.fetch(`/api/moments/${id}/convert-to-clip`, {
      method: "POST",
    });
  }

  async deleteDetectedMoment(id: number): Promise<{ status: string; moment_id: number }> {
    return this.fetch(`/api/moments/${id}`, {
      method: "DELETE",
    });
  }

  // --- Phase 5: AI Clip Ranking & Intelligent Selection ---
  async getClipCategories(): Promise<ClipCategoryInfo[]> {
    return this.fetch<ClipCategoryInfo[]>("/api/candidate-clips/categories");
  }

  async getTargetLengths(): Promise<number[]> {
    return this.fetch<number[]>("/api/candidate-clips/target-lengths");
  }

  async getCandidateClips(params?: {
    recording_id?: number;
    category?: string;
    target_length?: number;
    is_selected?: boolean;
    status?: string;
    min_score?: number;
    sort_by?: string;
    sort_order?: string;
    page?: number;
    page_size?: number;
  }): Promise<CandidateClipList> {
    const q = new URLSearchParams();
    if (params?.recording_id) q.append("recording_id", String(params.recording_id));
    if (params?.category && params.category !== "all") q.append("category", params.category);
    if (params?.target_length) q.append("target_length", String(params.target_length));
    if (params?.is_selected !== undefined) q.append("is_selected", String(params.is_selected));
    if (params?.status && params.status !== "all") q.append("status", params.status);
    if (params?.min_score) q.append("min_score", String(params.min_score));
    if (params?.sort_by) q.append("sort_by", params.sort_by);
    if (params?.sort_order) q.append("sort_order", params.sort_order);
    if (params?.page) q.append("page", String(params.page));
    if (params?.page_size) q.append("page_size", String(params.page_size));
    return this.fetch<CandidateClipList>(`/api/candidate-clips?${q.toString()}`);
  }

  async triggerClipRanking(
    recordingId: number,
    options?: ClipRankingTriggerOptions
  ): Promise<{ status: string; job_id: number; recording_id: number }> {
    return this.fetch(`/api/candidate-clips/recordings/${recordingId}/rank`, {
      method: "POST",
      body: JSON.stringify(options || {}),
    });
  }

  async batchSelectClips(
    recordingId: number,
    options: { select_top_n?: number; selected_ids?: number[]; deselect_all?: boolean }
  ): Promise<{ status: string; recording_id: number; selected_count: number; selected_ids: number[] }> {
    return this.fetch("/api/candidate-clips/select", {
      method: "POST",
      body: JSON.stringify({ recording_id: recordingId, ...options }),
    });
  }

  async updateCandidateClip(
    id: number,
    update: Partial<CandidateClip>
  ): Promise<CandidateClip> {
    return this.fetch<CandidateClip>(`/api/candidate-clips/${id}`, {
      method: "PATCH",
      body: JSON.stringify(update),
    });
  }

  async batchApproveCandidateClips(recordingId: number): Promise<{ status: string; approved_count: number }> {
    return this.fetch(`/api/candidate-clips/recordings/${recordingId}/batch-approve`, {
      method: "POST",
    });
  }

  async exportSelectedClips(recordingId: number): Promise<{ status: string; exported_count: number; recording_id: number }> {
    return this.fetch(`/api/candidate-clips/recordings/${recordingId}/export-selected`, {
      method: "POST",
    });
  }

  // Phase 7: GTA 6 Cinematic Shorts Editing
  async getCinematicPresets(): Promise<CinematicPresetInfo[]> {
    return this.fetch<CinematicPresetInfo[]>("/api/cinematic/presets");
  }

  async getMusicTracks(): Promise<AudioTrackInfo[]> {
    return this.fetch<AudioTrackInfo[]>("/api/cinematic/audio/music");
  }

  async getSfxTracks(): Promise<AudioTrackInfo[]> {
    return this.fetch<AudioTrackInfo[]>("/api/cinematic/audio/sfx");
  }

  async generateCinematicPreview(options: CinematicPreviewOptions): Promise<CinematicPreviewResult> {
    return this.fetch<CinematicPreviewResult>("/api/cinematic/preview", {
      method: "POST",
      body: JSON.stringify(options),
    });
  }

  async renderCinematicShort(options: CinematicEditOptions): Promise<CinematicRenderResult> {
    return this.fetch<CinematicRenderResult>("/api/cinematic/render", {
      method: "POST",
      body: JSON.stringify(options),
    });
  }

  // Phase 8: AI YouTube Shorts Metadata Generator
  async getClipMetadata(clipId: number, autoGenerate = true): Promise<ClipMetadata> {
    return this.fetch<ClipMetadata>(`/api/metadata/clips/${clipId}?auto_generate=${autoGenerate}`);
  }

  async generateClipMetadata(clipId: number, options?: ClipMetadataGenerateOptions): Promise<ClipMetadata> {
    return this.fetch<ClipMetadata>(`/api/metadata/clips/${clipId}/generate`, {
      method: "POST",
      body: JSON.stringify(options || {}),
    });
  }

  async updateClipMetadata(clipId: number, update: ClipMetadataUpdateOptions): Promise<ClipMetadata> {
    return this.fetch<ClipMetadata>(`/api/metadata/clips/${clipId}`, {
      method: "PUT",
      body: JSON.stringify(update),
    });
  }

  async batchGenerateMetadata(options: { clip_ids?: number[]; recording_id?: number; overwrite_existing?: boolean }): Promise<{
    status: string;
    total_requested: number;
    generated_count: number;
    items: Array<{ clip_id: number; title: string; hashtags: string }>;
  }> {
    return this.fetch("/api/metadata/batch-generate", {
      method: "POST",
      body: JSON.stringify(options),
    });
  }

  async getYouTubePublishPayload(clipId: number): Promise<YouTubePublishPayload> {
    return this.fetch<YouTubePublishPayload>(`/api/metadata/clips/${clipId}/export-payload`);
  }

  // Phase 9: Copyright and Monetization Risk Center
  async getOfficialPolicies(): Promise<OfficialPolicyInfo[]> {
    return this.fetch<OfficialPolicyInfo[]>("/api/copyright/policies");
  }

  async getCopyrightSummary(): Promise<CopyrightSummary> {
    return this.fetch<CopyrightSummary>("/api/copyright/summary");
  }

  async getRecordingPermission(recordingId: number): Promise<RecordingPermission> {
    return this.fetch<RecordingPermission>(`/api/copyright/recordings/${recordingId}`);
  }

  async updateRecordingPermission(recordingId: number, options: RecordingPermissionUpdateOptions): Promise<RecordingPermission> {
    return this.fetch<RecordingPermission>(`/api/copyright/recordings/${recordingId}`, {
      method: "PUT",
      body: JSON.stringify(options),
    });
  }

  async assessRecordingRisk(recordingId: number): Promise<RecordingPermission> {
    return this.fetch<RecordingPermission>(`/api/copyright/recordings/${recordingId}/assess`, {
      method: "POST",
    });
  }

  async submitManualReview(recordingId: number, options: ManualReviewOptions): Promise<RecordingPermission> {
    return this.fetch<RecordingPermission>(`/api/copyright/recordings/${recordingId}/manual-review`, {
      method: "POST",
      body: JSON.stringify(options),
    });
  }

  async checkClipExportStatus(clipId: number): Promise<{ clip_id: number; can_export: boolean; block_reason: string | null; legal_disclaimer: string }> {
    return this.fetch(`/api/copyright/clips/${clipId}/status`);
  }

  // Phase 10: Publishing Workspace & Production Export
  async getPublishingSummary(): Promise<PublishingWorkspaceSummary> {
    return this.fetch<PublishingWorkspaceSummary>("/api/publishing/summary");
  }

  async getPublishingItems(status?: string, recordingId?: number): Promise<PublishingItem[]> {
    const params = new URLSearchParams();
    if (status && status !== "all") params.append("status", status);
    if (recordingId) params.append("recording_id", String(recordingId));
    const qs = params.toString() ? `?${params.toString()}` : "";
    return this.fetch<PublishingItem[]>(`/api/publishing/items${qs}`);
  }

  async getPublishingItem(clipId: number): Promise<PublishingItem> {
    return this.fetch<PublishingItem>(`/api/publishing/items/${clipId}`);
  }

  async updatePublishingItem(clipId: number, options: PublishingItemUpdateOptions): Promise<PublishingItem> {
    return this.fetch<PublishingItem>(`/api/publishing/items/${clipId}`, {
      method: "PUT",
      body: JSON.stringify(options),
    });
  }

  async updatePublishingMetrics(clipId: number, options: PublishingMetricsUpdateOptions): Promise<PublishingItem> {
    return this.fetch<PublishingItem>(`/api/publishing/items/${clipId}/metrics`, {
      method: "PUT",
      body: JSON.stringify(options),
    });
  }

  async syncYouTubeAnalytics(clipId: number): Promise<PublishingItem> {
    return this.fetch<PublishingItem>(`/api/publishing/items/${clipId}/sync-analytics`, {
      method: "POST",
    });
  }

  async createExportPackageZip(options: ExportPackageOptions): Promise<ExportPackageResult> {
    return this.fetch<ExportPackageResult>("/api/exports/package-zip", {
      method: "POST",
      body: JSON.stringify(options),
    });
  }

  async exportBestMoments(recordingId: number): Promise<{ status: string; exported_count: number; moments: any[] }> {
    return this.fetch(`/api/exports/best-moments/${recordingId}`, {
      method: "POST",
    });
  }

  // --- YouTube Import & Auto Shorts ---
  async getYouTubeInfo(url: string): Promise<YouTubeVideoInfo> {
    return this.fetch<YouTubeVideoInfo>("/api/youtube/info", {
      method: "POST",
      body: JSON.stringify({ url }),
    });
  }

  async importYouTubeVideo(options: YouTubeImportOptions): Promise<YouTubeTask> {
    return this.fetch<YouTubeTask>("/api/youtube/import", {
      method: "POST",
      body: JSON.stringify(options),
    });
  }

  async getYouTubeTasks(limit = 20): Promise<YouTubeTask[]> {
    return this.fetch<YouTubeTask[]>(`/api/youtube/tasks?limit=${limit}`);
  }

  async getYouTubeTask(taskId: string): Promise<YouTubeTask> {
    return this.fetch<YouTubeTask>(`/api/youtube/tasks/${taskId}`);
  }

  async cancelYouTubeTask(taskId: string): Promise<{ status: string; task_id: string; message: string }> {
    return this.fetch(`/api/youtube/tasks/${taskId}/cancel`, {
      method: "POST",
    });
  }
}

export interface YouTubeVideoInfo {
  url: string;
  video_id: string;
  title: string;
  uploader: string;
  channel_url: string;
  duration_seconds: number;
  duration_formatted: string;
  thumbnail: string;
  view_count: number;
  description: string;
  resolution: string;
  fps: number;
}

export interface YouTubeTask {
  task_id: string;
  url: string;
  title: string;
  uploader: string;
  thumbnail: string;
  duration_seconds: number;
  status: "pending" | "downloading" | "processing" | "analyzing" | "completed" | "failed" | "cancelled";
  progress: number;
  downloaded_bytes: number;
  total_bytes: number;
  speed_str: string;
  eta_seconds: number;
  message: string;
  recording_id?: number | null;
  job_id?: number | null;
  error?: string | null;
  created_at?: string | null;
  completed_at?: string | null;
}

export interface YouTubeImportOptions {
  url: string;
  auto_generate_shorts?: boolean;
  notes?: string;
  has_permission?: boolean;
  creator_name?: string;
}

export const api = new ApiClient(API_URL);
