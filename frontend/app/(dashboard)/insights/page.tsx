"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import {
  Activity,
  AlertTriangle,
  ArrowDown,
  ArrowRight,
  ArrowUp,
  Banknote,
  BarChart3,
  CheckCircle2,
  Clock,
  CreditCard,
  FileText,
  Landmark,
  Lightbulb,
  PiggyBank,
  Plug,
  PoundSterling,
  TrendingUp,
  XCircle,
} from "lucide-react";
import apiClient from "@/lib/api-client";

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
    stale_details: Array<{ name: string; last_sync: string | null; hours_ago?: number }>;
  };
  connected_sources: Record<string, number>;
  recommendations: Array<{
    type: string;
    priority: string;
    title: string;
    description: string;
  }>;
}

interface ROIData {
  time_saved: { hours: number; description: string };
  money_saved: { gbp: number; description: string };
  data_processed: { rows: number; pipeline_runs: number };
  automation: { active_pipelines: number; description: string };
  verdict: { status: string; message: string };
}

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

const insightCards = [
  {
    id: "cash-flow",
    icon: Landmark,
    title: "Cash Flow Analysis",
    description: "Daily inflows vs outflows, spending breakdown, balance trends, recurring costs",
    requires: "Open Banking",
    color: "text-blue-600",
    bg: "bg-blue-50 dark:bg-blue-950",
  },
  {
    id: "revenue",
    icon: TrendingUp,
    title: "Revenue & Payments",
    description: "Revenue trends, MRR tracking, payment success rates, failed payment alerts, churn signals",
    requires: "GoCardless / Stripe",
    color: "text-green-600",
    bg: "bg-green-50 dark:bg-green-950",
  },
  {
    id: "invoicing",
    icon: FileText,
    title: "Invoice Health",
    description: "Overdue invoices, aging report, average days to pay, top debtors, collection rate",
    requires: "Xero",
    color: "text-orange-600",
    bg: "bg-orange-50 dark:bg-orange-950",
  },
  {
    id: "tax",
    icon: PoundSterling,
    title: "Tax Readiness",
    description: "Next VAT deadline, estimated liability, filing history, compliance score",
    requires: "HMRC MTD",
    color: "text-purple-600",
    bg: "bg-purple-50 dark:bg-purple-950",
  },
];

export default function InsightsPage() {
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [roi, setRoi] = useState<ROIData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchData() {
      try {
        const [dashRes, roiRes] = await Promise.all([
          apiClient.get("/insights/dashboard"),
          apiClient.get("/insights/roi"),
        ]);
        setDashboard(dashRes.data);
        setRoi(roiRes.data);
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
        <h1 className="text-3xl font-bold tracking-tight">Business Insights</h1>
        <p className="text-muted-foreground">
          See what your data tells you about your business.
        </p>
      </div>

      {/* ROI Banner */}
      {roi && (
        <Card className="border-primary/50 bg-gradient-to-r from-primary/5 to-primary/10">
          <CardContent className="pt-6">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
                  <PiggyBank className="h-6 w-6 text-primary" />
                </div>
                <div>
                  <p className="text-lg font-semibold">{dashboard?.summary.headline}</p>
                  <p className="text-sm text-muted-foreground">{roi.verdict.message}</p>
                </div>
              </div>
              <div className="flex gap-6">
                <div className="text-center">
                  <p className="text-2xl font-bold">{roi.time_saved.hours}h</p>
                  <p className="text-xs text-muted-foreground">Time saved</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold">
                    &pound;{roi.money_saved.gbp.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                  </p>
                  <p className="text-xs text-muted-foreground">Money saved</p>
                </div>
                <div className="text-center">
                  <p className="text-2xl font-bold">{formatNumber(roi.data_processed.rows)}</p>
                  <p className="text-xs text-muted-foreground">Rows synced</p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* KPI Cards */}
      {dashboard && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Data Synced</CardTitle>
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{formatNumber(dashboard.summary.data_synced)}</div>
              <div className="flex items-center text-xs">
                {dashboard.summary.data_trend_percent > 0 ? (
                  <ArrowUp className="h-3 w-3 text-green-600 mr-1" />
                ) : dashboard.summary.data_trend_percent < 0 ? (
                  <ArrowDown className="h-3 w-3 text-red-600 mr-1" />
                ) : null}
                <span className={dashboard.summary.data_trend_percent >= 0 ? "text-green-600" : "text-red-600"}>
                  {dashboard.summary.data_trend_percent > 0 ? "+" : ""}{dashboard.summary.data_trend_percent}%
                </span>
                <span className="text-muted-foreground ml-1">vs last month</span>
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Pipeline Health</CardTitle>
              {dashboard.summary.success_rate >= 95 ? (
                <CheckCircle2 className="h-4 w-4 text-green-600" />
              ) : (
                <AlertTriangle className="h-4 w-4 text-yellow-600" />
              )}
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{dashboard.summary.success_rate}%</div>
              <p className="text-xs text-muted-foreground">
                {dashboard.data_health.healthy_pipelines} healthy, {dashboard.data_health.stale_pipelines} stale
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Automations</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{dashboard.summary.pipeline_runs}</div>
              <p className="text-xs text-muted-foreground">Pipeline runs this month</p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between pb-2">
              <CardTitle className="text-sm font-medium">Time Saved</CardTitle>
              <Clock className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{dashboard.summary.time_saved_hours}h</div>
              <p className="text-xs text-muted-foreground">of manual work this month</p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Business Insight Cards */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Your Business at a Glance</h2>
        <div className="grid gap-6 md:grid-cols-2">
          {insightCards.map((card) => {
            const Icon = card.icon;
            const isConnected = dashboard?.connected_sources && (
              (card.id === "cash-flow" && dashboard.connected_sources["open_banking"]) ||
              (card.id === "revenue" && (dashboard.connected_sources["gocardless"] || dashboard.connected_sources["stripe"] || dashboard.connected_sources["paystack"])) ||
              (card.id === "invoicing" && dashboard.connected_sources["xero"]) ||
              (card.id === "tax" && dashboard.connected_sources["hmrc_mtd"])
            );

            return (
              <Card key={card.id} className={`transition-all ${isConnected ? "hover:shadow-md" : "opacity-80"}`}>
                <CardHeader>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${card.bg}`}>
                        <Icon className={`h-5 w-5 ${card.color}`} />
                      </div>
                      <div>
                        <CardTitle className="text-base">{card.title}</CardTitle>
                        <CardDescription className="text-xs">Requires {card.requires}</CardDescription>
                      </div>
                    </div>
                    {isConnected ? (
                      <Badge variant="default" className="bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100">
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        Connected
                      </Badge>
                    ) : (
                      <Badge variant="secondary">
                        <Plug className="h-3 w-3 mr-1" />
                        Connect
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent>
                  <p className="text-sm text-muted-foreground mb-4">{card.description}</p>
                  {isConnected ? (
                    <Link href={`/insights/${card.id === "cash-flow" ? "cash-flow" : card.id === "revenue" ? "revenue" : card.id === "invoicing" ? "invoicing" : "tax"}`}>
                      <Button variant="outline" size="sm" className="w-full">
                        View Insights
                        <ArrowRight className="ml-2 h-3 w-3" />
                      </Button>
                    </Link>
                  ) : (
                    <Link href="/sources">
                      <Button variant="secondary" size="sm" className="w-full">
                        <Plug className="mr-2 h-3 w-3" />
                        Connect {card.requires}
                      </Button>
                    </Link>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Recommendations */}
      {dashboard && dashboard.recommendations.length > 0 && (
        <Card>
          <CardHeader>
            <div className="flex items-center gap-2">
              <Lightbulb className="h-5 w-5 text-yellow-600" />
              <CardTitle>Recommendations</CardTitle>
            </div>
            <CardDescription>Actions to get more value from your data</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {dashboard.recommendations.map((rec, i) => (
                <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                  {rec.type === "connect" ? (
                    <Plug className="h-5 w-5 text-blue-600 shrink-0 mt-0.5" />
                  ) : rec.type === "fix" ? (
                    <AlertTriangle className="h-5 w-5 text-red-600 shrink-0 mt-0.5" />
                  ) : (
                    <ArrowRight className="h-5 w-5 text-green-600 shrink-0 mt-0.5" />
                  )}
                  <div>
                    <p className="text-sm font-medium">{rec.title}</p>
                    <p className="text-xs text-muted-foreground">{rec.description}</p>
                  </div>
                  <Badge
                    variant={rec.priority === "high" ? "destructive" : "secondary"}
                    className="shrink-0 ml-auto text-xs"
                  >
                    {rec.priority}
                  </Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Stale Pipelines Warning */}
      {dashboard && dashboard.data_health.stale_pipelines > 0 && (
        <Card className="border-yellow-500/50">
          <CardHeader>
            <div className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-yellow-600" />
              <CardTitle className="text-base">Stale Data Warning</CardTitle>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {dashboard.data_health.stale_details.map((p, i) => (
                <div key={i} className="flex items-center justify-between text-sm">
                  <span>{p.name}</span>
                  <span className="text-muted-foreground">
                    {p.last_sync ? `${p.hours_ago}h ago` : "Never synced"}
                  </span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
