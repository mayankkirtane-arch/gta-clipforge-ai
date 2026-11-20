"use client";

import React, { useEffect, useState } from "react";
import { Film, Video, Loader, CheckCircle } from "lucide-react";
import { StatCard } from "@/components/ui/stat-card";
import { api, DashboardStats } from "@/lib/api";

export function StatsGrid() {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let mounted = true;
    const fetchStats = async () => {
      try {
        const data = await api.getDashboardStats();
        if (mounted) {
          setStats(data);
          setError(null);
        }
      } catch {
        if (mounted) {
          setError("Could not connect to backend. Is the server running?");
        }
      } finally {
        if (mounted) {
          setLoading(false);
        }
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 10000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  if (error) {
    return (
      <div className="rounded-xl border border-red-800/40 bg-red-950/20 p-4">
        <p className="text-sm text-error font-medium">{error}</p>
        <p className="text-xs text-text-muted mt-1">Make sure the Python backend is running on port 8000.</p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
      <StatCard
        title="Total Recordings"
        value={loading ? "—" : (stats?.total_recordings ?? 0)}
        icon={Film}
        color="purple"
        description="Imported gameplay files"
        loading={loading}
      />
      <StatCard
        title="Clips Generated"
        value={loading ? "—" : (stats?.total_clips_generated ?? 0)}
        icon={Video}
        color="blue"
        description="AI-generated short clips"
        loading={loading}
      />
      <StatCard
        title="Processing Jobs"
        value={loading ? "—" : (stats?.processing_jobs ?? 0)}
        icon={Loader}
        color="yellow"
        description="Active in queue"
        loading={loading}
      />
      <StatCard
        title="Approved Clips"
        value={loading ? "—" : (stats?.approved_clips ?? 0)}
        icon={CheckCircle}
        color="green"
        description="Ready for export"
        loading={loading}
      />
    </div>
  );
}
