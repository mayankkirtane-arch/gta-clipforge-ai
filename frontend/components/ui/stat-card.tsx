import React from "react";
import { cn } from "@/lib/utils";
import { LucideIcon } from "lucide-react";

interface StatCardProps {
  title: string;
  value: number | string;
  icon: LucideIcon;
  color?: "purple" | "blue" | "green" | "yellow";
  description?: string;
  loading?: boolean;
}

const colorConfig = {
  purple: {
    bg: "bg-purple-950/40",
    border: "border-purple-800/40",
    icon: "text-primary-light",
    iconBg: "bg-purple-900/40",
    value: "text-primary-light",
  },
  blue: {
    bg: "bg-blue-950/40",
    border: "border-blue-800/40",
    icon: "text-electric",
    iconBg: "bg-blue-900/40",
    value: "text-electric",
  },
  green: {
    bg: "bg-green-950/40",
    border: "border-green-800/40",
    icon: "text-success",
    iconBg: "bg-green-900/40",
    value: "text-success",
  },
  yellow: {
    bg: "bg-yellow-950/40",
    border: "border-yellow-800/40",
    icon: "text-warning",
    iconBg: "bg-yellow-900/40",
    value: "text-warning",
  },
};

export function StatCard({ title, value, icon: Icon, color = "purple", description, loading }: StatCardProps) {
  const c = colorConfig[color];
  return (
    <div
      className={cn(
        "rounded-xl border p-5 transition-all duration-200 hover:scale-[1.02]",
        c.bg,
        c.border
      )}
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wider text-text-muted mb-2">{title}</p>
          {loading ? (
            <div className="h-8 w-16 bg-surface-3 rounded animate-pulse" />
          ) : (
            <p className={cn("text-3xl font-bold", c.value)}>{value}</p>
          )}
          {description && <p className="text-xs text-text-muted mt-1">{description}</p>}
        </div>
        <div className={cn("p-3 rounded-lg", c.iconBg)}>
          <Icon className={cn("w-5 h-5", c.icon)} />
        </div>
      </div>
    </div>
  );
}
