"use client";

import { useOnboardingStatus } from "@/hooks/queries/useOnboarding";
import { OnboardingChecklist } from "./OnboardingChecklist";

interface OnboardingWidgetProps {
  className?: string;
}

export function OnboardingWidget({ className }: OnboardingWidgetProps) {
  const { data: status, isLoading } = useOnboardingStatus();

  // Don't show if loading or if onboarding is completed/skipped
  if (isLoading) {
    return (
      <div className={className}>
        <div className="rounded-lg border bg-card p-4 animate-pulse">
          <div className="h-4 bg-muted rounded w-1/2 mb-2" />
          <div className="h-3 bg-muted rounded w-3/4" />
        </div>
      </div>
    );
  }

  if (!status || status.status === "completed" || status.status === "skipped") {
    return null;
  }

  // Only show if there's still progress to be made
  if (status.completion_percentage === 100) {
    return null;
  }

  return (
    <div className={className}>
      <OnboardingChecklist
        checklist={status.checklist}
        completionPercentage={status.completion_percentage}
        status={status.status}
        compact
      />
    </div>
  );
}
