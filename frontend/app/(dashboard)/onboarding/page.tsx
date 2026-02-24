"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import { ArrowLeft, PartyPopper, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";
import { RoleSelector } from "@/components/onboarding/RoleSelector";
import { SourceRecommendations } from "@/components/onboarding/SourceRecommendations";
import { OnboardingChecklist } from "@/components/onboarding/OnboardingChecklist";
import {
  useRoleOptions,
  useOnboardingStatus,
  useSourceRecommendations,
  useSkipOnboarding,
} from "@/hooks/queries/useOnboarding";
import { UserRole } from "@/types/onboarding";

type OnboardingStep = "role" | "recommendations" | "checklist" | "completed";

export default function OnboardingPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState<OnboardingStep>("role");
  const [showConfetti, setShowConfetti] = useState(false);

  const { data: roles, isLoading: rolesLoading } = useRoleOptions();
  const { data: status, isLoading: statusLoading } = useOnboardingStatus();
  const { data: recommendations } = useSourceRecommendations();
  const { mutate: skipOnboarding } = useSkipOnboarding();

  // Determine starting step based on status
  useEffect(() => {
    if (status) {
      if (status.status === "completed") {
        setCurrentStep("completed");
      } else if (status.status === "skipped") {
        router.push("/overview");
      } else if (status.business_role) {
        // Role already selected, go to recommendations or checklist
        if (status.completion_percentage > 0) {
          setCurrentStep("checklist");
        } else {
          setCurrentStep("recommendations");
        }
      } else {
        setCurrentStep("role");
      }
    }
  }, [status, router]);

  const handleRoleSelected = () => {
    setCurrentStep("recommendations");
  };

  const handleSkipRecommendations = () => {
    setCurrentStep("checklist");
  };

  const handleSkipOnboarding = () => {
    skipOnboarding(undefined, {
      onSuccess: () => {
        router.push("/overview");
      },
    });
  };

  const handleGoBack = () => {
    if (currentStep === "recommendations") {
      setCurrentStep("role");
    } else if (currentStep === "checklist") {
      setCurrentStep("recommendations");
    }
  };

  // Check for completion
  useEffect(() => {
    if (status?.status === "completed" && currentStep !== "completed") {
      setShowConfetti(true);
      setCurrentStep("completed");
      setTimeout(() => setShowConfetti(false), 3000);
    }
  }, [status?.status, currentStep]);

  if (rolesLoading || statusLoading) {
    return (
      <div className="flex items-center justify-center min-h-[60vh]">
        <div className="animate-pulse space-y-4 w-full max-w-md">
          <div className="h-8 bg-muted rounded w-3/4 mx-auto" />
          <div className="h-4 bg-muted rounded w-1/2 mx-auto" />
          <div className="grid grid-cols-2 gap-4 mt-8">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="h-32 bg-muted rounded-lg" />
            ))}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[80vh] flex flex-col">
      {/* Progress indicator */}
      <div className="flex items-center justify-between mb-8">
        {currentStep !== "role" && currentStep !== "completed" ? (
          <Button variant="ghost" size="sm" onClick={handleGoBack}>
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back
          </Button>
        ) : (
          <div />
        )}

        <div className="flex items-center gap-2">
          {["role", "recommendations", "checklist"].map((step, index) => (
            <div
              key={step}
              className={`w-2 h-2 rounded-full transition-colors ${
                currentStep === step
                  ? "bg-primary"
                  : index <
                    ["role", "recommendations", "checklist"].indexOf(currentStep)
                  ? "bg-primary/50"
                  : "bg-muted"
              }`}
            />
          ))}
        </div>

        <Button variant="ghost" size="sm" onClick={() => router.push("/overview")}>
          Skip
        </Button>
      </div>

      {/* Main content */}
      <div className="flex-1 flex items-center justify-center">
        <div className="w-full max-w-2xl">
          <AnimatePresence mode="wait">
            {currentStep === "role" && roles && (
              <motion.div
                key="role"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <RoleSelector
                  roles={roles}
                  currentRole={status?.business_role as UserRole | undefined}
                  onRoleSelected={handleRoleSelected}
                />
              </motion.div>
            )}

            {currentStep === "recommendations" && recommendations && (
              <motion.div
                key="recommendations"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <SourceRecommendations
                  recommendations={recommendations}
                  onSkip={handleSkipRecommendations}
                />
              </motion.div>
            )}

            {currentStep === "checklist" && status && (
              <motion.div
                key="checklist"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
              >
                <OnboardingChecklist
                  checklist={status.checklist}
                  completionPercentage={status.completion_percentage}
                  status={status.status}
                  onSkip={handleSkipOnboarding}
                />
              </motion.div>
            )}

            {currentStep === "completed" && (
              <motion.div
                key="completed"
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="text-center space-y-6"
              >
                <div className="relative inline-block">
                  <motion.div
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    transition={{ type: "spring", delay: 0.2 }}
                    className="w-24 h-24 rounded-full bg-green-100 dark:bg-green-900/30 flex items-center justify-center mx-auto"
                  >
                    <PartyPopper className="w-12 h-12 text-green-600 dark:text-green-400" />
                  </motion.div>
                  {showConfetti && (
                    <motion.div
                      initial={{ opacity: 0 }}
                      animate={{ opacity: 1 }}
                      className="absolute inset-0"
                    >
                      {[...Array(12)].map((_, i) => (
                        <motion.div
                          key={i}
                          initial={{
                            x: 0,
                            y: 0,
                            scale: 0,
                          }}
                          animate={{
                            x: Math.cos((i * 30 * Math.PI) / 180) * 80,
                            y: Math.sin((i * 30 * Math.PI) / 180) * 80,
                            scale: [0, 1, 0],
                          }}
                          transition={{ duration: 1, delay: i * 0.05 }}
                          className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2"
                        >
                          <Sparkles
                            className={`w-4 h-4 ${
                              i % 3 === 0
                                ? "text-yellow-500"
                                : i % 3 === 1
                                ? "text-purple-500"
                                : "text-blue-500"
                            }`}
                          />
                        </motion.div>
                      ))}
                    </motion.div>
                  )}
                </div>

                <div className="space-y-2">
                  <h2 className="text-2xl font-bold tracking-tight">
                    You&apos;re all set!
                  </h2>
                  <p className="text-muted-foreground">
                    Your data platform is ready. Start exploring your data.
                  </p>
                </div>

                <div className="flex items-center justify-center gap-4 pt-4">
                  <Button onClick={() => router.push("/overview")}>
                    Go to Dashboard
                  </Button>
                  <Button variant="outline" onClick={() => router.push("/ask")}>
                    Ask AI a Question
                  </Button>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
