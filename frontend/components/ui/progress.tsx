"use client"

import * as React from "react"
import * as ProgressPrimitive from "@radix-ui/react-progress"

import { cn } from "@/lib/utils"

interface ProgressProps extends React.ComponentPropsWithoutRef<typeof ProgressPrimitive.Root> {
  animated?: boolean;
  indeterminate?: boolean;
}

const Progress = React.forwardRef<
  React.ElementRef<typeof ProgressPrimitive.Root>,
  ProgressProps
>(({ className, value, animated, indeterminate, ...props }, ref) => (
  <ProgressPrimitive.Root
    ref={ref}
    className={cn(
      "relative h-2 w-full overflow-hidden rounded-full bg-primary/20",
      className
    )}
    {...props}
  >
    {indeterminate ? (
      // Indeterminate mode - shows a moving bar when we don't know progress
      <div className="h-full w-full bg-primary/20 relative overflow-hidden">
        <div className="absolute h-full w-1/3 bg-primary rounded-full animate-indeterminate" />
      </div>
    ) : (
      <ProgressPrimitive.Indicator
        className={cn(
          "h-full w-full flex-1 bg-primary transition-all",
          animated && "relative overflow-hidden"
        )}
        style={{ transform: `translateX(-${100 - (value || 0)}%)` }}
      >
        {animated && (
          // Shimmer effect for animated progress
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/30 to-transparent animate-shimmer" />
        )}
      </ProgressPrimitive.Indicator>
    )}
  </ProgressPrimitive.Root>
))
Progress.displayName = ProgressPrimitive.Root.displayName

export { Progress }
