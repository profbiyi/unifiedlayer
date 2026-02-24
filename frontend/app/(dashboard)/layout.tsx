"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Sidebar from "@/components/layout/sidebar";
import Header from "@/components/layout/header";
import AuthGuard from "@/components/auth-guard";
import ImpersonationBanner from "@/components/layout/ImpersonationBanner";
import { AnimatedPage } from "@/components/animations/PageTransition";
import { WelcomeModal } from "@/components/feedback/WelcomeModal";
import { GlobalConfetti } from "@/components/feedback/GlobalConfetti";
import { useCurrentUser } from "@/hooks/queries/useAuth";
import api from "@/lib/api-client";

interface ImpersonationSession {
  target_org_id: number;
  target_org_name: string;
  target_org_slug: string;
  target_org_logo: string | null;
  started_at: string;
  expires_at: string;
}

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const { data: user } = useCurrentUser();
  const [impersonationSession, setImpersonationSession] = useState<ImpersonationSession | null>(null);
  const [showWelcome, setShowWelcome] = useState(false);

  // Show welcome modal for first-time users
  useEffect(() => {
    if (user && !localStorage.getItem("unifiedlayer_welcome_seen")) {
      // Small delay so the dashboard loads first
      const timer = setTimeout(() => setShowWelcome(true), 500);
      return () => clearTimeout(timer);
    }
  }, [user]);

  const handleWelcomeClose = () => {
    setShowWelcome(false);
    localStorage.setItem("unifiedlayer_welcome_seen", "true");
  };

  // Check for active impersonation session (super admin only)
  useEffect(() => {
    const checkImpersonation = async () => {
      if (user?.roles?.includes("SUPER_ADMIN")) {
        try {
          const response = await api.get("/admin/impersonation/current");
          if (response.data.active) {
            setImpersonationSession(response.data.session);
          } else {
            setImpersonationSession(null);
          }
        } catch (error) {
          // Silently fail - user may not have access
          setImpersonationSession(null);
        }
      }
    };

    checkImpersonation();
    // Re-check every 30 seconds
    const interval = setInterval(checkImpersonation, 30000);

    return () => clearInterval(interval);
  }, [user]);

  const handleImpersonationEnd = () => {
    setImpersonationSession(null);
  };

  return (
    <AuthGuard>
      {/* Global confetti for celebrations */}
      <GlobalConfetti />

      {/* Welcome modal for first-time users */}
      <WelcomeModal
        isOpen={showWelcome}
        onClose={handleWelcomeClose}
        userName={user?.full_name?.split(" ")[0] || user?.email?.split("@")[0]}
      />

      {impersonationSession && (
        <ImpersonationBanner
          session={impersonationSession}
          onEnd={handleImpersonationEnd}
        />
      )}
      <div className={`flex h-screen overflow-hidden ${impersonationSession ? "pt-12" : ""}`}>
        <Sidebar />
        <div className="flex flex-1 flex-col overflow-hidden">
          <Header />
          <main className="flex-1 overflow-y-auto bg-background p-6">
            <AnimatedPage pageKey={pathname}>
              {children}
            </AnimatedPage>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
