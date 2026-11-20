import React from "react";
import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "error" | "info" | "purple";
  className?: string;
}

const variantClasses = {
  default: "bg-surface-3 text-text-secondary border-border",
  success: "bg-green-950/80 text-success border-green-800/40",
  warning: "bg-yellow-950/80 text-warning border-yellow-800/40",
  error: "bg-red-950/80 text-error border-red-800/40",
  info: "bg-blue-950/80 text-electric border-blue-800/40",
  purple: "bg-purple-950/80 text-primary-light border-purple-800/40",
};

export function Badge({ children, variant = "default", className }: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border",
        variantClasses[variant],
        className
      )}
    >
      {children}
    </span>
  );
}
