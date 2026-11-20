"use client";

import React, { useEffect, useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  HardDrive,
  Database,
  FolderOpen,
  AlertTriangle,
  CheckCircle2,
  Cpu,
  Pause,
  PlayCircle,
  RefreshCw,
  Save,
  Check,
} from "lucide-react";
import { api, WatcherSettings } from "@/lib/api";

export default function SettingsPage() {
  const [settings, setSettings] = useState<Record<string, string | number> | null>(null);
  const [diskSpace, setDiskSpace] = useState<{
    free_gb?: number;
    total_gb?: number;
    sufficient?: boolean;
    required_gb?: number;
  } | null>(null);
  const [watcherConfig, setWatcherConfig] = useState<WatcherSettings>({
    enable_auto_mode: true,
    monitoring_paused: false,
    auto_analyze: true,
    auto_generate_clips: true,
    require_approval: true,
    watch_folder_path: "D:\\GTA_CLIPFORGE_AI\\GTA6_RECORDINGS",
  });
  const [loading, setLoading] = useState(true);
  const [savingWatcher, setSavingWatcher] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState<string | null>(null);

  useEffect(() => {
    const apiUrl = api.baseUrl;
    Promise.all([
      fetch(`${apiUrl}/api/settings`).then((r) => (r.ok ? r.json() : null)),
      fetch(`${apiUrl}/api/settings/disk-space`).then((r) => (r.ok ? r.json() : null)),
      api.getWatcherSettings().catch(() => null),
    ])
      .then(([sData, dData, wData]) => {
        if (sData) setSettings(sData);
        if (dData) setDiskSpace(dData);
        if (wData) setWatcherConfig(wData);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const handleSaveWatcherSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    setSavingWatcher(true);
    setSavedSuccess(false);
    try {
      const updated = await api.updateWatcherSettings(watcherConfig);
      setWatcherConfig(updated);
      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 4000);
    } catch (err) {
      alert("Failed to update watcher settings");
    } finally {
      setSavingWatcher(false);
    }
  };

  const handleTogglePause = async () => {
    try {
      if (watcherConfig.monitoring_paused) {
        await api.resumeWatcher();
        setWatcherConfig((prev) => ({ ...prev, monitoring_paused: false }));
      } else {
        await api.pauseWatcher();
        setWatcherConfig((prev) => ({ ...prev, monitoring_paused: true }));
      }
    } catch (err) {
      alert("Failed to toggle watcher pause state");
    }
  };

  const handleScanNow = async () => {
    setScanning(true);
    setScanMessage(null);
    try {
      const res = await api.scanWatcherFolder();
      setScanMessage(`Scan complete: ${res.new_recordings_found} new recording(s) detected.`);
      setTimeout(() => setScanMessage(null), 5000);
    } catch (err: any) {
      setScanMessage("Scan failed or backend offline");
    } finally {
      setScanning(false);
    }
  };

  return (
    <div>
      <Header
        title="Settings"
        subtitle="Automatic processing controls, folder watcher, and storage preferences"
      />
      <div className="p-6 space-y-6 max-w-5xl">
        {/* AUTOMATIC PROCESSING & WATCHER SETTINGS */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center gap-2">
                <Cpu className="w-4 h-4 text-primary-light" />
                <CardTitle>Automatic Folder Watcher & Processing Engine</CardTitle>
              </div>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleTogglePause}
                  className="text-xs"
                >
                  {watcherConfig.monitoring_paused ? (
                    <>
                      <PlayCircle className="w-3.5 h-3.5 mr-1.5 text-success" /> Resume Monitoring
                    </>
                  ) : (
                    <>
                      <Pause className="w-3.5 h-3.5 mr-1.5 text-warning" /> Pause Monitoring
                    </>
                  )}
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleScanNow}
                  disabled={scanning}
                  className="text-xs"
                >
                  <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${scanning ? "animate-spin" : ""}`} />
                  Scan Now
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            {scanMessage && (
              <div className="mb-4 p-3 rounded-lg bg-primary/10 border border-primary/30 text-xs text-primary-light">
                {scanMessage}
              </div>
            )}

            <form onSubmit={handleSaveWatcherSettings} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold text-text-primary mb-1">
                  Watch Folder Path (GTA6_RECORDINGS)
                </label>
                <input
                  type="text"
                  value={watcherConfig.watch_folder_path}
                  onChange={(e) =>
                    setWatcherConfig((prev) => ({ ...prev, watch_folder_path: e.target.value }))
                  }
                  className="w-full px-3 py-2 text-xs font-mono rounded-lg bg-surface-2 border border-border text-text-primary focus:outline-none focus:border-primary"
                  placeholder="D:\GTA_CLIPFORGE_AI\GTA6_RECORDINGS"
                />
                <p className="text-[11px] text-text-muted mt-1">
                  Python Watchdog continuously monitors this folder. When new recordings appear (MP4, MKV, MOV, WebM), they are verified via FFprobe and ingested automatically.
                </p>
              </div>

              <div className="pt-2 divide-y divide-border/40">
                {/* Control 1: Enable Auto Mode */}
                <div className="py-3 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-text-primary block">
                      Enable Auto Mode
                    </span>
                    <span className="text-[11px] text-text-muted">
                      Master toggle for background automated ingestion and pipeline dispatch
                    </span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={watcherConfig.enable_auto_mode}
                      onChange={(e) =>
                        setWatcherConfig((prev) => ({ ...prev, enable_auto_mode: e.target.checked }))
                      }
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>

                {/* Control 2: Automatically Analyze New Recordings */}
                <div className="py-3 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-text-primary block">
                      Automatically Analyze New Recordings
                    </span>
                    <span className="text-[11px] text-text-muted">
                      Trigger Vision & Audio AI gameplay analysis immediately when a file finishes copying
                    </span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={watcherConfig.auto_analyze}
                      onChange={(e) =>
                        setWatcherConfig((prev) => ({ ...prev, auto_analyze: e.target.checked }))
                      }
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>

                {/* Control 3: Automatically Generate Candidate Clips */}
                <div className="py-3 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-text-primary block">
                      Automatically Generate Candidate Clips
                    </span>
                    <span className="text-[11px] text-text-muted">
                      Automatically generate 9:16 Shorts candidates after gameplay analysis finishes
                    </span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={watcherConfig.auto_generate_clips}
                      onChange={(e) =>
                        setWatcherConfig((prev) => ({
                          ...prev,
                          auto_generate_clips: e.target.checked,
                        }))
                      }
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>

                {/* Control 4: Require Approval Before Export */}
                <div className="py-3 flex items-center justify-between">
                  <div>
                    <span className="text-xs font-semibold text-text-primary block">
                      Require Approval Before Export
                    </span>
                    <span className="text-[11px] text-text-muted">
                      Require manual user confirmation in Copyright & Export Center before final Shorts rendering
                    </span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={watcherConfig.require_approval}
                      onChange={(e) =>
                        setWatcherConfig((prev) => ({ ...prev, require_approval: e.target.checked }))
                      }
                      className="sr-only peer"
                    />
                    <div className="w-9 h-5 bg-surface-3 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary"></div>
                  </label>
                </div>
              </div>

              <div className="pt-3 flex items-center justify-between">
                <div>
                  {savedSuccess && (
                    <span className="text-xs text-success flex items-center gap-1.5 font-medium">
                      <Check className="w-4 h-4" /> Watcher settings saved successfully!
                    </span>
                  )}
                </div>
                <Button type="submit" disabled={savingWatcher} size="sm">
                  <Save className="w-3.5 h-3.5 mr-1.5" />
                  {savingWatcher ? "Saving..." : "Save Settings"}
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* STORAGE CONFIGURATION */}
        <Card>
          <CardHeader>
            <CardTitle>Storage Configuration (D: Drive Enforced)</CardTitle>
            <HardDrive className="w-4 h-4 text-text-muted" />
          </CardHeader>
          <CardContent>
            {loading ? (
              <div className="space-y-3">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="h-10 bg-surface-2 rounded animate-pulse" />
                ))}
              </div>
            ) : settings ? (
              <div className="space-y-2.5">
                {[
                  { key: "watch_dir", label: "Watch Folder (GTA6_RECORDINGS)", desc: "Automatic watchdog drop folder" },
                  { key: "recordings_dir", label: "Recordings Directory", desc: "Raw GTA gameplay files database" },
                  { key: "models_dir", label: "AI Models Directory", desc: "Vision & audio AI models" },
                  { key: "temp_dir", label: "Temporary Processing Directory", desc: "Auto-cleaned working files" },
                  { key: "exports_dir", label: "Exports Directory", desc: "Final 9:16 Shorts files" },
                  { key: "logs_dir", label: "Logs Directory", desc: "Application log files" },
                ].map((item) => (
                  <div
                    key={item.key}
                    className="flex flex-col sm:flex-row sm:items-center justify-between p-3.5 rounded-lg bg-surface-2 border border-border/40 gap-2"
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <FolderOpen className="w-4 h-4 text-primary-light flex-shrink-0" />
                        <span className="text-xs font-semibold text-text-primary">{item.label}</span>
                      </div>
                      <p className="text-[11px] text-text-muted mt-0.5 ml-6">{item.desc}</p>
                    </div>
                    <code className="text-xs text-electric font-mono bg-surface-3 px-2.5 py-1 rounded border border-border/60 self-start sm:self-auto">
                      {(settings[item.key] as string) || "D:\\GTA_CLIPFORGE_AI\\GTA6_RECORDINGS"}
                    </code>
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-text-muted">Connect to backend on port 8000 to view active settings.</p>
            )}
          </CardContent>
        </Card>

        {diskSpace && (
          <Card>
            <CardHeader>
              <CardTitle>D: Drive Disk Space Pre-flight Check</CardTitle>
              <Database className="w-4 h-4 text-text-muted" />
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between items-center text-sm">
                  <span className="text-text-secondary">Free Disk Space</span>
                  <span className={`font-semibold ${diskSpace.sufficient ? "text-success" : "text-error"}`}>
                    {diskSpace.free_gb} GB
                  </span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-text-secondary">Total Drive Capacity</span>
                  <span className="text-text-primary font-medium">{diskSpace.total_gb} GB</span>
                </div>
                <div className="flex justify-between items-center text-sm">
                  <span className="text-text-secondary">Minimum Required Threshold</span>
                  <span className="text-text-muted font-mono">{diskSpace.required_gb} GB</span>
                </div>

                {diskSpace.sufficient ? (
                  <div className="mt-3 p-3.5 rounded-lg bg-green-950/20 border border-green-800/30 flex items-center gap-2.5 text-xs text-success">
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                    <span>Disk space is sufficient for video importing and AI analysis.</span>
                  </div>
                ) : (
                  <div className="mt-3 p-3.5 rounded-lg bg-red-950/30 border border-red-800/40 flex items-center gap-2.5 text-xs text-error">
                    <AlertTriangle className="w-4 h-4 flex-shrink-0" />
                    <span>Warning: Less than {diskSpace.required_gb} GB free on D: drive! Free up space before importing recordings.</span>
                  </div>
                )}
              </div>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
