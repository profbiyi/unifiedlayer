"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

type Status = "active" | "inactive" | "error" | "warning" | "running" | "pending";

interface StatusIndicatorProps {
  status: Status;
  size?: "xs" | "sm" | "md" | "lg";
  showLabel?: boolean;
  label?: string;
  className?: string;
}

const statusConfig = {
  active: {
    color: "bg-success",
    pulseColor: "bg-success/50",
    label: "Active",
    animate: true,
  },
  inactive: {
    color: "bg-muted-foreground",
    pulseColor: "bg-muted-foreground/50",
    label: "Inactive",
    animate: false,
  },
  error: {
    color: "bg-error",
    pulseColor: "bg-error/50",
    label: "Error",
    animate: false,
  },
  warning: {
    color: "bg-warning",
    pulseColor: "bg-warning/50",
    label: "Warning",
    animate: true,
  },
  running: {
    color: "bg-running",
    pulseColor: "bg-running/50",
    label: "Running",
    animate: true,
  },
  pending: {
    color: "bg-warning",
    pulseColor: "bg-warning/50",
    label: "Pending",
    animate: true,
  },
};

const sizeConfig = {
  xs: {
    dot: "w-1.5 h-1.5",
    pulse: "w-3 h-3",
    text: "text-xs",
    gap: "gap-1.5",
  },
  sm: {
    dot: "w-2 h-2",
    pulse: "w-4 h-4",
    text: "text-xs",
    gap: "gap-2",
  },
  md: {
    dot: "w-2.5 h-2.5",
    pulse: "w-5 h-5",
    text: "text-sm",
    gap: "gap-2",
  },
  lg: {
    dot: "w-3 h-3",
    pulse: "w-6 h-6",
    text: "text-base",
    gap: "gap-3",
  },
};

const pulseVariants = {
  animate: {
    scale: [1, 1.5, 1],
    opacity: [0.7, 0, 0.7],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
};

export function StatusIndicator({
  status,
  size = "sm",
  showLabel = false,
  label,
  className,
}: StatusIndicatorProps) {
  const config = statusConfig[status];
  const sizes = sizeConfig[size];

  return (
    <div className={cn("flex items-center", sizes.gap, className)}>
      <div className="relative flex items-center justify-center">
        {/* Pulse ring for animated states */}
        {config.animate && (
          <motion.div
            variants={pulseVariants}
            animate="animate"
            className={cn(
              "absolute rounded-full",
              sizes.pulse,
              config.pulseColor
            )}
          />
        )}
        {/* Core dot */}
        <div
          className={cn(
            "relative rounded-full",
            sizes.dot,
            config.color
          )}
        />
      </div>
      {showLabel && (
        <span className={cn("text-muted-foreground", sizes.text)}>
          {label || config.label}
        </span>
      )}
    </div>
  );
}

// Connection status indicator with animated line
interface ConnectionStatusProps {
  isConnected: boolean;
  className?: string;
}

export function ConnectionStatus({ isConnected, className }: ConnectionStatusProps) {
  return (
    <div className={cn("flex items-center gap-2", className)}>
      <StatusIndicator
        status={isConnected ? "active" : "error"}
        size="sm"
      />
      <span className="text-sm text-muted-foreground">
        {isConnected ? "Connected" : "Disconnected"}
      </span>
    </div>
  );
}

// Sync status indicator with progress
interface SyncStatusIndicatorProps {
  status: "idle" | "syncing" | "completed" | "failed";
  progress?: number;
  className?: string;
}

export function SyncStatusIndicator({
  status,
  progress,
  className,
}: SyncStatusIndicatorProps) {
  const statusMap: Record<typeof status, Status> = {
    idle: "inactive",
    syncing: "running",
    completed: "active",
    failed: "error",
  };

  const labelMap: Record<typeof status, string> = {
    idle: "Idle",
    syncing: progress !== undefined ? `Syncing ${progress}%` : "Syncing...",
    completed: "Synced",
    failed: "Sync Failed",
  };

  return (
    <div className={cn("flex items-center gap-2", className)}>
      <StatusIndicator status={statusMap[status]} size="sm" />
      <span className="text-sm text-muted-foreground">{labelMap[status]}</span>
    </div>
  );
}

// Pipeline status indicator
type PipelineStatus = "active" | "paused" | "error" | "running";

interface PipelineStatusIndicatorProps {
  status: PipelineStatus;
  showLabel?: boolean;
  size?: "xs" | "sm" | "md" | "lg";
  className?: string;
}

export function PipelineStatusIndicator({
  status,
  showLabel = true,
  size = "sm",
  className,
}: PipelineStatusIndicatorProps) {
  const statusMap: Record<PipelineStatus, Status> = {
    active: "active",
    paused: "inactive",
    error: "error",
    running: "running",
  };

  const labelMap: Record<PipelineStatus, string> = {
    active: "Active",
    paused: "Paused",
    error: "Error",
    running: "Running",
  };

  return (
    <StatusIndicator
      status={statusMap[status]}
      size={size}
      showLabel={showLabel}
      label={labelMap[status]}
      className={className}
    />
  );
}

// Status badge (combines indicator with styled container)
interface StatusBadgeProps {
  status: Status;
  label?: string;
  className?: string;
}

export function StatusBadge({ status, label, className }: StatusBadgeProps) {
  const config = statusConfig[status];

  const bgColors: Record<Status, string> = {
    active: "bg-success/10 text-success border-success/20",
    inactive: "bg-muted text-muted-foreground border-muted",
    error: "bg-error/10 text-error border-error/20",
    warning: "bg-warning/10 text-warning border-warning/20",
    running: "bg-running/10 text-running border-running/20",
    pending: "bg-warning/10 text-warning border-warning/20",
  };

  return (
    <div
      className={cn(
        "inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border",
        bgColors[status],
        className
      )}
    >
      <StatusIndicator status={status} size="xs" />
      <span>{label || config.label}</span>
    </div>
  );
}

export default StatusIndicator;
