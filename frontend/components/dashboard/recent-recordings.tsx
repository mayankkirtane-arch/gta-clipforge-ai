"use client";

import React, { useEffect, useState } from "react";
import { Film, Clock, HardDrive } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { api, Recording } from "@/lib/api";
import { formatBytes, formatDuration, formatRelativeTime } from "@/lib/utils";

const statusVariant: Record<string, "default" | "warning" | "success" | "error"> = {
  pending: "default",
  analyzing: "warning",
  analyzed: "success",
  failed: "error",
};

export function RecentRecordings() {
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const fetchRecordings = async () => {
      try {
        const data = await api.getRecordings(1, 5);
        if (mounted) setRecordings(data.items);
      } catch {
        // silent on offline backend
      } finally {
        if (mounted) setLoading(false);
      }
    };
    fetchRecordings();
    return () => {
      mounted = false;
    };
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>Recent Recordings</CardTitle>
        <Film className="w-4 h-4 text-text-muted" />
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            {[...Array(3)].map((_, i) => (
              <div key={i} className="h-14 bg-surface-2 rounded-lg animate-pulse" />
            ))}
          </div>
        ) : recordings.length === 0 ? (
          <div className="text-center py-10 border border-dashed border-border/60 rounded-lg">
            <Film className="w-10 h-10 text-text-muted mx-auto mb-3 opacity-30" />
            <p className="text-sm font-medium text-text-secondary">No recordings yet</p>
            <p className="text-xs text-text-muted mt-1">Import a GTA gameplay file to get started</p>
          </div>
        ) : (
          <div className="space-y-2">
            {recordings.map((rec) => (
              <div
                key={rec.id}
                className="flex items-center gap-3 p-3 rounded-lg bg-surface-2 hover:bg-surface-3 transition-colors border border-border/40"
              >
                <div className="p-2 rounded-lg bg-surface-3">
                  <Film className="w-4 h-4 text-primary-light" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-text-primary truncate">{rec.original_filename}</p>
                  <div className="flex items-center gap-3 mt-0.5">
                    {rec.duration_seconds && (
                      <span className="text-xs text-text-muted flex items-center gap-1">
                        <Clock className="w-3 h-3" /> {formatDuration(rec.duration_seconds)}
                      </span>
                    )}
                    {rec.file_size_bytes && (
                      <span className="text-xs text-text-muted flex items-center gap-1">
                        <HardDrive className="w-3 h-3" /> {formatBytes(rec.file_size_bytes)}
                      </span>
                    )}
                    {rec.created_at && (
                      <span className="text-xs text-text-muted">{formatRelativeTime(rec.created_at)}</span>
                    )}
                  </div>
                </div>
                <Badge variant={statusVariant[rec.status] || "default"}>{rec.status}</Badge>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
