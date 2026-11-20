"use client";

import React from "react";
import { useRouter } from "next/navigation";
import { Upload, Brain, Video, FolderOpen, Youtube } from "lucide-react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";

export function QuickActions() {
  const router = useRouter();

  const actions = [
    {
      label: "YouTube to Shorts",
      icon: Youtube,
      description: "Paste link & auto-generate",
      onClick: () => router.push("/recordings?action=youtube"),
      highlight: true,
    },
    {
      label: "Import Recording",
      icon: Upload,
      description: "Add a GTA gameplay file",
      onClick: () => router.push("/recordings"),
    },
    {
      label: "Analyze Gameplay",
      icon: Brain,
      description: "AI moment detection",
      onClick: () => router.push("/recordings"),
    },
    {
      label: "Generate Shorts",
      icon: Video,
      description: "Create YouTube Shorts (9:16)",
      onClick: () => router.push("/generated-shorts"),
    },
    {
      label: "Open Exports",
      icon: FolderOpen,
      description: "Browse generated clips",
      onClick: () => router.push("/export-center"),
    },
  ];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Quick Actions</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 gap-3">
          {actions.map((action) => {
            const Icon = action.icon;
            return (
              <button
                key={action.label}
                onClick={action.onClick}
                className={`flex flex-col items-start gap-1.5 p-3 rounded-lg border transition-all duration-150 text-left group ${
                  action.highlight
                    ? "border-red-500/40 bg-red-950/20 hover:border-red-500 hover:bg-red-900/30"
                    : "border-border bg-surface-2 hover:border-primary/50 hover:bg-surface-3"
                }`}
              >
                <div className={`p-2 rounded-lg transition-colors ${
                  action.highlight
                    ? "bg-red-500/20 group-hover:bg-red-500/30 text-red-400"
                    : "bg-surface-3 group-hover:bg-primary/20 text-primary-light"
                }`}>
                  <Icon className="w-4 h-4" />
                </div>
                <span className="text-xs font-semibold text-text-primary mt-1">{action.label}</span>
                <span className="text-[11px] text-text-muted leading-tight">{action.description}</span>
              </button>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}
