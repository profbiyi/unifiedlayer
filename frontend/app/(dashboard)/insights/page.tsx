"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import Link from "next/link";
import {
  Activity,
  ArrowDown,
  ArrowUp,
  Clock,
  Database,
  Lightbulb,
  PiggyBank,
  TrendingUp,
} from "lucide-react";
import dynamic from "next/dynamic";
import apiClient from "@/lib/api-client";
import { usePipelineRuns } from "@/hooks/queries/usePipelines";
import { useSources } from "@/hooks/queries/useSources";
import { Skeleton } from "@/components/ui/skeleton";

// Lazy-load Recharts so it code-splits out of the initial insights bundle.
const VolumeAreaChart = dynamic(
  () => import("@/components/charts/dashboard-charts").then((m) => m.VolumeAreaChart),
  { ssr: false, loading: () => <Skeleton className="h-[280px] w-full" /> }
);
const SourcesBarChart = dynamic(
  () => import("@/components/charts/dashboard-charts").then((m) => m.SourcesBarChart),
  { ssr: false, loading: () => <Skeleton className="h-[280px] w-full" /> }
);

interface DashboardData {
  summary: {
    headline: string;
    data_synced: number;
    data_trend_percent: number;
    success_rate: number;
    time_saved_hours: number;
    pipeline_runs: number;
  };
  data_health: {
    healthy_pipelines: number;
    stale_pipelines: number;
  };
  connected_sources: Record<string, number>;
}

interface ROIData {
  time_saved: { hours: number };
  money_saved: { gbp: number };
  data_processed: { rows: number; pipeline_runs: number };
  automation: { active_pipelines: number };
  verdict: { status: string; message: string };
}

const SOURCE_LABELS: Record<string, string> = {
  paystack: "Paystack",
  flutterwave: "Flutterwave",
  mpesa: "M-Pesa",
  mtn_momo: "MTN MoMo",
  mono: "Mono",
  stripe: "Stripe",
  postgres: "PostgreSQL",
  mysql: "MySQL",
  mongodb: "MongoDB",
  google_sheets: "Google Sheets",
  whatsapp: "WhatsApp",
};

function fmt(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

export default function InsightsPage() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [roi, setRoi] = useState<ROIData | null>(null);
  const [loading, setLoading] = useState(true);
  const { data: runs } = usePipelineRuns();
  const { data: sources } = useSources();

  useEffect(() => {
    Promise.all([
      apiClient.get("/insights/dashboard").then((r) => r.data).catch(() => null),
      apiClient.get("/insights/roi").then((r) => r.data).catch(() => null),
    ]).then(([d, r]) => {
      setDashboard(d);
      setRoi(r);
      setLoading(false);
    });
  }, []);

  // Rows synced per day (last 14 days) from real run history
  const last14 = Array.from({ length: 14 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (13 - i));
    return date.toISOString().split("T")[0];
  });
  const volumeOverTime = last14.map((date) => {
    const dayRuns =
      runs?.filter(
        (run) =>
          run.status === "completed" &&
          new Date(run.created_at).toISOString().split("T")[0] === date
      ) || [];
    return {
      date: new Date(date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      rows: dayRuns.reduce((sum, r) => sum + (r.rows_written || 0), 0),
    };
  });
  const hasVolume = volumeOverTime.some((d) => d.rows > 0);

  // Connected sources by type (real coverage)
  const bySource = Object.entries(dashboard?.connected_sources || {}).map(
    ([type, count]) => ({
      name: SOURCE_LABELS[type] || type,
      sources: count,
    })
  );

  const hasData = (sources?.length || 0) > 0;

  if (loading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Business Insights</h1>
          <p className="text-muted-foreground">Crunching your numbers...</p>
        </div>
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {[...Array(4)].map((_, i) => (
            <Skeleton key={i} className="h-28" />
          ))}
        </div>
        <Skeleton className="h-[300px]" />
      </div>
    );
  }

  if (!hasData) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Business Insights</h1>
          <p className="text-muted-foreground">
            Connect a source and your insights appear here automatically.
          </p>
        </div>
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-3 py-16 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
              <Lightbulb className="h-6 w-6 text-primary" />
            </div>
            <p className="font-medium">No data to analyse yet</p>
            <p className="max-w-md text-sm text-muted-foreground">
              Once you connect a payment processor, bank, or database, UnifiedLayer
              builds these insights from your data — no spreadsheets, no analyst required.
            </p>
            <Link
              href="/connect"
              className="text-sm font-medium text-primary hover:underline"
            >
              Connect your first source →
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const trend = dashboard?.summary.data_trend_percent ?? 0;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Business Insights</h1>
        <p className="text-muted-foreground">
          {dashboard?.summary.headline || "Your business data, analysed automatically"}
        </p>
      </div>

      {/* Real headline metrics */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Data synced (30d)</CardTitle>
            <Database className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{fmt(dashboard?.summary.data_synced || 0)}</div>
            <p className="flex items-center gap-1 text-xs text-muted-foreground">
              {trend !== 0 && (
                <span className={trend > 0 ? "text-green-600" : "text-red-600"}>
                  {trend > 0 ? <ArrowUp className="inline h-3 w-3" /> : <ArrowDown className="inline h-3 w-3" />}
                  {Math.abs(trend)}%
                </span>
              )}
              rows vs previous month
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Time saved (30d)</CardTitle>
            <Clock className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{roi?.time_saved.hours ?? 0}h</div>
            <p className="text-xs text-muted-foreground">vs manual reconciliation</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Estimated value</CardTitle>
            <PiggyBank className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              £{(roi?.money_saved.gbp ?? 0).toLocaleString()}
            </div>
            <p className="text-xs text-muted-foreground">staff time not spent</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Sync reliability</CardTitle>
            <Activity className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{dashboard?.summary.success_rate ?? 100}%</div>
            <p className="text-xs text-muted-foreground">
              {dashboard?.data_health.healthy_pipelines ?? 0} healthy ·{" "}
              {dashboard?.data_health.stale_pipelines ?? 0} stale
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Real charts from run history */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <TrendingUp className="h-4 w-4 text-primary" />
              Data flowing into your business (14 days)
            </CardTitle>
            <CardDescription>Rows synced per day across all your sources</CardDescription>
          </CardHeader>
          <CardContent>
            {!hasVolume ? (
              <div className="flex h-[280px] items-center justify-center">
                <p className="text-sm text-muted-foreground">No synced rows in the last 14 days</p>
              </div>
            ) : (
              <VolumeAreaChart data={volumeOverTime} />
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Where your data comes from</CardTitle>
            <CardDescription>Connected sources by type</CardDescription>
          </CardHeader>
          <CardContent>
            {bySource.length === 0 ? (
              <div className="flex h-[280px] items-center justify-center">
                <p className="text-sm text-muted-foreground">No sources connected</p>
              </div>
            ) : (
              <SourcesBarChart data={bySource} />
            )}
          </CardContent>
        </Card>
      </div>

      {roi?.verdict?.message && (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="flex items-center gap-3 py-4">
            <Lightbulb className="h-5 w-5 shrink-0 text-primary" />
            <p className="text-sm">
              <span className="font-medium">The bottom line: </span>
              {roi.verdict.message}
            </p>
          </CardContent>
        </Card>
      )}

      <p className="text-center text-xs text-muted-foreground">
        Want a specific number?{" "}
        <Link href="/ask" className="text-primary hover:underline">
          Ask your data a question →
        </Link>
      </p>
    </div>
  );
}
