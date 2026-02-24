"use client";

import { motion } from "framer-motion";
import { ArrowRight, Database, CreditCard, FileSpreadsheet, Building } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { SourceRecommendation } from "@/types/onboarding";
import { cn } from "@/lib/utils";

const sourceIcons: Record<string, React.ComponentType<{ className?: string }>> = {
  stripe: CreditCard,
  paystack: CreditCard,
  xero: FileSpreadsheet,
  quickbooks: FileSpreadsheet,
  postgres: Database,
  mysql: Database,
  mongodb: Database,
  mono: Building,
  truelayer: Building,
};

const sourceColors: Record<string, string> = {
  stripe: "bg-purple-500",
  paystack: "bg-teal-500",
  xero: "bg-blue-500",
  quickbooks: "bg-green-500",
  postgres: "bg-blue-600",
  mysql: "bg-orange-500",
  mongodb: "bg-green-600",
  mono: "bg-yellow-500",
  truelayer: "bg-indigo-500",
};

interface SourceRecommendationsProps {
  recommendations: SourceRecommendation[];
  onSkip?: () => void;
}

export function SourceRecommendations({
  recommendations,
  onSkip,
}: SourceRecommendationsProps) {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">
          Recommended Data Sources
        </h2>
        <p className="text-muted-foreground">
          Based on your role, here are the best data sources to get started with.
        </p>
      </div>

      <div className="space-y-3">
        {recommendations.map((source, index) => {
          const Icon = sourceIcons[source.type] || Database;
          const colorClass = sourceColors[source.type] || "bg-gray-500";

          return (
            <motion.div
              key={source.type}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: index * 0.1 }}
              className="group relative flex items-center gap-4 p-4 rounded-lg border bg-card hover:bg-accent/50 transition-colors"
            >
              <div
                className={cn(
                  "w-12 h-12 rounded-lg flex items-center justify-center text-white shrink-0",
                  colorClass
                )}
              >
                <Icon className="w-6 h-6" />
              </div>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium">{source.name}</h3>
                  {source.priority === 1 && (
                    <Badge variant="secondary" className="text-xs">
                      Recommended
                    </Badge>
                  )}
                </div>
                <p className="text-sm text-muted-foreground">{source.reason}</p>
              </div>

              <Link href={`/sources/new?type=${source.type}`}>
                <Button variant="ghost" size="sm" className="shrink-0">
                  Connect
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
            </motion.div>
          );
        })}
      </div>

      <div className="flex items-center justify-center gap-4 pt-4">
        <Link href="/sources/new">
          <Button variant="outline">Browse All Sources</Button>
        </Link>
        {onSkip && (
          <Button variant="ghost" onClick={onSkip}>
            Skip for now
          </Button>
        )}
      </div>
    </div>
  );
}
