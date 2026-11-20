import React from "react";
import { cn } from "@/lib/utils";
import { Loader2 } from "lucide-react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "electric" | "outline" | "default";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
  icon?: React.ReactNode;
}

const variantClasses = {
  primary: "bg-primary hover:bg-primary-hover text-white border border-primary/20",
  default: "bg-primary hover:bg-primary-hover text-white border border-primary/20",
  electric: "bg-electric hover:bg-electric-hover text-white border border-electric/20",
  secondary: "bg-surface-2 hover:bg-surface-3 text-text-primary border border-border",
  outline: "bg-surface-2 hover:bg-surface-3 text-text-primary border border-border",
  ghost: "bg-transparent hover:bg-surface-2 text-text-secondary hover:text-text-primary border border-transparent",
  danger: "bg-red-900 hover:bg-red-800 text-white border border-red-700",
};

const sizeClasses = {
  sm: "px-3 py-1.5 text-xs gap-1.5",
  md: "px-4 py-2 text-sm gap-2",
  lg: "px-6 py-3 text-base gap-2",
};

export function Button({
  variant = "secondary",
  size = "md",
  loading = false,
  icon,
  children,
  className,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center rounded-lg font-medium transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed",
        variantClasses[variant],
        sizeClasses[size],
        className
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading ? <Loader2 className="w-4 h-4 animate-spin mr-1" /> : icon}
      {children}
    </button>
  );
}
