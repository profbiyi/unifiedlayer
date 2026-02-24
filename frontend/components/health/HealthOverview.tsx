"use client";

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { Button } from "@/components/ui/button";
import { useHealthOverview, useSourcesHealth, usePipelinesHealth } from "@/hooks/queries/useHealth";
import { HealthBadge, HealthStatus, HealthDot } from "./HealthBadge";
import {
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Activity,
  RefreshCw,
  Database,
  GitBranch,
  ArrowRight,
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";
import { Skeleton } from "@/components/ui/skeleton";

interface HealthOverviewProps {
  showDetails?: boolean;
  className?: string;
}

export function HealthOverview({ showDetails = true, className }: HealthOverviewProps) {
  const { data: overview, isLoading, error, refetch } = useHealthOverview();

  if (isLoading) {
    return <HealthOverviewSkeleton showDetails={showDetails} className={className} />;
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            System Health
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">
            Unable to load health status. Please try again.
          </p>
          <Button variant="outline" size="sm" onClick={() => refetch()} className="mt-2">
            <RefreshCw className="h-4 w-4 mr-2" />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  if (!overview) {
    return null;
  }

  const overallStatus = overview.overall_status as HealthStatus;
  const scoreColor =
    overview.average_score >= 70 ? "text-green-500" :
    overview.average_score >= 40 ? "text-yellow-500" : "text-red-500";

  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Activity className="h-5 w-5" />
            <CardTitle>System Health</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            <HealthBadge status={overallStatus} size="md" />
            <Button variant="ghost" size="icon" onClick={() => refetch()}>
              <RefreshCw className="h-4 w-4" />
            </Button>
          </div>
        </div>
        <CardDescription>
          Monitoring {overview.total_resources} resources
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Health Score */}
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-muted-foreground">Average Health Score</span>
            <span className={cn("font-semibold", scoreColor)}>
              {Math.round(overview.average_score)}%
            </span>
          </div>
          <Progress
            value={overview.average_score}
            className="h-2"
          />
        </div>

        {/* Status Summary */}
        <div className="grid grid-cols-4 gap-2 text-center">
          <div className="p-2 rounded-lg bg-green-500/10">
            <div className="flex items-center justify-center gap-1 text-green-500 font-semibold">
              <CheckCircle2 className="h-4 w-4" />
              {overview.healthy}
            </div>
            <div className="text-xs text-muted-foreground mt-1">Healthy</div>
          </div>
          <div className="p-2 rounded-lg bg-yellow-500/10">
            <div className="flex items-center justify-center gap-1 text-yellow-500 font-semibold">
              <AlertTriangle className="h-4 w-4" />
              {overview.warning}
            </div>
            <div className="text-xs text-muted-foreground mt-1">Warning</div>
          </div>
          <div className="p-2 rounded-lg bg-red-500/10">
            <div className="flex items-center justify-center gap-1 text-red-500 font-semibold">
              <XCircle className="h-4 w-4" />
              {overview.critical}
            </div>
            <div className="text-xs text-muted-foreground mt-1">Critical</div>
          </div>
          <div className="p-2 rounded-lg bg-gray-500/10">
            <div className="flex items-center justify-center gap-1 text-gray-500 font-semibold">
              {overview.unknown}
            </div>
            <div className="text-xs text-muted-foreground mt-1">Unknown</div>
          </div>
        </div>

        {showDetails && (
          <>
            {/* By Type Breakdown */}
            <div className="space-y-2">
              <h4 className="text-sm font-medium">By Resource Type</h4>
              <div className="space-y-2">
                {/* Sources */}
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <Database className="h-4 w-4 text-muted-foreground" />
                    <span>Sources</span>
                  </div>
                  <div className="flex items-center gap-1">
                    {overview.by_type.source.critical > 0 && (
                      <span className="text-red-500 text-xs">{overview.by_type.source.critical} critical</span>
                    )}
                    {overview.by_type.source.warning > 0 && (
                      <span className="text-yellow-500 text-xs">{overview.by_type.source.warning} warning</span>
                    )}
                    <span className="text-muted-foreground text-xs">
                      ({overview.by_type.source.total} total)
                    </span>
                  </div>
                </div>
                {/* Pipelines */}
                <div className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <GitBranch className="h-4 w-4 text-muted-foreground" />
                    <span>Pipelines</span>
                  </div>
                  <div className="flex items-center gap-1">
                    {overview.by_type.pipeline.critical > 0 && (
                      <span className="text-red-500 text-xs">{overview.by_type.pipeline.critical} critical</span>
                    )}
                    {overview.by_type.pipeline.warning > 0 && (
                      <span className="text-yellow-500 text-xs">{overview.by_type.pipeline.warning} warning</span>
                    )}
                    <span className="text-muted-foreground text-xs">
                      ({overview.by_type.pipeline.total} total)
                    </span>
                  </div>
                </div>
              </div>
            </div>

            {/* Critical Issues */}
            {overview.critical_issues && overview.critical_issues.length > 0 && (
              <div className="space-y-2">
                <h4 className="text-sm font-medium text-red-500">Critical Issues</h4>
                <div className="space-y-1">
                  {overview.critical_issues.slice(0, 3).map((item: any, idx: number) => (
                    <div
                      key={idx}
                      className="text-sm p-2 rounded bg-red-500/10 border border-red-500/20"
                    >
                      <span className="font-medium capitalize">{item.resource_type}:</span>{" "}
                      {item.issue?.message || "Critical issue detected"}
                    </div>
                  ))}
                  {overview.critical_issues.length > 3 && (
                    <p className="text-xs text-muted-foreground">
                      +{overview.critical_issues.length - 3} more critical issues
                    </p>
                  )}
                </div>
              </div>
            )}
          </>
        )}

        {/* View All Link */}
        <Link href="/settings/health" className="block">
          <Button variant="outline" className="w-full">
            View All Health Details
            <ArrowRight className="h-4 w-4 ml-2" />
          </Button>
        </Link>
      </CardContent>
    </Card>
  );
}

function HealthOverviewSkeleton({
  showDetails,
  className
}: {
  showDetails?: boolean;
  className?: string;
}) {
  return (
    <Card className={className}>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Skeleton className="h-5 w-5 rounded" />
            <Skeleton className="h-6 w-32" />
          </div>
          <Skeleton className="h-6 w-20 rounded-full" />
        </div>
        <Skeleton className="h-4 w-40 mt-1" />
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-4 w-12" />
          </div>
          <Skeleton className="h-2 w-full" />
        </div>
        <div className="grid grid-cols-4 gap-2">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-16 rounded-lg" />
          ))}
        </div>
        {showDetails && (
          <>
            <div className="space-y-2">
              <Skeleton className="h-4 w-24" />
              <Skeleton className="h-8 w-full" />
              <Skeleton className="h-8 w-full" />
            </div>
          </>
        )}
        <Skeleton className="h-10 w-full" />
      </CardContent>
    </Card>
  );
}

/**
 * Compact health summary for sidebar or header.
 */
export function HealthSummaryCompact({ className }: { className?: string }) {
  const { data: overview, isLoading } = useHealthOverview();

  if (isLoading || !overview) {
    return (
      <div className={cn("flex items-center gap-2", className)}>
        <Skeleton className="h-4 w-4 rounded-full" />
        <Skeleton className="h-4 w-16" />
      </div>
    );
  }

  const overallStatus = overview.overall_status as HealthStatus;

  return (
    <Link href="/settings/health">
      <div className={cn("flex items-center gap-2 hover:opacity-80 transition", className)}>
        <HealthDot status={overallStatus} size="md" />
        <span className="text-sm">
          {overview.healthy}/{overview.total_resources} healthy
        </span>
      </div>
    </Link>
  );
}

export default HealthOverview;
