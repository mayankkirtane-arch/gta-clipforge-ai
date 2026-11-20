import React from "react";
import { Header } from "@/components/layout/header";
import { StatsGrid } from "@/components/dashboard/stats-grid";
import { SystemStatusPanel } from "@/components/dashboard/system-status";
import { QuickActions } from "@/components/dashboard/quick-actions";
import { RecentRecordings } from "@/components/dashboard/recent-recordings";
import { ProcessingQueue } from "@/components/dashboard/processing-queue";

export default function DashboardPage() {
  return (
    <div className="animate-fade-in min-h-screen pb-12">
      <Header
        title="Dashboard"
        subtitle="GTA ClipForge AI — Phase 6 Automatic YouTube Shorts Generator"
      />
      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        <StatsGrid />
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <RecentRecordings />
            <ProcessingQueue />
          </div>
          <div className="space-y-6">
            <QuickActions />
            <SystemStatusPanel />
          </div>
        </div>
      </div>
    </div>
  );
}
