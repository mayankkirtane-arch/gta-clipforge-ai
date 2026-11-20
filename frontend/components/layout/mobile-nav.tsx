"use client";

import React, { useState, useEffect } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Film,
  Youtube,
  Video,
  Download,
  Share2,
  Smartphone,
  X,
} from "lucide-react";
import { cn } from "@/lib/utils";

const mobileTabs = [
  { href: "/", label: "Home", icon: LayoutDashboard },
  { href: "/recordings", label: "Recordings", icon: Film },
  { href: "/recordings?action=youtube", label: "YouTube", icon: Youtube, highlight: true },
  { href: "/generated-shorts", label: "Shorts", icon: Video },
  { href: "/export-center", label: "Publish", icon: Download },
];

export function MobileNav() {
  const pathname = usePathname();
  const [deferredPrompt, setDeferredPrompt] = useState<any>(null);
  const [showInstallBanner, setShowInstallBanner] = useState(false);

  useEffect(() => {
    const handler = (e: any) => {
      e.preventDefault();
      setDeferredPrompt(e);
      setShowInstallBanner(true);
    };
    window.addEventListener("beforeinstallprompt", handler);
    return () => window.removeEventListener("beforeinstallprompt", handler);
  }, []);

  const handleInstallClick = async () => {
    if (!deferredPrompt) return;
    deferredPrompt.prompt();
    const { outcome } = await deferredPrompt.userChoice;
    if (outcome === "accepted") {
      setShowInstallBanner(false);
    }
    setDeferredPrompt(null);
  };

  return (
    <>
      {/* Optional Install as Mobile App Banner */}
      {showInstallBanner && (
        <div className="md:hidden fixed top-2 left-2 right-2 z-50 bg-gradient-to-r from-red-950/90 to-surface border border-red-500/50 rounded-xl p-3 shadow-2xl backdrop-blur-md flex items-center justify-between animate-fade-in">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-red-600 text-white">
              <Smartphone className="w-4 h-4" />
            </div>
            <div>
              <p className="text-xs font-bold text-white">Install on Samsung Device</p>
              <p className="text-[10px] text-text-muted">Fullscreen app with zero browser bars</p>
            </div>
          </div>
          <div className="flex items-center gap-1.5">
            <button
              onClick={handleInstallClick}
              className="px-2.5 py-1 text-[11px] font-bold bg-red-600 hover:bg-red-500 text-white rounded-lg transition-colors shadow"
            >
              Install
            </button>
            <button
              onClick={() => setShowInstallBanner(false)}
              className="p-1 text-text-muted hover:text-white"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      )}

      {/* Bottom Sticky Mobile Navigation Bar */}
      <nav className="md:hidden fixed bottom-0 left-0 right-0 z-50 bg-surface/95 backdrop-blur-lg border-t border-border px-2 py-1.5 shadow-2xl safe-area-pb">
        <div className="flex items-center justify-around max-w-lg mx-auto">
          {mobileTabs.map((tab) => {
            const Icon = tab.icon;
            const isActive =
              tab.href === "/"
                ? pathname === "/"
                : pathname.startsWith(tab.href.split("?")[0]);

            return (
              <Link
                key={tab.label}
                href={tab.href}
                className={cn(
                  "flex flex-col items-center justify-center py-1 px-2.5 rounded-xl transition-all duration-150 touch-manipulation min-w-[56px]",
                  isActive && !tab.highlight
                    ? "text-primary-light font-bold"
                    : tab.highlight
                    ? "text-red-400 font-bold"
                    : "text-text-muted hover:text-text-primary"
                )}
              >
                <div
                  className={cn(
                    "p-1.5 rounded-xl transition-all",
                    tab.highlight
                      ? "bg-red-600/20 text-red-400 shadow-sm shadow-red-500/20"
                      : isActive
                      ? "bg-primary/15 text-primary-light"
                      : "text-text-muted"
                  )}
                >
                  <Icon className="w-5 h-5" />
                </div>
                <span className="text-[10px] tracking-tight mt-0.5 leading-none">
                  {tab.label}
                </span>
              </Link>
            );
          })}
        </div>
      </nav>
    </>
  );
}
