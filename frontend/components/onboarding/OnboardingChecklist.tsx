"use client";

import { motion } from "framer-motion";
import { Check, Circle, ArrowRight } from "lucide-react";
import Link from "next/link";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { ChecklistItem } from "@/types/onboarding";
import { cn } from "@/lib/utils";

interface OnboardingChecklistProps {
  checklist: ChecklistItem[];
  completionPercentage: number;
  status: string;
  onSkip?: () => void;
  compact?: boolean;
}

export function OnboardingChecklist({
  checklist,
  completionPercentage,
  status,
  onSkip,
  compact = false,
}: OnboardingChecklistProps) {
  const nextStep = checklist.find((item) => !item.completed);

  if (compact) {
    return (
      <div className="rounded-lg border bg-card p-4 space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-medium">Getting Started</h3>
            <p className="text-sm text-muted-foreground">
              {completionPercentage}% complete
            </p>
          </div>
          <div className="w-20">
            <Progress value={completionPercentage} className="h-2" />
          </div>
        </div>

        {nextStep && status !== "completed" && status !== "skipped" && (
          <Link href={nextStep.href}>
            <Button size="sm" className="w-full">
              {nextStep.title}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        )}

        {(status === "completed" || status === "skipped") && (
          <p className="text-sm text-muted-foreground text-center">
            {status === "completed" ? "All done!" : "Onboarding skipped"}
          </p>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">Your Progress</h2>
        <p className="text-muted-foreground">
          Complete these steps to get the most out of UnifiedLayer.
        </p>
      </div>

      <div className="flex items-center gap-4 px-4">
        <Progress value={completionPercentage} className="flex-1" />
        <span className="text-sm font-medium text-muted-foreground">
          {completionPercentage}%
        </span>
      </div>

      <div className="space-y-2">
        {checklist.map((item, index) => {
          const isNext = nextStep?.id === item.id;

          return (
            <motion.div
              key={item.id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.05 }}
            >
              <Link
                href={item.completed ? "#" : item.href}
                className={cn(
                  "flex items-start gap-4 p-4 rounded-lg border transition-colors",
                  item.completed
                    ? "bg-muted/50 border-transparent"
                    : isNext
                    ? "bg-primary/5 border-primary hover:bg-primary/10"
                    : "bg-card hover:bg-accent/50"
                )}
              >
                <div
                  className={cn(
                    "w-6 h-6 rounded-full flex items-center justify-center shrink-0 mt-0.5",
                    item.completed
                      ? "bg-green-500 text-white"
                      : isNext
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  )}
                >
                  {item.completed ? (
                    <Check className="w-4 h-4" />
                  ) : (
                    <Circle className="w-3 h-3" />
                  )}
                </div>

                <div className="flex-1 min-w-0">
                  <h3
                    className={cn(
                      "font-medium",
                      item.completed && "text-muted-foreground line-through"
                    )}
                  >
                    {item.title}
                  </h3>
                  <p className="text-sm text-muted-foreground">
                    {item.description}
                  </p>
                </div>

                {!item.completed && (
                  <ArrowRight
                    className={cn(
                      "w-5 h-5 shrink-0",
                      isNext ? "text-primary" : "text-muted-foreground"
                    )}
                  />
                )}
              </Link>
            </motion.div>
          );
        })}
      </div>

      {onSkip && status === "in_progress" && (
        <div className="flex justify-center pt-4">
          <Button variant="ghost" onClick={onSkip}>
            Skip onboarding
          </Button>
        </div>
      )}
    </div>
  );
}
