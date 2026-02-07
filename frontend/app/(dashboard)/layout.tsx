"use client";

import { useEffect, useState } from "react";
import Sidebar from "@/components/layout/sidebar";
import Header from "@/components/layout/header";
import AuthGuard from "@/components/auth-guard";
import ImpersonationBanner from "@/components/layout/ImpersonationBanner";
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
  const { data: user } = useCurrentUser();
  const [impersonationSession, setImpersonationSession] = useState<ImpersonationSession | null>(null);

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
            {children}
          </main>
        </div>
      </div>
    </AuthGuard>
  );
}
