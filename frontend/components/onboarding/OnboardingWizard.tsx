"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { useCurrentUser } from "@/hooks/queries/useAuth";
import api from "@/lib/api-client";
import {
  Sparkles,
  Database,
  HardDrive,
  Workflow,
  ArrowRight,
  ArrowLeft,
} from "lucide-react";

const ONBOARDING_STORAGE_KEY = "datasync_onboarded";

interface OnboardingStep {
  title: string;
  description: string;
  icon: React.ElementType;
  action?: {
    label: string;
    href: string;
  };
}

const steps: OnboardingStep[] = [
  {
    title: "Welcome to UnifiedLayer!",
    description:
      "Let's get you set up in 3 quick steps. We'll walk you through connecting your first data source, setting up a destination, and creating your first pipeline.",
    icon: Sparkles,
  },
  {
    title: "Connect a Data Source",
    description:
      "Data sources are where your data lives. Connect a database, API, cloud storage, or SaaS tool to start syncing data.",
    icon: Database,
    action: {
      label: "Connect your first data source",
      href: "/sources/new",
    },
  },
  {
    title: "Set Up a Destination",
    description:
      "Destinations are where your data goes. Choose a data warehouse, database, or storage service to receive your synced data.",
    icon: HardDrive,
    action: {
      label: "Set up where your data goes",
      href: "/destinations/new",
    },
  },
  {
    title: "Create Your First Pipeline",
    description:
      "Pipelines connect sources to destinations and handle scheduling, transformations, and monitoring automatically.",
    icon: Workflow,
    action: {
      label: "Create your first pipeline",
      href: "/pipelines/new",
    },
  },
];

export default function OnboardingWizard() {
  const { data: user } = useCurrentUser();
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [open, setOpen] = useState(true);

  const totalSteps = steps.length;
  const step = steps[currentStep];
  const Icon = step.icon;
  const progressValue = ((currentStep + 1) / totalSteps) * 100;

  const completeOnboarding = async () => {
    // Store in localStorage as immediate flag
    localStorage.setItem(ONBOARDING_STORAGE_KEY, "true");

    // Also try to persist to the backend
    if (user?.organization_id) {
      try {
        await api.patch(`/organizations/${user.organization_id}`, {
          admin_onboarded: true,
        });
      } catch {
        // localStorage fallback is sufficient
      }
    }

    setOpen(false);
  };

  const handleNext = () => {
    if (currentStep < totalSteps - 1) {
      setCurrentStep((prev) => prev + 1);
    } else {
      completeOnboarding();
    }
  };

  const handleBack = () => {
    if (currentStep > 0) {
      setCurrentStep((prev) => prev - 1);
    }
  };

  const handleActionClick = (href: string) => {
    completeOnboarding();
    router.push(href);
  };

  const firstName = user?.full_name?.split(" ")[0] || user?.username || "there";

  return (
    <Dialog open={open} onOpenChange={(value) => !value && completeOnboarding()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <div className="flex items-center gap-2 text-xs text-muted-foreground mb-2">
            Step {currentStep + 1} of {totalSteps}
          </div>
          <Progress value={progressValue} className="mb-4 h-1.5" />
          <div className="flex justify-center py-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-2xl bg-primary/10">
              <Icon className="h-8 w-8 text-primary" />
            </div>
          </div>
          <DialogTitle className="text-center text-xl">
            {currentStep === 0
              ? `Welcome to UnifiedLayer, ${firstName}!`
              : step.title}
          </DialogTitle>
          <DialogDescription className="text-center">
            {currentStep === 0
              ? "Let's get you set up in 3 quick steps."
              : step.description}
          </DialogDescription>
        </DialogHeader>

        {currentStep === 0 && (
          <p className="text-sm text-muted-foreground text-center">
            {step.description}
          </p>
        )}

        {step.action && (
          <div className="flex justify-center pt-2">
            <Button
              size="lg"
              onClick={() => handleActionClick(step.action!.href)}
            >
              {step.action.label}
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </div>
        )}

        <DialogFooter className="flex-row items-center justify-between sm:justify-between gap-2 pt-2">
          <div>
            {currentStep > 0 && (
              <Button variant="ghost" size="sm" onClick={handleBack}>
                <ArrowLeft className="mr-1 h-4 w-4" />
                Back
              </Button>
            )}
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="ghost"
              size="sm"
              onClick={completeOnboarding}
            >
              {currentStep === totalSteps - 1
                ? "Skip for now"
                : "Skip onboarding"}
            </Button>
            <Button size="sm" onClick={handleNext}>
              {currentStep === totalSteps - 1 ? "Finish" : "Next"}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export function useShowOnboarding(): boolean {
  const { data: user, isLoading } = useCurrentUser();

  if (isLoading || !user) return false;

  // Check localStorage first (immediate, works offline)
  if (typeof window !== "undefined") {
    if (localStorage.getItem(ONBOARDING_STORAGE_KEY) === "true") {
      return false;
    }
  }

  // Check organization's admin_onboarded field
  if (user.organization?.admin_onboarded) {
    return false;
  }

  return true;
}
