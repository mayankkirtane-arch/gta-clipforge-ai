"use client";

import React, { useEffect, useState } from "react";
import { Database, HardDrive, Server, Wifi } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { api, SystemStatus } from "@/lib/api";
import { cn } from "@/lib/utils";

function StatusDot({ status }: { status: string }) {
  const isGood = status === "healthy" || status === "ok" || status === "connected";
  return (
    <div
      className={cn(
        "w-2 h-2 rounded-full",
        isGood ? "bg-success animate-pulse-slow" : "bg-error"
      )}
    />
  );
}

function StatusRow({
  label,
  value,
  icon: Icon,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
}) {
  const isGood = value === "healthy" || value === "ok" || value === "connected";
  return (
    <div className="flex items-center justify-between py-2.5 border-b border-border/50 last:border-0">
      <div className="flex items-center gap-2">
        <Icon className="w-4 h-4 text-text-muted" />
        <span className="text-xs text-text-secondary">{label}</span>
      </div>
      <div className="flex items-center gap-2">
        <StatusDot status={value} />
        <span className={cn("text-xs font-semibold capitalize", isGood ? "text-success" : "text-error")}>
          {value}
        </span>
      </div>
    </div>
  );
}

export function SystemStatusPanel() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let mounted = true;
    const fetchStatus = async () => {
      try {
        const data = await api.getSystemStatus();
        if (mounted) setStatus(data);
      } catch {
        // Backend not running
      } finally {
        if (mounted) setLoading(false);
      }
    };

    fetchStatus();
    const interval = setInterval(fetchStatus, 15000);
    return () => {
      mounted = false;
      clearInterval(interval);
    };
  }, []);

  return (
    <Card>
      <CardHeader>
        <CardTitle>System & Storage Status</CardTitle>
        <Wifi className="w-4 h-4 text-text-muted" />
      </CardHeader>
      <CardContent>
        {loading ? (
          <div className="space-y-3">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="h-8 bg-surface-2 rounded animate-pulse" />
            ))}
          </div>
        ) : !status ? (
          <div className="text-center py-6">
            <Server className="w-8 h-8 text-error mx-auto mb-2" />
            <p className="text-sm text-error font-medium">Backend Offline</p>
            <p className="text-xs text-text-muted mt-1">Start Python server on port 8000</p>
          </div>
        ) : (
          <>
            <StatusRow label="Database" value={status.database} icon={Database} />
            <StatusRow label="Recordings Storage" value={status.storage_recordings} icon={HardDrive} />
            <StatusRow label="Exports Storage" value={status.storage_exports} icon={HardDrive} />
            <StatusRow label="Temp Storage" value={status.storage_temp} icon={HardDrive} />
            {status.free_space_gb !== null && status.total_space_gb !== null && (
              <div className="mt-4 pt-3 border-t border-border">
                <div className="flex justify-between text-xs text-text-secondary mb-1.5 font-medium">
                  <span>D: Drive Free Space</span>
                  <span className={status.free_space_gb < 5 ? "text-warning" : "text-success"}>
                    {status.free_space_gb} GB free
                  </span>
                </div>
                <div className="w-full bg-surface-3 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-gradient-to-r from-primary to-electric h-2 rounded-full transition-all duration-300"
                    style={{
                      width: `${Math.min(
                        100,
                        Math.max(
                          0,
                          ((status.total_space_gb - status.free_space_gb) / status.total_space_gb) * 100
                        )
                      )}%`,
                    }}
                  />
                </div>
                <div className="flex justify-between text-[11px] text-text-muted mt-1">
                  <span>Used: {(status.total_space_gb - status.free_space_gb).toFixed(1)} GB</span>
                  <span>Total: {status.total_space_gb} GB</span>
                </div>
              </div>
            )}
          </>
        )}
      </CardContent>
    </Card>
  );
}
