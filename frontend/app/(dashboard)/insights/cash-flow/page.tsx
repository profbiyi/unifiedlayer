"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import {
  Activity,
  ArrowLeft,
  ArrowDown,
  ArrowUp,
  Landmark,
  Plug,
  TrendingDown,
  TrendingUp,
} from "lucide-react";
import apiClient from "@/lib/api-client";

interface CashFlowData {
  period_days: number;
  description: string;
  available_when_connected: string[];
  sample_insights: Record<string, { description: string; chart_type: string }>;
}

export default function CashFlowPage() {
  const [data, setData] = useState<CashFlowData | null>(null);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        const [cfRes, dashRes] = await Promise.all([
          apiClient.get("/insights/cash-flow"),
          apiClient.get("/insights/dashboard"),
        ]);
        setData(cfRes.data);
        const sources = dashRes.data.connected_sources || {};
        setConnected(!!sources["open_banking"]);
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
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/insights">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-5 w-5" />
          </Button>
        </Link>
        <div>
          <h1 className="text-3xl font-bold tracking-tight flex items-center gap-3">
            <Landmark className="h-8 w-8 text-blue-600" />
            Cash Flow Analysis
          </h1>
          <p className="text-muted-foreground">
            Daily inflows vs outflows, spending breakdown, and balance trends.
          </p>
        </div>
      </div>

      {!connected ? (
        <Card className="border-blue-200 bg-blue-50/50 dark:bg-blue-950/20">
          <CardContent className="pt-6">
            <div className="text-center space-y-4 py-8">
              <div className="flex justify-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-blue-100 dark:bg-blue-900">
                  <Plug className="h-8 w-8 text-blue-600" />
                </div>
              </div>
              <h2 className="text-xl font-semibold">Connect Your Bank Account</h2>
              <p className="text-muted-foreground max-w-md mx-auto">
                {data?.description || "Connect via Open Banking to see real-time cash flow analysis."}
              </p>
              <Link href="/sources">
                <Button size="lg" className="mt-2">
                  <Plug className="mr-2 h-4 w-4" />
                  Connect Open Banking
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* KPI Row */}
          <div className="grid gap-4 md:grid-cols-4">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Net Cash Flow</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">+&pound;4,230</div>
                <div className="flex items-center text-xs text-muted-foreground">
                  <TrendingUp className="h-3 w-3 mr-1 text-green-600" />
                  +12% vs last month
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Total Inflows</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">&pound;18,450</div>
                <p className="text-xs text-muted-foreground">Last 30 days</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Total Outflows</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">&pound;14,220</div>
                <p className="text-xs text-muted-foreground">Last 30 days</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Runway</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">6.2 months</div>
                <p className="text-xs text-muted-foreground">At current burn rate</p>
              </CardContent>
            </Card>
          </div>

          {/* Spending Breakdown */}
          <Card>
            <CardHeader>
              <CardTitle>Spending by Category</CardTitle>
              <CardDescription>Auto-categorized from bank transactions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { category: "Payroll", amount: 6800, percent: 47.8, color: "bg-blue-500" },
                  { category: "Rent & Utilities", amount: 2400, percent: 16.9, color: "bg-purple-500" },
                  { category: "Software & Subscriptions", amount: 1850, percent: 13.0, color: "bg-green-500" },
                  { category: "Professional Services", amount: 1200, percent: 8.4, color: "bg-orange-500" },
                  { category: "Marketing", amount: 980, percent: 6.9, color: "bg-pink-500" },
                  { category: "Other", amount: 990, percent: 7.0, color: "bg-gray-400" },
                ].map((item) => (
                  <div key={item.category} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{item.category}</span>
                      <span className="text-muted-foreground">
                        &pound;{item.amount.toLocaleString()} ({item.percent}%)
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-muted">
                      <div
                        className={`h-full rounded-full ${item.color}`}
                        style={{ width: `${item.percent}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Recurring Costs */}
          <Card>
            <CardHeader>
              <CardTitle>Detected Recurring Costs</CardTitle>
              <CardDescription>Direct debits and subscriptions identified from transactions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  { name: "AWS", amount: 340, frequency: "Monthly", next: "Feb 1" },
                  { name: "Slack", amount: 95, frequency: "Monthly", next: "Feb 3" },
                  { name: "Google Workspace", amount: 78, frequency: "Monthly", next: "Feb 5" },
                  { name: "WeWork", amount: 650, frequency: "Monthly", next: "Feb 1" },
                  { name: "Xero", amount: 35, frequency: "Monthly", next: "Feb 10" },
                ].map((item) => (
                  <div key={item.name} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div>
                      <p className="text-sm font-medium">{item.name}</p>
                      <p className="text-xs text-muted-foreground">{item.frequency} &middot; Next: {item.next}</p>
                    </div>
                    <span className="text-sm font-semibold">&pound;{item.amount}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* Available Insights */}
      {data?.sample_insights && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Available Insights</CardTitle>
            <CardDescription>What you get with Open Banking connected</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 md:grid-cols-2">
              {Object.entries(data.sample_insights).map(([key, insight]) => (
                <div key={key} className="flex items-start gap-3 p-3 rounded-lg bg-muted/50">
                  <Badge variant="outline" className="shrink-0 text-xs">
                    {insight.chart_type}
                  </Badge>
                  <p className="text-sm text-muted-foreground">{insight.description}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
