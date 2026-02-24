"use client";

import { forwardRef, ReactNode } from "react";
import { motion, HTMLMotionProps, Variants } from "framer-motion";
import { cn } from "@/lib/utils";

// Animated card with hover lift effect
interface AnimatedCardProps extends HTMLMotionProps<"div"> {
  children: ReactNode;
  hoverScale?: number;
  hoverY?: number;
  className?: string;
}

export const AnimatedCard = forwardRef<HTMLDivElement, AnimatedCardProps>(
  ({ children, hoverScale = 1.02, hoverY = -4, className, ...props }, ref) => {
    return (
      <motion.div
        ref={ref}
        whileHover={{
          scale: hoverScale,
          y: hoverY,
          transition: { duration: 0.2, ease: "easeOut" },
        }}
        whileTap={{ scale: 0.98 }}
        className={cn(
          "rounded-lg border bg-card text-card-foreground shadow-sm transition-shadow hover:shadow-lg",
          className
        )}
        {...props}
      >
        {children}
      </motion.div>
    );
  }
);
AnimatedCard.displayName = "AnimatedCard";

// Animated button with press effect
interface AnimatedButtonProps extends HTMLMotionProps<"button"> {
  children: ReactNode;
  className?: string;
}

export const AnimatedButton = forwardRef<HTMLButtonElement, AnimatedButtonProps>(
  ({ children, className, ...props }, ref) => {
    return (
      <motion.button
        ref={ref}
        whileHover={{ scale: 1.05 }}
        whileTap={{ scale: 0.95 }}
        transition={{ duration: 0.1 }}
        className={className}
        {...props}
      >
        {children}
      </motion.button>
    );
  }
);
AnimatedButton.displayName = "AnimatedButton";

// Shimmer effect for loading states
interface ShimmerEffectProps {
  className?: string;
  duration?: number;
}

export function ShimmerEffect({ className, duration = 1.5 }: ShimmerEffectProps) {
  return (
    <motion.div
      className={cn(
        "absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent",
        className
      )}
      animate={{
        x: ["-100%", "100%"],
      }}
      transition={{
        duration,
        repeat: Infinity,
        ease: "easeInOut",
      }}
    />
  );
}

// Pulse effect for attention
interface PulseEffectProps {
  children: ReactNode;
  isActive?: boolean;
  color?: string;
  className?: string;
}

export function PulseEffect({
  children,
  isActive = true,
  color = "primary",
  className,
}: PulseEffectProps) {
  const colorClasses: Record<string, string> = {
    primary: "bg-primary/30",
    success: "bg-success/30",
    warning: "bg-warning/30",
    error: "bg-error/30",
  };

  return (
    <div className={cn("relative inline-flex", className)}>
      {isActive && (
        <motion.div
          className={cn(
            "absolute inset-0 rounded-full",
            colorClasses[color] || colorClasses.primary
          )}
          animate={{
            scale: [1, 1.5, 1],
            opacity: [0.7, 0, 0.7],
          }}
          transition={{
            duration: 2,
            repeat: Infinity,
            ease: "easeInOut",
          }}
        />
      )}
      <div className="relative">{children}</div>
    </div>
  );
}

// Fade in animation wrapper
interface FadeInProps {
  children: ReactNode;
  delay?: number;
  duration?: number;
  className?: string;
}

export function FadeIn({
  children,
  delay = 0,
  duration = 0.3,
  className,
}: FadeInProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration, delay }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// Slide in animation wrapper
interface SlideInProps {
  children: ReactNode;
  direction?: "up" | "down" | "left" | "right";
  delay?: number;
  duration?: number;
  distance?: number;
  className?: string;
}

export function SlideIn({
  children,
  direction = "up",
  delay = 0,
  duration = 0.3,
  distance = 20,
  className,
}: SlideInProps) {
  const directionMap = {
    up: { y: distance },
    down: { y: -distance },
    left: { x: distance },
    right: { x: -distance },
  };

  return (
    <motion.div
      initial={{ opacity: 0, ...directionMap[direction] }}
      animate={{ opacity: 1, x: 0, y: 0 }}
      transition={{ duration, delay, ease: [0.25, 0.1, 0.25, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
}

// Stagger list animation
interface StaggerListProps {
  children: ReactNode;
  staggerDelay?: number;
  className?: string;
}

const containerVariants: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.05,
      delayChildren: 0.1,
    },
  },
};

const itemVariants: Variants = {
  hidden: { opacity: 0, y: 10 },
  visible: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.2 },
  },
};

export function StaggerList({
  children,
  staggerDelay = 0.05,
  className,
}: StaggerListProps) {
  return (
    <motion.div
      variants={{
        hidden: { opacity: 0 },
        visible: {
          opacity: 1,
          transition: {
            staggerChildren: staggerDelay,
            delayChildren: 0.1,
          },
        },
      }}
      initial="hidden"
      animate="visible"
      className={className}
    >
      {children}
    </motion.div>
  );
}

// Stagger item (use as child of StaggerList)
interface StaggerItemProps {
  children: ReactNode;
  className?: string;
}

export function StaggerItem({ children, className }: StaggerItemProps) {
  return (
    <motion.div variants={itemVariants} className={className}>
      {children}
    </motion.div>
  );
}

// Number counter animation
interface AnimatedCounterProps {
  value: number;
  duration?: number;
  formatValue?: (value: number) => string;
  className?: string;
}

export function AnimatedCounter({
  value,
  duration = 1,
  formatValue = (v) => Math.round(v).toLocaleString(),
  className,
}: AnimatedCounterProps) {
  return (
    <motion.span
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={className}
    >
      <motion.span
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2 }}
      >
        {formatValue(value)}
      </motion.span>
    </motion.span>
  );
}

// Tooltip that follows cursor
interface FollowCursorTooltipProps {
  children: ReactNode;
  content: string;
  className?: string;
}

export function FollowCursorTooltip({
  children,
  content,
  className,
}: FollowCursorTooltipProps) {
  return (
    <motion.div className={cn("relative group", className)}>
      {children}
      <motion.div
        className="absolute z-50 px-2 py-1 text-xs bg-popover text-popover-foreground rounded shadow-lg opacity-0 group-hover:opacity-100 pointer-events-none whitespace-nowrap"
        initial={false}
        style={{
          top: "100%",
          left: "50%",
          translateX: "-50%",
          marginTop: 8,
        }}
        transition={{ duration: 0.15 }}
      >
        {content}
      </motion.div>
    </motion.div>
  );
}

// Hover reveal effect
interface HoverRevealProps {
  children: ReactNode;
  revealContent: ReactNode;
  className?: string;
}

export function HoverReveal({
  children,
  revealContent,
  className,
}: HoverRevealProps) {
  return (
    <motion.div
      className={cn("relative overflow-hidden", className)}
      whileHover="hover"
    >
      <motion.div
        variants={{
          hover: { opacity: 0.5, scale: 0.95 },
        }}
        transition={{ duration: 0.2 }}
      >
        {children}
      </motion.div>
      <motion.div
        className="absolute inset-0 flex items-center justify-center"
        variants={{
          hover: { opacity: 1 },
        }}
        initial={{ opacity: 0 }}
        transition={{ duration: 0.2 }}
      >
        {revealContent}
      </motion.div>
    </motion.div>
  );
}

// Skeleton with shimmer for loading
interface SkeletonShimmerProps {
  width?: string | number;
  height?: string | number;
  borderRadius?: string | number;
  className?: string;
}

export function SkeletonShimmer({
  width = "100%",
  height = 20,
  borderRadius = 4,
  className,
}: SkeletonShimmerProps) {
  return (
    <div
      className={cn("relative overflow-hidden bg-muted", className)}
      style={{ width, height, borderRadius }}
    >
      <ShimmerEffect />
    </div>
  );
}

// Press scale effect for interactive elements
interface PressScaleProps extends HTMLMotionProps<"div"> {
  children: ReactNode;
  scale?: number;
  className?: string;
}

export function PressScale({
  children,
  scale = 0.95,
  className,
  ...props
}: PressScaleProps) {
  return (
    <motion.div
      whileTap={{ scale }}
      transition={{ duration: 0.1 }}
      className={className}
      {...props}
    >
      {children}
    </motion.div>
  );
}

export default AnimatedCard;
