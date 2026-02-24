"use client";

import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Workflow, Database, HardDrive, Activity, Loader2, CheckCircle2, XCircle, Clock, TrendingUp, Sparkles, ArrowRight, Check } from "lucide-react";
import { usePipelines } from "@/hooks/queries/usePipelines";
import { useSources } from "@/hooks/queries/useSources";
import { useDestinations } from "@/hooks/queries/useDestinations";
import { usePipelineRuns } from "@/hooks/queries/usePipelines";
import { useOverviewMetrics } from "@/hooks/queries/useMetrics";
import { useTemplates } from "@/hooks/queries/useTemplates";
import { HealthOverview } from "@/components/health/HealthOverview";
import { Badge } from "@/components/ui/badge";
import { StatsCardSkeleton } from "@/components/skeletons/StatsCardSkeleton";
import { Skeleton } from "@/components/ui/skeleton";
import { LineChart, Line, PieChart, Pie, Cell, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import TemplateCard from "@/components/templates/TemplateCard";
import Link from "next/link";

export default function OverviewPage() {
  const { data: pipelines, isLoading: pipelinesLoading } = usePipelines();
  const { data: sources, isLoading: sourcesLoading } = useSources();
  const { data: destinations, isLoading: destinationsLoading } = useDestinations();
  const { data: runs, isLoading: runsLoading } = usePipelineRuns();
  const { data: metrics, isLoading: metricsLoading } = useOverviewMetrics("24h");
  const { data: templates } = useTemplates();

  const activeRuns = runs?.filter((run) => run.status === "running") || [];

  // Prepare run status distribution data
  const statusCounts = runs?.reduce((acc, run) => {
    const status = run.status || "unknown";
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>) || {};

  const statusData = Object.entries(statusCounts).map(([status, count]) => ({
    name: status.charAt(0).toUpperCase() + status.slice(1),
    value: count,
  }));

  const STATUS_COLORS = {
    Completed: "#10b981",
    Failed: "#ef4444",
    Running: "#3b82f6",
    Pending: "#f59e0b",
  };

  // Prepare runs over time data (last 7 days)
  const last7Days = Array.from({ length: 7 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (6 - i));
    return date.toISOString().split("T")[0];
  });

  const runsOverTime = last7Days.map((date) => {
    const dayRuns = runs?.filter((run) => {
      const runDate = new Date(run.created_at).toISOString().split("T")[0];
      return runDate === date;
    }) || [];

    return {
      date: new Date(date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      runs: dayRuns.length,
      completed: dayRuns.filter((r) => r.status === "completed").length,
      failed: dayRuns.filter((r) => r.status === "failed").length,
    };
  });

  // Get recent runs
  const recentRuns = runs?.slice(0, 5) || [];

  const resourceCountsLoading = pipelinesLoading || sourcesLoading || destinationsLoading || runsLoading;

  const stats = [
    {
      title: "Total Pipelines",
      value: pipelines?.length || 0,
      icon: Workflow,
      description: pipelines?.length === 1 ? "Active data pipeline" : "Active data pipelines",
    },
    {
      title: "Data Sources",
      value: sources?.length || 0,
      icon: Database,
      description: sources?.length === 1 ? "Connected source" : "Connected sources",
    },
    {
      title: "Destinations",
      value: destinations?.length || 0,
      icon: HardDrive,
      description: destinations?.length === 1 ? "Active destination" : "Active destinations",
    },
    {
      title: "Active Runs",
      value: activeRuns.length,
      icon: Activity,
      description: "Currently running",
    },
  ];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Overview</h1>
        <p className="text-muted-foreground">
          Welcome to your data integration platform
        </p>
      </div>

      {/* Quick Start Banner */}
      <Card className="bg-gradient-to-r from-primary/10 via-primary/5 to-background border-primary/20">
        <CardContent className="flex flex-col sm:flex-row items-center justify-between gap-4 py-6">
          <div className="flex items-center gap-4">
            <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-primary/20">
              <Sparkles className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h2 className="text-lg font-semibold">Get Started in 60 Seconds</h2>
              <p className="text-sm text-muted-foreground">
                Deploy a pre-built sync pipeline with one click
              </p>
            </div>
          </div>
          <Link href="/templates">
            <Button>
              Browse Templates
              <ArrowRight className="ml-2 h-4 w-4" />
            </Button>
          </Link>
        </CardContent>
      </Card>

      {/* Featured Templates */}
      {templates && templates.length > 0 && (
        <div>
          <div className="flex items-center justify-between mb-3">
            <h2 className="text-lg font-semibold">Popular Templates</h2>
            <Link href="/templates" className="text-sm text-primary hover:underline">
              View all
            </Link>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {templates.slice(0, 3).map((t) => (
              <TemplateCard key={t.id} template={t} compact />
            ))}
          </div>
        </div>
      )}

      {/* Getting Started Checklist */}
      {((sources?.length || 0) < 1 || (pipelines?.length || 0) < 1) && (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Getting Started</CardTitle>
            <CardDescription>Complete these steps to set up your first pipeline</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              <div className="flex items-center gap-3">
                {(sources?.length || 0) >= 1 ? (
                  <Check className="h-5 w-5 text-green-600" />
                ) : (
                  <div className="h-5 w-5 rounded-full border-2 border-muted-foreground/30" />
                )}
                <span className="text-sm">
                  {(sources?.length || 0) >= 1 ? (
                    "Data source created"
                  ) : (
                    <Link href="/sources/new" className="text-primary hover:underline">
                      Create a data source
                    </Link>
                  )}
                </span>
              </div>
              <div className="flex items-center gap-3">
                {(destinations?.length || 0) >= 1 ? (
                  <Check className="h-5 w-5 text-green-600" />
                ) : (
                  <div className="h-5 w-5 rounded-full border-2 border-muted-foreground/30" />
                )}
                <span className="text-sm">
                  {(destinations?.length || 0) >= 1 ? (
                    "Destination added"
                  ) : (
                    <Link href="/destinations/new" className="text-primary hover:underline">
                      Add a destination
                    </Link>
                  )}
                </span>
              </div>
              <div className="flex items-center gap-3">
                {(pipelines?.length || 0) >= 1 ? (
                  <Check className="h-5 w-5 text-green-600" />
                ) : (
                  <div className="h-5 w-5 rounded-full border-2 border-muted-foreground/30" />
                )}
                <span className="text-sm">
                  {(pipelines?.length || 0) >= 1 ? (
                    "First pipeline running"
                  ) : (
                    <Link href="/pipelines/new" className="text-primary hover:underline">
                      Run your first pipeline
                    </Link>
                  )}
                </span>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Performance Metrics (Last 24h) */}
      {metricsLoading ? (
        <StatsCardSkeleton count={4} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {`${metrics?.success_rate || 0}%`}
              </div>
              <p className="text-xs text-muted-foreground">
                Last 24 hours
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Avg Duration</CardTitle>
              <Clock className="h-4 w-4 text-blue-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {`${metrics?.avg_duration_seconds?.toFixed(1) || 0}s`}
              </div>
              <p className="text-xs text-muted-foreground">
                Per pipeline run
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
              <Activity className="h-4 w-4 text-purple-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {metrics?.total_runs || 0}
              </div>
              <p className="text-xs text-muted-foreground">
                {metrics?.failed_runs || 0} failed
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Records Processed</CardTitle>
              <TrendingUp className="h-4 w-4 text-emerald-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(metrics?.total_rows_processed || 0).toLocaleString()}
              </div>
              <p className="text-xs text-muted-foreground">
                Last 24 hours
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Resource Counts */}
      {resourceCountsLoading ? (
        <StatsCardSkeleton count={4} />
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          {stats.map((stat) => {
            const Icon = stat.icon;
            return (
              <Card key={stat.title}>
                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                  <CardTitle className="text-sm font-medium">
                    {stat.title}
                  </CardTitle>
                  <Icon className="h-4 w-4 text-muted-foreground" />
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">{stat.value}</div>
                  <p className="text-xs text-muted-foreground">
                    {stat.description}
                  </p>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* System Health Overview */}
      <HealthOverview />

      <div className="grid gap-4 md:grid-cols-2">
        {/* Pipeline Runs Over Time */}
        <Card className="col-span-2">
          <CardHeader>
            <CardTitle>Pipeline Runs (Last 7 Days)</CardTitle>
            <CardDescription>Overview of successful and failed runs</CardDescription>
          </CardHeader>
          <CardContent>
            {runsLoading ? (
              <div className="h-[300px] space-y-4">
                <div className="flex justify-between">
                  <Skeleton className="h-4 w-16" />
                  <Skeleton className="h-4 w-24" />
                </div>
                <Skeleton className="h-[260px] w-full" />
              </div>
            ) : runsOverTime.every((d) => d.runs === 0) ? (
              <div className="flex items-center justify-center h-[300px]">
                <p className="text-sm text-muted-foreground">No pipeline runs yet</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={300}>
                <LineChart data={runsOverTime}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="completed" stroke="#10b981" strokeWidth={2} name="Completed" />
                  <Line type="monotone" dataKey="failed" stroke="#ef4444" strokeWidth={2} name="Failed" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Run Status Distribution */}
        <Card>
          <CardHeader>
            <CardTitle>Run Status Distribution</CardTitle>
            <CardDescription>Current status breakdown</CardDescription>
          </CardHeader>
          <CardContent>
            {runsLoading ? (
              <div className="flex items-center justify-center h-[250px]">
                <Skeleton className="h-40 w-40 rounded-full" />
              </div>
            ) : statusData.length === 0 ? (
              <div className="flex items-center justify-center h-[250px]">
                <p className="text-sm text-muted-foreground">No runs to display</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={250}>
                <PieChart>
                  <Pie
                    data={statusData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
                    outerRadius={80}
                    fill="#8884d8"
                    dataKey="value"
                  >
                    {statusData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={STATUS_COLORS[entry.name as keyof typeof STATUS_COLORS] || "#6b7280"} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        {/* Recent Pipeline Runs */}
        <Card>
          <CardHeader>
            <CardTitle>Recent Runs</CardTitle>
            <CardDescription>Latest pipeline executions</CardDescription>
          </CardHeader>
          <CardContent>
            {runsLoading ? (
              <div className="space-y-4">
                {[...Array(5)].map((_, i) => (
                  <div key={i} className="flex items-center justify-between border-b pb-3 last:border-0">
                    <div className="flex items-center gap-3">
                      <Skeleton className="h-4 w-4 rounded-full" />
                      <div className="space-y-1">
                        <Skeleton className="h-4 w-20" />
                        <Skeleton className="h-3 w-28" />
                      </div>
                    </div>
                    <Skeleton className="h-5 w-16 rounded-full" />
                  </div>
                ))}
              </div>
            ) : recentRuns.length === 0 ? (
              <div className="flex items-center justify-center h-[250px]">
                <p className="text-sm text-muted-foreground">No recent runs</p>
              </div>
            ) : (
              <div className="space-y-4">
                {recentRuns.map((run) => {
                  const getStatusIcon = (status: string) => {
                    switch (status) {
                      case "completed":
                        return <CheckCircle2 className="h-4 w-4 text-green-600" />;
                      case "failed":
                        return <XCircle className="h-4 w-4 text-red-600" />;
                      case "running":
                        return <Activity className="h-4 w-4 text-blue-600 animate-pulse" />;
                      default:
                        return <Clock className="h-4 w-4 text-yellow-600" />;
                    }
                  };

                  const getStatusBadgeVariant = (status: string) => {
                    switch (status) {
                      case "completed":
                        return "default";
                      case "failed":
                        return "destructive";
                      default:
                        return "secondary";
                    }
                  };

                  return (
                    <div key={run.id} className="flex items-center justify-between border-b pb-3 last:border-0">
                      <div className="flex items-center gap-3">
                        {getStatusIcon(run.status)}
                        <div>
                          <p className="text-sm font-medium">Run #{run.id}</p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(run.created_at).toLocaleString()}
                          </p>
                        </div>
                      </div>
                      <Badge variant={getStatusBadgeVariant(run.status)}>
                        {run.status}
                      </Badge>
                    </div>
                  );
                })}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
