"use client";

import React, { useEffect, useState, useCallback } from "react";
import { Loader, CheckCircle, XCircle, Clock, Ban, RotateCcw, AlertCircle } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { api, Job } from "@/lib/api";

function JobStatusIcon({ status }: { status: Job["status"] }) {
  if (status === "running" || status === "processing") {
    return <Loader className="w-4 h-4 text-warning animate-spin flex-shrink-0" />;
  }
  if (status === "completed") {
    return <CheckCircle className="w-4 h-4 text-success flex-shrink-0" />;
  }
  if (status === "failed") {
    return <XCircle className="w-4 h-4 text-error flex-shrink-0" />;
  }
  if (status === "cancelled") {
    return <Ban className="w-4 h-4 text-text-muted flex-shrink-0" />;
  }
  return <Clock className="w-4 h-4 text-text-muted flex-shrink-0" />;
}

export function ProcessingQueue() {
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<number | null>(null);

  const fetchJobs = useCallback(async () => {
    try {
      const data = await api.getJobs("all", 10);
      setJobs(data);
    } catch {
      // silent
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchJobs();
    const interval = setInterval(fetchJobs, 3000);
    return () => clearInterval(interval);
  }, [fetchJobs]);

  const handleRetry = async (jobId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setActionLoading(jobId);
    try {
      await api.retryJob(jobId);
      await fetchJobs();
    } catch {}
    finally {
      setActionLoading(null);
    }
  };

  const handleCancel = async (jobId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    setActionLoading(jobId);
    try {
      await api.cancelJob(jobId);
      await fetchJobs();
    } catch {}
    finally {
      setActionLoading(null);
    }
  };

  const jobTypeLabel: Record<string, string> = {
    analysis: "AI Analysis",
    clip_generation: "Clip Generation",
    export: "Export",
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>Processing Queue</CardTitle>
        <Loader className="w-4 h-4 text-text-muted" />
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-2">
            {[...Array(2)].map((_, i) => (
              <div key={i} className="h-12 bg-surface-2 rounded animate-pulse" />
            ))}
          </div>
        ) : jobs.length === 0 ? (
          <div className="text-center py-10 border border-dashed border-border/60 rounded-lg">
            <CheckCircle className="w-10 h-10 text-text-muted mx-auto mb-3 opacity-30" />
            <p className="text-sm font-medium text-text-secondary">Queue is empty</p>
            <p className="text-xs text-text-muted mt-1">No active processing jobs</p>
          </div>
        ) : (
          <div className="space-y-2 max-h-[360px] overflow-y-auto pr-1">
            {jobs.map((job) => (
              <div key={job.id} className="p-3 rounded-lg bg-surface-2 border border-border/40">
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-2 min-w-0">
                    <JobStatusIcon status={job.status} />
                    <div className="min-w-0">
                      <span className="text-xs font-semibold text-text-primary block truncate">
                        {jobTypeLabel[job.job_type] || job.job_type}
                        {job.recording_filename && (
                          <span className="text-text-muted font-normal ml-1.5">
                            ({job.recording_filename})
                          </span>
                        )}
                      </span>
                    </div>
                  </div>

                  <div className="flex items-center gap-2 flex-shrink-0">
                    <span className="text-xs text-text-muted font-mono">{job.progress}%</span>
                    {job.status === "failed" && (
                      <button
                        onClick={(e) => handleRetry(job.id, e)}
                        disabled={actionLoading === job.id}
                        className="text-[11px] px-2 py-0.5 rounded bg-surface-3 hover:bg-primary/20 text-primary-light flex items-center gap-1"
                        title="Retry Failed Job"
                      >
                        <RotateCcw className="w-3 h-3" /> Retry
                      </button>
                    )}
                    {(job.status === "running" || job.status === "processing" || job.status === "pending" || job.status === "queued") && (
                      <button
                        onClick={(e) => handleCancel(job.id, e)}
                        disabled={actionLoading === job.id}
                        className="text-[11px] px-2 py-0.5 rounded bg-surface-3 hover:bg-error/20 text-text-muted hover:text-error"
                        title="Cancel Job"
                      >
                        Cancel
                      </button>
                    )}
                  </div>
                </div>

                {(job.status === "running" || job.status === "processing") && (
                  <div className="w-full bg-surface-3 rounded-full h-1 my-1.5 overflow-hidden">
                    <div
                      className="bg-gradient-to-r from-primary to-electric h-1 rounded-full transition-all duration-300"
                      style={{ width: `${job.progress}%` }}
                    />
                  </div>
                )}

                {job.message && (
                  <p className="text-[11px] text-text-muted truncate mt-1">{job.message}</p>
                )}

                {job.error && (
                  <div className="mt-1 flex items-center gap-1.5 text-[11px] text-error bg-error/10 p-1.5 rounded">
                    <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                    <span className="truncate">{job.error}</span>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
