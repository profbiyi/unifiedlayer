"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Database,
  Activity,
  CheckCircle2,
  XCircle,
  Clock,
  TrendingUp,
  Sparkles,
  ArrowRight,
  Check,
  Lightbulb,
} from "lucide-react";
import { usePipelines } from "@/hooks/queries/usePipelines";
import { useSources } from "@/hooks/queries/useSources";
import { useDestinations } from "@/hooks/queries/useDestinations";
import { usePipelineRuns } from "@/hooks/queries/usePipelines";
import { useOverviewMetrics } from "@/hooks/queries/useMetrics";
import { useTemplates } from "@/hooks/queries/useTemplates";
import QuickConnect from "@/components/dashboard/QuickConnect";
import { Badge } from "@/components/ui/badge";
import { StatsCardSkeleton } from "@/components/skeletons/StatsCardSkeleton";
import { Skeleton } from "@/components/ui/skeleton";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from "recharts";
import TemplateCard from "@/components/templates/TemplateCard";
import Link from "next/link";

// Source types that unlock revenue/cash-flow insights
const PAYMENT_SOURCE_TYPES = new Set([
  "paystack",
  "flutterwave",
  "mpesa",
  "mtn_momo",
  "stripe",
  "mono",
  "gocardless",
]);

const SUGGESTED_QUESTIONS = [
  "How many rows did we sync this week?",
  "Which pipeline failed most recently?",
  "What does our sync volume look like by day?",
];

function relativeTime(iso: string): string {
  const diffMs = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diffMs / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

function AskBar() {
  const router = useRouter();
  const [question, setQuestion] = useState("");

  const ask = (q: string) => {
    if (!q.trim()) return;
    router.push(`/ask?q=${encodeURIComponent(q.trim())}`);
  };

  return (
    <Card className="border-primary/30 bg-primary/5">
      <CardContent className="pt-6">
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            ask(question);
          }}
        >
          <div className="relative flex-1">
            <Sparkles className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-primary" />
            <Input
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask anything about your data — plain English, no SQL"
              className="bg-background pl-9"
            />
          </div>
          <Button type="submit">Ask</Button>
        </form>
        <div className="mt-3 flex flex-wrap gap-2">
          {SUGGESTED_QUESTIONS.map((q) => (
            <button
              key={q}
              type="button"
              onClick={() => ask(q)}
              className="rounded-full border bg-background px-3 py-1 text-xs text-muted-foreground transition-colors hover:border-primary/50 hover:text-foreground"
            >
              {q}
            </button>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export default function OverviewPage() {
  const { data: pipelines, isLoading: pipelinesLoading } = usePipelines();
  const { data: sources, isLoading: sourcesLoading } = useSources();
  const { data: destinations } = useDestinations();
  const { data: runs, isLoading: runsLoading } = usePipelineRuns();
  const { data: metrics, isLoading: metricsLoading } = useOverviewMetrics("24h");
  const { data: templates } = useTemplates();

  const stillLoading = pipelinesLoading || sourcesLoading;
  const isNewUser =
    !stillLoading && ((sources?.length || 0) < 1 || (pipelines?.length || 0) < 1);

  // Business tiles
  const latestCompleted = runs?.find((r) => r.status === "completed");
  const freshness = latestCompleted ? relativeTime(latestCompleted.created_at) : "—";
  const hasPaymentSource = sources?.some((s) =>
    PAYMENT_SOURCE_TYPES.has((s.source_type || "").toLowerCase())
  );

  // 7-day chart data
  const last7Days = Array.from({ length: 7 }, (_, i) => {
    const date = new Date();
    date.setDate(date.getDate() - (6 - i));
    return date.toISOString().split("T")[0];
  });
  const runsOverTime = last7Days.map((date) => {
    const dayRuns =
      runs?.filter(
        (run) => new Date(run.created_at).toISOString().split("T")[0] === date
      ) || [];
    return {
      date: new Date(date).toLocaleDateString("en-US", { month: "short", day: "numeric" }),
      completed: dayRuns.filter((r) => r.status === "completed").length,
      failed: dayRuns.filter((r) => r.status === "failed").length,
    };
  });

  const recentRuns = runs?.slice(0, 5) || [];

  // ── New-user view: onboarding replaces the dashboard, not stacks on it ──
  if (isNewUser) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Welcome to UnifiedLayer</h1>
          <p className="text-muted-foreground">
            Connect your first source and your business data starts flowing into one place.
          </p>
        </div>

        <QuickConnect />

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Three steps to your first sync</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {[
                {
                  done: (sources?.length || 0) >= 1,
                  doneLabel: "Data source connected",
                  href: "/sources/new",
                  label: "Connect a data source",
                },
                {
                  done: (destinations?.length || 0) >= 1,
                  doneLabel: "Destination added",
                  href: "/destinations/new",
                  label: "Add a destination",
                },
                {
                  done: (pipelines?.length || 0) >= 1,
                  doneLabel: "First pipeline running",
                  href: "/pipelines/new",
                  label: "Run your first pipeline",
                },
              ].map((step) => (
                <div key={step.label} className="flex items-center gap-3">
                  {step.done ? (
                    <Check className="h-5 w-5 text-green-600" />
                  ) : (
                    <div className="h-5 w-5 rounded-full border-2 border-muted-foreground/30" />
                  )}
                  <span className="text-sm">
                    {step.done ? (
                      step.doneLabel
                    ) : (
                      <Link href={step.href} className="text-primary hover:underline">
                        {step.label}
                      </Link>
                    )}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        {templates && templates.length > 0 && (
          <div>
            <div className="flex items-center justify-between mb-3">
              <h2 className="text-lg font-semibold">Start from a template</h2>
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
      </div>
    );
  }

  // ── Working dashboard: AI front and center, business numbers, one chart ──
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Overview</h1>
        <p className="text-muted-foreground">Your business data, at a glance</p>
      </div>

      <AskBar />

      {/* Business tiles */}
      {metricsLoading || runsLoading ? (
        <StatsCardSkeleton count={4} />
      ) : (
        <div className="grid gap-4 grid-cols-1 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Rows synced</CardTitle>
              <TrendingUp className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">
                {(metrics?.total_rows_processed || 0).toLocaleString()}
              </div>
              <p className="text-xs text-muted-foreground">Last 24 hours</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Sync health</CardTitle>
              <CheckCircle2 className="h-4 w-4 text-green-600" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{`${metrics?.success_rate ?? 100}%`}</div>
              <p className="text-xs text-muted-foreground">
                {metrics?.failed_runs
                  ? `${metrics.failed_runs} failed in 24h`
                  : "No failures in 24h"}
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Data freshness</CardTitle>
              <Clock className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{freshness}</div>
              <p className="text-xs text-muted-foreground">Last successful sync</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Connected sources</CardTitle>
              <Database className="h-4 w-4 text-primary" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{sources?.length || 0}</div>
              <p className="text-xs text-muted-foreground">
                feeding {pipelines?.length || 0} pipeline{(pipelines?.length || 0) === 1 ? "" : "s"}
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Insights bridge — shown when payment data is connected */}
      {hasPaymentSource && (
        <Link href="/insights" className="block">
          <Card className="transition-colors hover:border-primary/50">
            <CardContent className="flex items-center justify-between py-4">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <Lightbulb className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-sm font-medium">Business insights are ready</p>
                  <p className="text-xs text-muted-foreground">
                    Revenue trends and payment health from your connected payment sources
                  </p>
                </div>
              </div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </CardContent>
          </Card>
        </Link>
      )}

      {/* One chart + recent activity */}
      <div className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Data flowing (last 7 days)</CardTitle>
            <CardDescription>Completed and failed syncs per day</CardDescription>
          </CardHeader>
          <CardContent>
            {runsLoading ? (
              <Skeleton className="h-[260px] w-full" />
            ) : runsOverTime.every((d) => d.completed === 0 && d.failed === 0) ? (
              <div className="flex items-center justify-center h-[260px]">
                <p className="text-sm text-muted-foreground">No syncs in the last 7 days</p>
              </div>
            ) : (
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={runsOverTime}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="date" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="completed" stroke="#10b981" strokeWidth={2} name="Completed" />
                  <Line type="monotone" dataKey="failed" stroke="#ef4444" strokeWidth={2} name="Failed" />
                </LineChart>
              </ResponsiveContainer>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
            <CardDescription>Latest syncs</CardDescription>
          </CardHeader>
          <CardContent>
            {runsLoading ? (
              <div className="space-y-4">
                {[...Array(5)].map((_, i) => (
                  <Skeleton key={i} className="h-8 w-full" />
                ))}
              </div>
            ) : recentRuns.length === 0 ? (
              <div className="flex items-center justify-center h-[200px]">
                <p className="text-sm text-muted-foreground">No recent syncs</p>
              </div>
            ) : (
              <div className="space-y-3">
                {recentRuns.map((run) => {
                  const icon =
                    run.status === "completed" ? (
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-green-600" />
                    ) : run.status === "failed" ? (
                      <XCircle className="h-4 w-4 shrink-0 text-red-600" />
                    ) : run.status === "running" ? (
                      <Activity className="h-4 w-4 shrink-0 animate-pulse text-blue-600" />
                    ) : (
                      <Clock className="h-4 w-4 shrink-0 text-yellow-600" />
                    );
                  return (
                    <div key={run.id} className="flex items-center justify-between gap-2">
                      <div className="flex min-w-0 items-center gap-2">
                        {icon}
                        <span className="truncate text-xs text-muted-foreground">
                          {relativeTime(run.created_at)}
                        </span>
                      </div>
                      <Badge
                        variant={
                          run.status === "completed"
                            ? "default"
                            : run.status === "failed"
                            ? "destructive"
                            : "secondary"
                        }
                        className="text-[10px]"
                      >
                        {run.status}
                      </Badge>
                    </div>
                  );
                })}
                <Link
                  href="/runs"
                  className="block pt-1 text-xs text-primary hover:underline"
                >
                  View all runs →
                </Link>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Gentle growth nudge for orgs with 1–2 sources */}
      {(sources?.length || 0) < 3 && <QuickConnect />}
    </div>
  );
}
