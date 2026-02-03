"use client";

import { Button } from "@/components/ui/button";
import { AlertTriangle } from "lucide-react";

export default function DashboardError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  return (
    <div className="flex flex-1 items-center justify-center p-8">
      <div className="text-center space-y-4">
        <AlertTriangle className="mx-auto h-10 w-10 text-destructive" />
        <h2 className="text-xl font-semibold">Something went wrong</h2>
        <p className="text-sm text-muted-foreground max-w-md">
          An error occurred while loading this page. Please try again.
        </p>
        <div className="flex justify-center gap-3">
          <Button variant="outline" onClick={() => (window.location.href = "/overview")}>
            Go to Overview
          </Button>
          <Button onClick={reset}>Try Again</Button>
        </div>
      </div>
    </div>
  );
}
