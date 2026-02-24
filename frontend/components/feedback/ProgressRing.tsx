"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

interface ProgressRingProps {
  progress: number; // 0-100
  size?: "sm" | "md" | "lg" | "xl";
  strokeWidth?: number;
  showPercentage?: boolean;
  color?: "primary" | "success" | "warning" | "error" | "running";
  label?: string;
  className?: string;
  animated?: boolean;
}

const sizeConfig = {
  sm: { size: 40, textSize: "text-xs", strokeWidth: 4 },
  md: { size: 64, textSize: "text-sm", strokeWidth: 5 },
  lg: { size: 96, textSize: "text-lg", strokeWidth: 6 },
  xl: { size: 128, textSize: "text-xl", strokeWidth: 8 },
};

const colorConfig = {
  primary: { stroke: "stroke-primary", text: "text-primary" },
  success: { stroke: "stroke-success", text: "text-success" },
  warning: { stroke: "stroke-warning", text: "text-warning" },
  error: { stroke: "stroke-error", text: "text-error" },
  running: { stroke: "stroke-running", text: "text-running" },
};

export function ProgressRing({
  progress,
  size = "md",
  strokeWidth,
  showPercentage = true,
  color = "primary",
  label,
  className,
  animated = true,
}: ProgressRingProps) {
  const config = sizeConfig[size];
  const colors = colorConfig[color];
  const actualStrokeWidth = strokeWidth || config.strokeWidth;
  const radius = (config.size - actualStrokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;
  const strokeDashoffset = circumference - (progress / 100) * circumference;

  return (
    <div
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: config.size, height: config.size }}
    >
      {/* Background circle */}
      <svg
        className="absolute transform -rotate-90"
        width={config.size}
        height={config.size}
      >
        <circle
          className="stroke-muted"
          strokeWidth={actualStrokeWidth}
          fill="none"
          r={radius}
          cx={config.size / 2}
          cy={config.size / 2}
        />
        {/* Progress circle */}
        <motion.circle
          className={cn(colors.stroke, "transition-all")}
          strokeWidth={actualStrokeWidth}
          strokeLinecap="round"
          fill="none"
          r={radius}
          cx={config.size / 2}
          cy={config.size / 2}
          initial={animated ? { strokeDashoffset: circumference } : false}
          animate={{ strokeDashoffset }}
          transition={{ duration: 0.5, ease: "easeOut" }}
          style={{
            strokeDasharray: circumference,
          }}
        />
      </svg>

      {/* Center content */}
      <div className="relative flex flex-col items-center justify-center">
        {showPercentage && (
          <motion.span
            className={cn("font-semibold", config.textSize, colors.text)}
            initial={animated ? { opacity: 0 } : false}
            animate={{ opacity: 1 }}
          >
            {Math.round(progress)}%
          </motion.span>
        )}
        {label && (
          <span className="text-[10px] text-muted-foreground mt-0.5">
            {label}
          </span>
        )}
      </div>
    </div>
  );
}

// Indeterminate progress ring (for unknown progress)
interface IndeterminateRingProps {
  size?: "sm" | "md" | "lg" | "xl";
  color?: "primary" | "success" | "warning" | "error" | "running";
  className?: string;
}

export function IndeterminateRing({
  size = "md",
  color = "primary",
  className,
}: IndeterminateRingProps) {
  const config = sizeConfig[size];
  const colors = colorConfig[color];
  const strokeWidth = config.strokeWidth;
  const radius = (config.size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;

  return (
    <div
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: config.size, height: config.size }}
    >
      <motion.svg
        className="absolute"
        width={config.size}
        height={config.size}
        animate={{ rotate: 360 }}
        transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
      >
        <circle
          className="stroke-muted"
          strokeWidth={strokeWidth}
          fill="none"
          r={radius}
          cx={config.size / 2}
          cy={config.size / 2}
        />
        <circle
          className={colors.stroke}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          fill="none"
          r={radius}
          cx={config.size / 2}
          cy={config.size / 2}
          strokeDasharray={`${circumference * 0.25} ${circumference * 0.75}`}
        />
      </motion.svg>
    </div>
  );
}

// Multi-segment progress ring (for showing multiple metrics)
interface SegmentedProgressRingProps {
  segments: Array<{
    value: number;
    color: "primary" | "success" | "warning" | "error" | "running";
    label?: string;
  }>;
  size?: "md" | "lg" | "xl";
  showTotal?: boolean;
  className?: string;
}

export function SegmentedProgressRing({
  segments,
  size = "lg",
  showTotal = true,
  className,
}: SegmentedProgressRingProps) {
  const config = sizeConfig[size];
  const strokeWidth = config.strokeWidth;
  const radius = (config.size - strokeWidth) / 2;
  const circumference = radius * 2 * Math.PI;

  const total = segments.reduce((sum, seg) => sum + seg.value, 0);
  let accumulatedOffset = 0;

  return (
    <div
      className={cn("relative inline-flex items-center justify-center", className)}
      style={{ width: config.size, height: config.size }}
    >
      <svg
        className="absolute transform -rotate-90"
        width={config.size}
        height={config.size}
      >
        {/* Background circle */}
        <circle
          className="stroke-muted"
          strokeWidth={strokeWidth}
          fill="none"
          r={radius}
          cx={config.size / 2}
          cy={config.size / 2}
        />

        {/* Segment circles */}
        {segments.map((segment, index) => {
          const segmentLength = (segment.value / 100) * circumference;
          const offset = accumulatedOffset;
          accumulatedOffset += segmentLength;

          return (
            <motion.circle
              key={index}
              className={colorConfig[segment.color].stroke}
              strokeWidth={strokeWidth}
              strokeLinecap="round"
              fill="none"
              r={radius}
              cx={config.size / 2}
              cy={config.size / 2}
              initial={{ strokeDashoffset: circumference }}
              animate={{
                strokeDashoffset: circumference - segmentLength,
              }}
              transition={{ duration: 0.5, ease: "easeOut", delay: index * 0.1 }}
              style={{
                strokeDasharray: `${segmentLength} ${circumference}`,
                transform: `rotate(${(offset / circumference) * 360}deg)`,
                transformOrigin: "center",
              }}
            />
          );
        })}
      </svg>

      {/* Center content */}
      {showTotal && (
        <div className="relative flex flex-col items-center justify-center">
          <span className={cn("font-semibold", config.textSize)}>
            {Math.round(total)}%
          </span>
          <span className="text-[10px] text-muted-foreground">Total</span>
        </div>
      )}
    </div>
  );
}

// Onboarding progress ring with steps
interface OnboardingProgressRingProps {
  completedSteps: number;
  totalSteps: number;
  size?: "md" | "lg" | "xl";
  className?: string;
}

export function OnboardingProgressRing({
  completedSteps,
  totalSteps,
  size = "lg",
  className,
}: OnboardingProgressRingProps) {
  const progress = (completedSteps / totalSteps) * 100;

  return (
    <div className={cn("flex flex-col items-center gap-2", className)}>
      <ProgressRing
        progress={progress}
        size={size}
        color={progress === 100 ? "success" : "primary"}
        showPercentage={false}
      />
      <span className="text-sm text-muted-foreground">
        {completedSteps} of {totalSteps} steps
      </span>
    </div>
  );
}

export default ProgressRing;
