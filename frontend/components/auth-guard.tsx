"use client";

import { useCurrentUser } from "@/hooks/queries/useAuth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { Loader2, Database } from "lucide-react";

/**
 * AuthGuard component - protects routes that require authentication.
 *
 * Uses useCurrentUser to verify authentication via HTTPOnly cookie.
 * If user is not authenticated, redirects to login page.
 */
export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { data: user, isLoading, error } = useCurrentUser();

  useEffect(() => {
    // Redirect to login if authentication fails
    if (!isLoading && (error || !user)) {
      router.push("/login");
    }
  }, [user, isLoading, error, router]);

  // Branded loading state while the auth check resolves — a blank screen
  // here reads as "slow/broken"; a spinner reads as "loading fast".
  if (isLoading) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-3">
        <div className="flex items-center gap-2 text-lg font-bold">
          <Database className="h-6 w-6 text-primary" />
          UnifiedLayer
        </div>
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Not authenticated — the effect above redirects to /login; render nothing.
  if (!user) {
    return null;
  }

  return <>{children}</>;
}
