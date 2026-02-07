"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { X, Eye, Building2, Clock } from "lucide-react";
import api from "@/lib/api-client";
import { useToast } from "@/hooks/use-toast";

interface ImpersonationSession {
  target_org_id: number;
  target_org_name: string;
  target_org_slug: string;
  target_org_logo: string | null;
  started_at: string;
  expires_at: string;
}

interface ImpersonationBannerProps {
  session: ImpersonationSession;
  onEnd: () => void;
}

export default function ImpersonationBanner({ session, onEnd }: ImpersonationBannerProps) {
  const [timeRemaining, setTimeRemaining] = useState<string>("");
  const [isEnding, setIsEnding] = useState(false);
  const { toast } = useToast();

  useEffect(() => {
    const calculateTimeRemaining = () => {
      const expiresAt = new Date(session.expires_at);
      const now = new Date();
      const diffMs = expiresAt.getTime() - now.getTime();

      if (diffMs <= 0) {
        setTimeRemaining("Expired");
        return;
      }

      const minutes = Math.floor(diffMs / 60000);
      const seconds = Math.floor((diffMs % 60000) / 1000);
      setTimeRemaining(`${minutes}m ${seconds}s`);
    };

    calculateTimeRemaining();
    const interval = setInterval(calculateTimeRemaining, 1000);

    return () => clearInterval(interval);
  }, [session.expires_at]);

  const handleStopImpersonation = async () => {
    setIsEnding(true);
    try {
      await api.post("/admin/stop-impersonate");
      toast({
        title: "Impersonation Ended",
        description: "You are now viewing as yourself.",
      });
      onEnd();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to end impersonation",
        variant: "destructive",
      });
    } finally {
      setIsEnding(false);
    }
  };

  const getOrgInitial = (name: string) => {
    return name.charAt(0).toUpperCase();
  };

  return (
    <div className="fixed top-0 left-0 right-0 z-50 bg-amber-500 text-amber-950 px-4 py-2 shadow-md">
      <div className="max-w-screen-2xl mx-auto flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Eye className="h-5 w-5" />
          <span className="font-semibold">Viewing as:</span>

          <div className="flex items-center gap-2 bg-amber-400/50 rounded-full px-3 py-1">
            {session.target_org_logo ? (
              <img
                src={session.target_org_logo}
                alt={session.target_org_name}
                className="h-5 w-5 rounded-full"
              />
            ) : (
              <div className="h-5 w-5 rounded-full bg-amber-700 text-amber-100 flex items-center justify-center text-xs font-bold">
                {getOrgInitial(session.target_org_name)}
              </div>
            )}
            <span className="font-medium">{session.target_org_name}</span>
          </div>

          <div className="flex items-center gap-1 text-amber-800 text-sm ml-2">
            <Clock className="h-4 w-4" />
            <span>Expires in: {timeRemaining}</span>
          </div>

          <span className="text-amber-700 text-sm ml-4 hidden md:inline">
            (READ-ONLY access - all actions are logged)
          </span>
        </div>

        <Button
          variant="outline"
          size="sm"
          onClick={handleStopImpersonation}
          disabled={isEnding}
          className="bg-amber-600 text-white hover:bg-amber-700 border-amber-600 hover:border-amber-700"
        >
          <X className="h-4 w-4 mr-1" />
          {isEnding ? "Ending..." : "Stop Impersonating"}
        </Button>
      </div>
    </div>
  );
}
