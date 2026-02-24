"use client";

import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import {
  Database,
  GitBranch,
  BarChart3,
  Zap,
  ArrowRight,
  ArrowLeft,
  Check,
  Sparkles,
} from "lucide-react";
import { cn } from "@/lib/utils";
import Link from "next/link";

interface WelcomeModalProps {
  isOpen: boolean;
  onClose: () => void;
  userName?: string;
}

interface Step {
  icon: React.ReactNode;
  title: string;
  description: string;
  highlight?: string;
}

const steps: Step[] = [
  {
    icon: <Database className="h-8 w-8" />,
    title: "Connect Your Data Sources",
    description:
      "Link your payment processors, accounting software, databases, or upload CSV files. We support Stripe, PayStack, Xero, QuickBooks, and many more.",
    highlight: "11+ connectors available",
  },
  {
    icon: <GitBranch className="h-8 w-8" />,
    title: "Build Data Pipelines",
    description:
      "Create pipelines to automatically sync data from sources to your warehouse. Set schedules, add transformations, and let UnifiedLayer handle the rest.",
    highlight: "Automated & reliable",
  },
  {
    icon: <BarChart3 className="h-8 w-8" />,
    title: "Unlock Business Insights",
    description:
      "Once your data flows, gain actionable insights into revenue trends, cash flow, customer behavior, and more. Make data-driven decisions with confidence.",
    highlight: "Real-time analytics",
  },
  {
    icon: <Zap className="h-8 w-8" />,
    title: "You're All Set!",
    description:
      "Start by connecting your first data source. We'll guide you through the process step by step. Your 30-day free trial includes all features.",
    highlight: "No credit card required",
  },
];

const slideVariants = {
  enter: (direction: number) => ({
    x: direction > 0 ? 100 : -100,
    opacity: 0,
  }),
  center: {
    x: 0,
    opacity: 1,
  },
  exit: (direction: number) => ({
    x: direction < 0 ? 100 : -100,
    opacity: 0,
  }),
};

export function WelcomeModal({ isOpen, onClose, userName }: WelcomeModalProps) {
  const [currentStep, setCurrentStep] = useState(0);
  const [direction, setDirection] = useState(0);

  const isLastStep = currentStep === steps.length - 1;
  const isFirstStep = currentStep === 0;

  const handleNext = () => {
    if (isLastStep) {
      onClose();
    } else {
      setDirection(1);
      setCurrentStep((prev) => prev + 1);
    }
  };

  const handlePrev = () => {
    if (!isFirstStep) {
      setDirection(-1);
      setCurrentStep((prev) => prev - 1);
    }
  };

  const handleSkip = () => {
    onClose();
  };

  // Reset step when modal opens
  useEffect(() => {
    if (isOpen) {
      setCurrentStep(0);
      setDirection(0);
    }
  }, [isOpen]);

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="sm:max-w-lg overflow-hidden">
        <DialogHeader className="text-center pb-2">
          <div className="flex items-center justify-center gap-2 mb-2">
            <Sparkles className="h-5 w-5 text-primary" />
            <DialogTitle>
              {userName ? `Welcome, ${userName}!` : "Welcome to UnifiedLayer"}
            </DialogTitle>
          </div>
          <DialogDescription>
            Let&apos;s take a quick tour of what you can do
          </DialogDescription>
        </DialogHeader>

        {/* Step content */}
        <div className="relative h-72 overflow-hidden">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={currentStep}
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.3, ease: "easeInOut" }}
              className="absolute inset-0 flex flex-col items-center justify-center px-4"
            >
              {/* Icon */}
              <motion.div
                initial={{ scale: 0 }}
                animate={{ scale: 1 }}
                transition={{ delay: 0.1, type: "spring", stiffness: 200 }}
                className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center text-primary mb-6"
              >
                {steps[currentStep].icon}
              </motion.div>

              {/* Title */}
              <h3 className="text-xl font-semibold mb-2 text-center">
                {steps[currentStep].title}
              </h3>

              {/* Description */}
              <p className="text-muted-foreground text-center text-sm leading-relaxed max-w-sm">
                {steps[currentStep].description}
              </p>

              {/* Highlight badge */}
              {steps[currentStep].highlight && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="mt-4 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-primary/10 text-primary text-xs font-medium"
                >
                  <Check className="h-3 w-3" />
                  {steps[currentStep].highlight}
                </motion.div>
              )}
            </motion.div>
          </AnimatePresence>
        </div>

        {/* Progress dots */}
        <div className="flex justify-center gap-2 py-2">
          {steps.map((_, index) => (
            <button
              key={index}
              onClick={() => {
                setDirection(index > currentStep ? 1 : -1);
                setCurrentStep(index);
              }}
              className={cn(
                "w-2 h-2 rounded-full transition-all duration-200",
                currentStep === index
                  ? "bg-primary w-6"
                  : "bg-muted-foreground/30 hover:bg-muted-foreground/50"
              )}
              aria-label={`Go to step ${index + 1}`}
            />
          ))}
        </div>

        <DialogFooter className="flex-col sm:flex-row gap-2">
          <div className="flex gap-2 w-full sm:w-auto">
            {!isFirstStep && (
              <Button variant="outline" onClick={handlePrev} className="flex-1 sm:flex-none">
                <ArrowLeft className="h-4 w-4 mr-2" />
                Back
              </Button>
            )}
            {isFirstStep && (
              <Button variant="ghost" onClick={handleSkip} className="flex-1 sm:flex-none">
                Skip tour
              </Button>
            )}
          </div>

          <Button onClick={handleNext} className="flex-1 sm:flex-none">
            {isLastStep ? (
              <>
                Get Started
                <Sparkles className="h-4 w-4 ml-2" />
              </>
            ) : (
              <>
                Next
                <ArrowRight className="h-4 w-4 ml-2" />
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Hook to manage welcome modal state with localStorage
export function useWelcomeModal(storageKey = "unifiedlayer_welcome_shown") {
  const [isOpen, setIsOpen] = useState(false);

  useEffect(() => {
    // Check if welcome has been shown before
    const hasShown = localStorage.getItem(storageKey);
    if (!hasShown) {
      // Small delay for better UX
      const timer = setTimeout(() => setIsOpen(true), 500);
      return () => clearTimeout(timer);
    }
  }, [storageKey]);

  const close = () => {
    setIsOpen(false);
    localStorage.setItem(storageKey, "true");
  };

  const reset = () => {
    localStorage.removeItem(storageKey);
  };

  return { isOpen, close, reset };
}

// Quick start card component for dashboard
interface QuickStartCardProps {
  title: string;
  description: string;
  icon: React.ReactNode;
  href: string;
  isComplete?: boolean;
  className?: string;
}

export function QuickStartCard({
  title,
  description,
  icon,
  href,
  isComplete,
  className,
}: QuickStartCardProps) {
  return (
    <Link href={href}>
      <motion.div
        whileHover={{ scale: 1.02, y: -2 }}
        whileTap={{ scale: 0.98 }}
        className={cn(
          "relative p-4 rounded-lg border bg-card transition-all cursor-pointer",
          isComplete
            ? "border-success/30 bg-success/5"
            : "hover:border-primary/50",
          className
        )}
      >
        {isComplete && (
          <div className="absolute top-2 right-2">
            <div className="w-5 h-5 rounded-full bg-success flex items-center justify-center">
              <Check className="h-3 w-3 text-white" />
            </div>
          </div>
        )}

        <div className="flex items-start gap-3">
          <div
            className={cn(
              "w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0",
              isComplete ? "bg-success/10 text-success" : "bg-primary/10 text-primary"
            )}
          >
            {icon}
          </div>
          <div>
            <h4 className="font-medium text-sm">{title}</h4>
            <p className="text-xs text-muted-foreground mt-0.5">{description}</p>
          </div>
        </div>

        <div className="mt-3 flex items-center text-xs text-primary">
          {isComplete ? "Completed" : "Get started"}
          <ArrowRight className="h-3 w-3 ml-1" />
        </div>
      </motion.div>
    </Link>
  );
}

export default WelcomeModal;
