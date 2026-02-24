"use client";

import { useEffect, useState } from "react";
import { SuccessConfetti } from "./SuccessConfetti";

/**
 * Global confetti listener that triggers on special events.
 * Add this to the root layout to enable app-wide celebrations.
 */
export function GlobalConfetti() {
  const [showConfetti, setShowConfetti] = useState(false);

  useEffect(() => {
    const handleFirstRun = () => {
      setShowConfetti(true);
    };

    const handleFirstSync = () => {
      setShowConfetti(true);
    };

    const handleOnboardingComplete = () => {
      setShowConfetti(true);
    };

    // Listen for celebration events
    window.addEventListener("unifiedlayer:first-run", handleFirstRun);
    window.addEventListener("unifiedlayer:first-sync", handleFirstSync);
    window.addEventListener("unifiedlayer:onboarding-complete", handleOnboardingComplete);

    return () => {
      window.removeEventListener("unifiedlayer:first-run", handleFirstRun);
      window.removeEventListener("unifiedlayer:first-sync", handleFirstSync);
      window.removeEventListener("unifiedlayer:onboarding-complete", handleOnboardingComplete);
    };
  }, []);

  if (!showConfetti) return null;

  return (
    <SuccessConfetti
      isActive={showConfetti}
      onComplete={() => setShowConfetti(false)}
      duration={4000}
    />
  );
}
