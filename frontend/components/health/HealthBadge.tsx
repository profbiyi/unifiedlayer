"use client";

import { cn } from "@/lib/utils";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { CheckCircle2, AlertTriangle, XCircle, HelpCircle } from "lucide-react";

export type HealthStatus = "healthy" | "warning" | "critical" | "unknown";

interface HealthBadgeProps {
  status?: HealthStatus;
  resourceType?: string;
  resourceId?: string | number;
  score?: number;
  showScore?: boolean;
  showLabel?: boolean;
  size?: "sm" | "md" | "lg";
  tooltip?: string;
  issues?: Array<{ message: string; severity: string }>;
  className?: string;
}

const statusConfig = {
  healthy: {
    label: "Healthy",
    icon: CheckCircle2,
    color: "text-green-500",
    bgColor: "bg-green-500/10",
    borderColor: "border-green-500/20",
    dotColor: "bg-green-500",
  },
  warning: {
    label: "Warning",
    icon: AlertTriangle,
    color: "text-yellow-500",
    bgColor: "bg-yellow-500/10",
    borderColor: "border-yellow-500/20",
    dotColor: "bg-yellow-500",
  },
  critical: {
    label: "Critical",
    icon: XCircle,
    color: "text-red-500",
    bgColor: "bg-red-500/10",
    borderColor: "border-red-500/20",
    dotColor: "bg-red-500",
  },
  unknown: {
    label: "Unknown",
    icon: HelpCircle,
    color: "text-gray-400",
    bgColor: "bg-gray-400/10",
    borderColor: "border-gray-400/20",
    dotColor: "bg-gray-400",
  },
};

const sizeConfig = {
  sm: {
    badge: "px-1.5 py-0.5 text-xs gap-1",
    icon: "h-3 w-3",
    dot: "h-1.5 w-1.5",
  },
  md: {
    badge: "px-2 py-1 text-sm gap-1.5",
    icon: "h-4 w-4",
    dot: "h-2 w-2",
  },
  lg: {
    badge: "px-3 py-1.5 text-base gap-2",
    icon: "h-5 w-5",
    dot: "h-2.5 w-2.5",
  },
};

export function HealthBadge({
  status = "unknown",
  score,
  showScore = false,
  showLabel = true,
  size = "sm",
  tooltip,
  issues,
  className,
}: HealthBadgeProps) {
  const config = statusConfig[status] || statusConfig.unknown;
  const sizeStyles = sizeConfig[size];
  const Icon = config.icon;

  const badge = (
    <div
      className={cn(
        "inline-flex items-center rounded-full border font-medium",
        config.bgColor,
        config.borderColor,
        config.color,
        sizeStyles.badge,
        className
      )}
    >
      <Icon className={sizeStyles.icon} />
      {showLabel && <span>{config.label}</span>}
      {showScore && score !== undefined && (
        <span className="opacity-80">({Math.round(score)})</span>
      )}
    </div>
  );

  // If we have tooltip content or issues, wrap in tooltip
  const hasTooltipContent = tooltip || (issues && issues.length > 0);

  if (!hasTooltipContent) {
    return badge;
  }

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>{badge}</TooltipTrigger>
        <TooltipContent className="max-w-xs">
          {tooltip && <p className="font-medium mb-1">{tooltip}</p>}
          {issues && issues.length > 0 && (
            <ul className="text-sm space-y-1">
              {issues.slice(0, 3).map((issue, idx) => (
                <li key={idx} className="flex items-start gap-1">
                  <span
                    className={cn(
                      "mt-1.5 rounded-full",
                      sizeStyles.dot,
                      issue.severity === "critical"
                        ? "bg-red-500"
                        : issue.severity === "warning"
                        ? "bg-yellow-500"
                        : "bg-blue-500"
                    )}
                  />
                  <span>{issue.message}</span>
                </li>
              ))}
              {issues.length > 3 && (
                <li className="text-muted-foreground">
                  +{issues.length - 3} more issues
                </li>
              )}
            </ul>
          )}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

/**
 * A simple dot indicator for health status.
 * Use when space is limited or in table cells.
 */
export function HealthDot({
  status,
  size = "md",
  className,
}: {
  status: HealthStatus;
  size?: "sm" | "md" | "lg";
  className?: string;
}) {
  const config = statusConfig[status] || statusConfig.unknown;
  const sizeStyles = sizeConfig[size];

  return (
    <TooltipProvider>
      <Tooltip>
        <TooltipTrigger asChild>
          <span
            className={cn(
              "inline-block rounded-full",
              config.dotColor,
              sizeStyles.dot,
              className
            )}
          />
        </TooltipTrigger>
        <TooltipContent>
          <p>{config.label}</p>
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  );
}

export default HealthBadge;
