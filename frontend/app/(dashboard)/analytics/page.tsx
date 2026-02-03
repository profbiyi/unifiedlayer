"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  TrendingUp,
  TrendingDown,
  Database,
  Zap,
  Clock,
  CheckCircle2,
  XCircle,
  Activity,
} from "lucide-react";
import apiClient from "@/lib/api-client";

interface OverviewData {
  pipelines: { total: number; active: number };
  runs: { total: number; successful: number; failed: number; success_rate: number };
  data: { rows_synced: number; avg_duration_seconds: number };
  connectors: { sources: number; destinations: number };
}

interface TimelineEntry {
  date: string;
  completed: number;
  failed: number;
  total: number;
}

interface PipelinePerformance {
  pipeline_id: string;
  pipeline_name: string;
  total_runs: number;
  successful: number;
  failed: number;
  success_rate: number;
  total_rows_synced: number;
  avg_duration_seconds: number;
  is_active: boolean;
  schedule: string | null;
}

interface SourceBreakdown {
  source_type: string;
  pipeline_count: number;
  total_rows_synced: number;
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

function formatDuration(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`;
  return `${(seconds / 3600).toFixed(1)}h`;
}

export default function AnalyticsPage() {
  const [overview, setOverview] = useState<OverviewData | null>(null);
  const [timeline, setTimeline] = useState<TimelineEntry[]>([]);
  const [pipelines, setPipelines] = useState<PipelinePerformance[]>([]);
  const [sources, setSources] = useState<SourceBreakdown[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [overviewRes, timelineRes, pipelinesRes, sourcesRes] = await Promise.all([
          apiClient.get("/analytics/overview"),
          apiClient.get("/analytics/runs/timeline?days=30"),
          apiClient.get("/analytics/pipelines/performance"),
          apiClient.get("/analytics/sources/breakdown"),
        ]);
        setOverview(overviewRes.data);
        setTimeline(timelineRes.data.timeline);
        setPipelines(pipelinesRes.data.pipelines);
        setSources(sourcesRes.data.sources);
      } catch (err) {
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Activity className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Analytics</h1>
        <p className="text-muted-foreground">
          Insights from your data pipelines over the last 30 days.
        </p>
      </div>

      {/* KPI Cards */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Rows Synced</CardTitle>
            <Database className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {overview ? formatNumber(overview.data.rows_synced) : "0"}
            </div>
            <p className="text-xs text-muted-foreground">Last 30 days</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Success Rate</CardTitle>
            {overview && overview.runs.success_rate >= 95 ? (
              <TrendingUp className="h-4 w-4 text-green-600" />
            ) : (
              <TrendingDown className="h-4 w-4 text-red-600" />
            )}
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {overview?.runs.success_rate ?? 0}%
            </div>
            <p className="text-xs text-muted-foreground">
              {overview?.runs.successful ?? 0} of {overview?.runs.total ?? 0} runs
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Total Runs</CardTitle>
            <Zap className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {overview?.runs.total ?? 0}
            </div>
            <p className="text-xs text-muted-foreground">
              {overview?.pipelines.active ?? 0} active pipelines
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Avg Duration</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {overview ? formatDuration(overview.data.avg_duration_seconds) : "0s"}
            </div>
            <p className="text-xs text-muted-foreground">Per pipeline run</p>
          </CardContent>
        </Card>
      </div>

      {/* Run Timeline Chart (Simple bar representation) */}
      <Card>
        <CardHeader>
          <CardTitle>Pipeline Runs</CardTitle>
          <CardDescription>Daily pipeline execution over the last 30 days</CardDescription>
        </CardHeader>
        <CardContent>
          {timeline.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-8">
              No pipeline runs in the selected period.
            </p>
          ) : (
            <div className="flex items-end gap-1 h-40">
              {timeline.map((day) => {
                const maxTotal = Math.max(...timeline.map((t) => t.total), 1);
                const height = (day.total / maxTotal) * 100;
                const failPercent = day.total > 0 ? (day.failed / day.total) * 100 : 0;
                return (
                  <div
                    key={day.date}
                    className="flex-1 flex flex-col justify-end group relative"
                  >
                    <div
                      className="w-full rounded-t transition-all hover:opacity-80"
                      style={{
                        height: `${height}%`,
                        background: failPercent > 0
                          ? `linear-gradient(to top, hsl(var(--destructive)) ${failPercent}%, hsl(var(--primary)) ${failPercent}%)`
                          : "hsl(var(--primary))",
                        minHeight: day.total > 0 ? "4px" : "0",
                      }}
                    />
                    <div className="absolute -top-8 left-1/2 -translate-x-1/2 hidden group-hover:block bg-popover border rounded px-2 py-1 text-xs whitespace-nowrap shadow-md z-10">
                      {day.date}: {day.completed} ok, {day.failed} failed
                    </div>
                  </div>
                );
              })}
            </div>
          )}
          <div className="flex items-center gap-4 mt-4 text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <div className="h-3 w-3 rounded-sm bg-primary" />
              Successful
            </div>
            <div className="flex items-center gap-1">
              <div className="h-3 w-3 rounded-sm bg-destructive" />
              Failed
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid gap-6 md:grid-cols-2">
        {/* Pipeline Performance Table */}
        <Card>
          <CardHeader>
            <CardTitle>Pipeline Performance</CardTitle>
            <CardDescription>Success rate and throughput per pipeline</CardDescription>
          </CardHeader>
          <CardContent>
            {pipelines.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No pipelines found.
              </p>
            ) : (
              <div className="space-y-3">
                {pipelines.slice(0, 8).map((p) => (
                  <div key={p.pipeline_id} className="flex items-center justify-between">
                    <div className="flex items-center gap-2 min-w-0">
                      {p.success_rate >= 95 ? (
                        <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0" />
                      ) : p.success_rate >= 80 ? (
                        <CheckCircle2 className="h-4 w-4 text-yellow-600 shrink-0" />
                      ) : (
                        <XCircle className="h-4 w-4 text-red-600 shrink-0" />
                      )}
                      <span className="text-sm truncate">{p.pipeline_name}</span>
                    </div>
                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-xs text-muted-foreground">
                        {formatNumber(p.total_rows_synced)} rows
                      </span>
                      <Badge
                        variant={p.success_rate >= 95 ? "default" : p.success_rate >= 80 ? "secondary" : "destructive"}
                        className="text-xs"
                      >
                        {p.success_rate}%
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* Source Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle>Data by Source</CardTitle>
            <CardDescription>Rows synced per connector type</CardDescription>
          </CardHeader>
          <CardContent>
            {sources.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-4">
                No data synced yet.
              </p>
            ) : (
              <div className="space-y-4">
                {sources.map((s) => {
                  const maxRows = Math.max(...sources.map((x) => x.total_rows_synced), 1);
                  const percent = (s.total_rows_synced / maxRows) * 100;
                  return (
                    <div key={s.source_type}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium capitalize">
                          {s.source_type.replace("_", " ")}
                        </span>
                        <span className="text-sm text-muted-foreground">
                          {formatNumber(s.total_rows_synced)} rows
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-muted overflow-hidden">
                        <div
                          className="h-full rounded-full bg-primary transition-all"
                          style={{ width: `${percent}%` }}
                        />
                      </div>
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
