"use client";

import React from "react";
import { Bell, Search } from "lucide-react";

interface HeaderProps {
  title: string;
  subtitle?: string;
}

export function Header({ title, subtitle }: HeaderProps) {
  return (
    <header className="h-16 border-b border-border bg-surface/80 backdrop-blur-md flex items-center justify-between px-6 sticky top-0 z-30">
      <div>
        <h2 className="text-lg font-bold text-white tracking-tight">{title}</h2>
        {subtitle && <p className="text-xs text-text-muted mt-0.5">{subtitle}</p>}
      </div>
      <div className="flex items-center gap-3">
        <button
          aria-label="Search"
          className="p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-2 transition-colors border border-transparent hover:border-border"
        >
          <Search className="w-4 h-4" />
        </button>
        <button
          aria-label="Notifications"
          className="p-2 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-2 transition-colors relative border border-transparent hover:border-border"
        >
          <Bell className="w-4 h-4" />
          <span className="w-2 h-2 rounded-full bg-electric absolute top-1.5 right-1.5" />
        </button>
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-primary to-electric flex items-center justify-center font-bold text-xs text-white shadow-md shadow-primary/20">
          G
        </div>
      </div>
    </header>
  );
}
