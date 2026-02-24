"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { X, BarChart3, ArrowRight, Sparkles } from "lucide-react";
import { Button } from "@/components/ui/button";

export interface AutoDashboardNotificationData {
  dashboard_id: string;
  template_id: string;
  dashboard_name: string;
  dashboard_url: string;
  title: string;
  message: string;
  cta: string;
  type: string;
}

interface AutoDashboardNotificationProps {
  notification: AutoDashboardNotificationData | null;
  onDismiss?: () => void;
  autoDismissMs?: number;
}

/**
 * AutoDashboardNotification Component
 *
 * Shows a toast/banner notification when an auto-dashboard is created
 * after a user connects their first data source.
 *
 * Features:
 * - Animated entrance/exit with Framer Motion
 * - Click to navigate to dashboard
 * - Auto-dismiss after configurable timeout
 * - Manual dismiss button
 */
export function AutoDashboardNotification({
  notification,
  onDismiss,
  autoDismissMs = 15000, // 15 seconds default
}: AutoDashboardNotificationProps) {
  const router = useRouter();
  const [isVisible, setIsVisible] = useState(false);
  const [progress, setProgress] = useState(100);

  useEffect(() => {
    if (notification) {
      setIsVisible(true);
      setProgress(100);

      // Start progress animation
      const progressInterval = setInterval(() => {
        setProgress((prev) => {
          if (prev <= 0) return 0;
          return prev - (100 / (autoDismissMs / 100));
        });
      }, 100);

      // Auto-dismiss timer
      const dismissTimer = setTimeout(() => {
        handleDismiss();
      }, autoDismissMs);

      return () => {
        clearInterval(progressInterval);
        clearTimeout(dismissTimer);
      };
    }
  }, [notification, autoDismissMs]);

  const handleDismiss = () => {
    setIsVisible(false);
    // Wait for exit animation before calling onDismiss
    setTimeout(() => {
      onDismiss?.();
    }, 300);
  };

  const handleViewDashboard = () => {
    if (notification?.dashboard_url) {
      handleDismiss();
      router.push(notification.dashboard_url);
    }
  };

  if (!notification) return null;

  return (
    <AnimatePresence>
      {isVisible && (
        <motion.div
          initial={{ opacity: 0, y: 50, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: 20, scale: 0.95 }}
          transition={{ duration: 0.3, ease: "easeOut" }}
          className="fixed bottom-6 right-6 z-50 max-w-md"
        >
          <div className="relative overflow-hidden rounded-xl border bg-card shadow-2xl">
            {/* Progress bar */}
            <div className="absolute top-0 left-0 h-1 w-full bg-muted">
              <motion.div
                className="h-full bg-primary"
                initial={{ width: "100%" }}
                animate={{ width: `${progress}%` }}
                transition={{ duration: 0.1, ease: "linear" }}
              />
            </div>

            {/* Content */}
            <div className="p-5 pt-6">
              {/* Header with icon and dismiss button */}
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <BarChart3 className="h-6 w-6 text-primary" />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <Sparkles className="h-4 w-4 text-amber-500" />
                    <h4 className="font-semibold text-foreground">
                      {notification.title}
                    </h4>
                  </div>
                  <p className="mt-1 text-sm text-muted-foreground line-clamp-2">
                    {notification.message}
                  </p>
                </div>

                <button
                  onClick={handleDismiss}
                  className="shrink-0 rounded-full p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
                  aria-label="Dismiss notification"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>

              {/* Action button */}
              <div className="mt-4 flex justify-end">
                <Button
                  onClick={handleViewDashboard}
                  className="group"
                  size="sm"
                >
                  {notification.cta}
                  <ArrowRight className="ml-2 h-4 w-4 transition-transform group-hover:translate-x-1" />
                </Button>
              </div>
            </div>

            {/* Subtle gradient overlay */}
            <div className="pointer-events-none absolute inset-0 bg-gradient-to-r from-primary/5 via-transparent to-transparent" />
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

/**
 * Hook to manage auto-dashboard notification state.
 *
 * Usage:
 * ```tsx
 * const { notification, showNotification, dismissNotification } = useAutoDashboardNotification();
 *
 * // After source creation:
 * if (response.auto_dashboard) {
 *   showNotification(response.auto_dashboard);
 * }
 *
 * // In render:
 * <AutoDashboardNotification
 *   notification={notification}
 *   onDismiss={dismissNotification}
 * />
 * ```
 */
export function useAutoDashboardNotification() {
  const [notification, setNotification] =
    useState<AutoDashboardNotificationData | null>(null);

  const showNotification = (data: AutoDashboardNotificationData) => {
    setNotification(data);
  };

  const dismissNotification = () => {
    setNotification(null);
  };

  return {
    notification,
    showNotification,
    dismissNotification,
  };
}

export default AutoDashboardNotification;
