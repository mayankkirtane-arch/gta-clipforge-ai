"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Film,
  Brain,
  Zap,
  Video,
  Scissors,
  Shield,
  Download,
  Settings,
  Swords,
  ChevronRight,
  Award,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/recordings", label: "Recordings", icon: Film },
  { href: "/ai-analysis", label: "AI Analysis", icon: Brain },
  { href: "/detected-moments", label: "Detected Moments", icon: Zap },
  { href: "/candidate-clips", label: "Candidate Clips", icon: Award },
  { href: "/generated-shorts", label: "Generated Shorts", icon: Video },
  { href: "/clip-editor", label: "Clip Editor", icon: Scissors },
  { href: "/copyright-center", label: "Copyright Center", icon: Shield },
  { href: "/export-center", label: "Export & Publishing", icon: Download },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-64 h-screen bg-surface border-r border-border hidden md:flex flex-col fixed left-0 top-0 z-40">
      {/* Logo */}
      <div className="p-5 border-b border-border">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-primary to-electric flex items-center justify-center shadow-lg shadow-primary/20">
            <Swords className="w-5 h-5 text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-white tracking-wide">GTA CLIPFORGE</h1>
            <p className="text-[10px] text-primary-light font-semibold tracking-widest uppercase">AI Engine</p>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 p-3 overflow-y-auto space-y-1">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-all duration-150 group",
                isActive
                  ? "bg-primary/15 text-white border border-primary/30 font-medium"
                  : "text-text-muted hover:text-text-primary hover:bg-surface-2"
              )}
            >
              <Icon
                className={cn(
                  "w-4 h-4 flex-shrink-0 transition-colors",
                  isActive ? "text-primary-light" : "text-text-muted group-hover:text-text-secondary"
                )}
              />
              <span>{item.label}</span>
              {isActive && <ChevronRight className="w-3.5 h-3.5 ml-auto text-primary-light" />}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="p-4 border-t border-border bg-surface-2/40">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-success animate-pulse-slow" />
          <span className="text-xs text-text-muted">Phase 10 — Production Ready</span>
        </div>
      </div>
    </aside>
  );
}
