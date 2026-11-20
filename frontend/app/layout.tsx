import React from "react";
import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Sidebar } from "@/components/layout/sidebar";
import { MobileNav } from "@/components/layout/mobile-nav";

export const metadata: Metadata = {
  title: "GTA ClipForge AI",
  description: "Local AI-powered GTA gameplay to YouTube Shorts converter",
  manifest: "/manifest.json",
  appleWebApp: {
    capable: true,
    statusBarStyle: "black-translucent",
    title: "ClipForge",
  },
};

export const viewport: Viewport = {
  themeColor: "#0a0a0f",
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  userScalable: false,
  viewportFit: "cover",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-background text-text-primary antialiased selection:bg-red-500/30 selection:text-red-200">
        <div className="flex h-screen overflow-hidden">
          <Sidebar />
          <main className="flex-1 ml-0 md:ml-64 pb-20 md:pb-0 overflow-y-auto">
            {children}
          </main>
          <MobileNav />
        </div>
      </body>
    </html>
  );
}
