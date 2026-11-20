"use client";

import React, { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Brain,
  Film,
  Sparkles,
  Zap,
  Volume2,
  Cpu,
  Layers,
  Flame,
  CheckCircle2,
  RefreshCw,
  Clock,
  HardDrive,
  ArrowRight,
  Activity,
  Play,
} from "lucide-react";
import { api, Recording } from "@/lib/api";
import { formatBytes, formatDuration, formatRelativeTime } from "@/lib/utils";

const statusVariants: Record<string, "default" | "warning" | "success" | "error"> = {
  pending: "default",
  analyzing: "warning",
  analyzed: "success",
  failed: "error",
};

export default function AIAnalysisPage() {
  const [recordings, setRecordings] = useState<Recording[]>([]);
  const [loading, setLoading] = useState(true);

  const loadRecordings = useCallback(async () => {
    try {
      const res = await api.getRecordings(1, 50);
      setRecordings(res.items);
    } catch {}
    finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadRecordings();
    const interval = setInterval(loadRecordings, 5000);
    return () => clearInterval(interval);
  }, [loadRecordings]);

  const totalAnalyzed = recordings.filter((r) => r.status === "analyzed").length;
  const totalProcessing = recordings.filter((r) => r.status === "analyzing").length;
  const totalPending = recordings.filter((r) => r.status === "pending").length;

  return (
    <div>
      <Header
        title="AI Analysis"
        subtitle="Professional video processing engine: PySceneDetect cuts, audio peaks, waveforms & 8h chunk processing"
      />

      <div className="p-6 space-y-6 max-w-7xl">
        {/* Engine Features Grid */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card className="bg-surface-2/60">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-primary/20 text-primary-light">
                <Brain className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xs text-text-muted block">PySceneDetect</span>
                <span className="text-sm font-bold text-text-primary">Cut & Scene Tracking</span>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-surface-2/60">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-warning/20 text-warning">
                <Volume2 className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xs text-text-muted block">Audio Analysis</span>
                <span className="text-sm font-bold text-text-primary">Peaks & Waveforms</span>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-surface-2/60">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-electric/20 text-electric">
                <Cpu className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xs text-text-muted block">Hardware Accel</span>
                <span className="text-sm font-bold text-text-primary">NVENC GPU + CPU Fallback</span>
              </div>
            </CardContent>
          </Card>

          <Card className="bg-surface-2/60">
            <CardContent className="p-4 flex items-center gap-3">
              <div className="p-2.5 rounded-lg bg-green-500/20 text-success">
                <Layers className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xs text-text-muted block">8-Hour Engine</span>
                <span className="text-sm font-bold text-text-primary">Chunk-based Recovery</span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Recordings AI Analysis Overview */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-primary-light" />
                <CardTitle>Gameplay Recordings Library ({recordings.length})</CardTitle>
              </div>
              <div className="flex items-center gap-2 text-xs font-mono">
                <span className="text-success font-semibold">{totalAnalyzed} Analyzed</span>
                <span className="text-text-muted">/</span>
                <span className="text-warning font-semibold">{totalProcessing} Analyzing</span>
                <span className="text-text-muted">/</span>
                <span className="text-text-muted font-semibold">{totalPending} Pending</span>
              </div>
            </div>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="p-6 space-y-3">
                {[...Array(3)].map((_, i) => (
                  <div key={i} className="h-16 bg-surface-2 rounded-lg animate-pulse" />
                ))}
              </div>
            ) : recordings.length === 0 ? (
              <div className="text-center py-16 px-4">
                <Film className="w-12 h-12 text-text-muted mx-auto mb-3 opacity-25" />
                <h4 className="text-sm font-semibold text-text-secondary">No recordings available</h4>
                <p className="text-xs text-text-muted mt-1 max-w-sm mx-auto">
                  Import a GTA 6 gameplay recording in the Recordings tab to run scene detection and audio analysis.
                </p>
                <Link href="/recordings" className="mt-4 inline-block">
                  <Button size="sm">Go to Recordings</Button>
                </Link>
              </div>
            ) : (
              <div className="divide-y divide-border/40">
                {recordings.map((rec) => (
                  <div
                    key={rec.id}
                    className="p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 hover:bg-surface-2/40 transition-colors"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="p-2.5 rounded-lg bg-surface-3 flex-shrink-0">
                        <Film className="w-5 h-5 text-primary-light" />
                      </div>
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <h4 className="text-sm font-semibold text-text-primary truncate" title={rec.original_filename}>
                            {rec.original_filename}
                          </h4>
                          <Badge variant={statusVariants[rec.status] || "default"}>
                            {rec.status}
                          </Badge>
                        </div>
                        <div className="flex items-center gap-3 mt-1 text-xs text-text-muted">
                          {rec.duration_seconds && (
                            <span className="flex items-center gap-1 font-mono">
                              <Clock className="w-3 h-3" /> {formatDuration(rec.duration_seconds)}
                            </span>
                          )}
                          {rec.resolution && (
                            <span className="font-mono">{rec.resolution}</span>
                          )}
                          {rec.file_size_bytes && (
                            <span className="font-mono">{formatBytes(rec.file_size_bytes)}</span>
                          )}
                          {rec.created_at && (
                            <span>{formatRelativeTime(rec.created_at)}</span>
                          )}
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 self-stretch sm:self-auto justify-end">
                      <Link href={`/detected-moments`}>
                        <Button variant="outline" size="sm" className="w-full sm:w-auto border-primary/30 text-primary-light hover:bg-primary/10">
                          <Zap className="w-3.5 h-3.5 mr-1.5" />
                          Moments
                        </Button>
                      </Link>
                      <Link href={`/recordings/${rec.id}`}>
                        <Button variant="primary" size="sm" className="w-full sm:w-auto">
                          <Sparkles className="w-3.5 h-3.5 mr-1.5" />
                          Open Timeline
                          <ArrowRight className="w-3.5 h-3.5 ml-1.5" />
                        </Button>
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
