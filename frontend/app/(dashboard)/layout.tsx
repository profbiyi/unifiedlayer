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
import { Menu } from "lucide-react";

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
  /** Controls the mobile sidebar drawer */
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);

  // Close the mobile drawer whenever the route changes
  useEffect(() => {
    setMobileSidebarOpen(false);
  }, [pathname]);

  // Show welcome modal for first-time users
  useEffect(() => {
    if (user && !localStorage.getItem("unifiedlayer_welcome_seen")) {
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
          setImpersonationSession(null);
        }
      }
    };

    checkImpersonation();
    const interval = setInterval(checkImpersonation, 30000);
    return () => clearInterval(interval);
  }, [user]);

  const handleImpersonationEnd = () => {
    setImpersonationSession(null);
  };

  return (
    <AuthGuard>
      <GlobalConfetti />

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
        {/*
         * Sidebar:
         * - Desktop (md+): always rendered as a fixed left column
         * - Mobile (<md): hidden by default, shown as an overlay drawer
         */}
        <Sidebar
          isOpen={mobileSidebarOpen}
          onClose={() => setMobileSidebarOpen(false)}
        />

        {/* Main content area — takes full width on mobile, shrinks on desktop */}
        <div className="flex flex-1 flex-col overflow-hidden min-w-0">
          {/*
           * Mobile-only top bar: shows hamburger + app name.
           * Replaces the sidebar brand area on small screens.
           */}
          <div className="flex items-center gap-3 h-14 border-b bg-card px-4 md:hidden">
            <button
              onClick={() => setMobileSidebarOpen(true)}
              className="text-muted-foreground hover:text-foreground focus:outline-none"
              aria-label="Open navigation menu"
            >
              <Menu className="h-5 w-5" />
            </button>
            <span className="text-base font-bold">UnifiedLayer</span>
          </div>

          {/* Desktop header — hidden on mobile (Header has its own border-b) */}
          <div className="hidden md:block">
            <Header />
          </div>

          <main className="flex-1 overflow-y-auto bg-background p-4 md:p-6">
            <AnimatedPage pageKey={pathname}>
              {children}
            </AnimatedPage>
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
