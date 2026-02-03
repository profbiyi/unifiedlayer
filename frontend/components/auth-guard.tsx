"use client";

import { useCurrentUser } from "@/hooks/queries/useAuth";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

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

  // Show nothing while loading or if not authenticated
  if (isLoading || !user) {
    return null;
  }

  return <>{children}</>;
}
