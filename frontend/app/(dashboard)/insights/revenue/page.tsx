"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import Link from "next/link";
import {
  Activity,
  ArrowLeft,
  AlertTriangle,
  CheckCircle2,
  CreditCard,
  Plug,
  TrendingUp,
  Users,
  XCircle,
} from "lucide-react";
import apiClient from "@/lib/api-client";

export default function RevenuePage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        const [revRes, dashRes] = await Promise.all([
          apiClient.get("/insights/revenue"),
          apiClient.get("/insights/dashboard"),
        ]);
        setData(revRes.data);
        const sources = dashRes.data.connected_sources || {};
        setConnected(!!(sources["gocardless"] || sources["stripe"] || sources["paystack"]));
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
            <TrendingUp className="h-8 w-8 text-green-600" />
            Revenue &amp; Payments
          </h1>
          <p className="text-muted-foreground">
            Revenue trends, MRR tracking, and payment health metrics.
          </p>
        </div>
      </div>

      {!connected ? (
        <Card className="border-green-200 bg-green-50/50 dark:bg-green-950/20">
          <CardContent className="pt-6">
            <div className="text-center space-y-4 py-8">
              <div className="flex justify-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-green-100 dark:bg-green-900">
                  <Plug className="h-8 w-8 text-green-600" />
                </div>
              </div>
              <h2 className="text-xl font-semibold">Connect a Payment Provider</h2>
              <p className="text-muted-foreground max-w-md mx-auto">
                {data?.description || "Connect GoCardless, Stripe, or Paystack to see revenue insights."}
              </p>
              <Link href="/sources">
                <Button size="lg" className="mt-2">
                  <Plug className="mr-2 h-4 w-4" />
                  Connect Payment Provider
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
                <CardTitle className="text-sm font-medium">MRR</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">&pound;12,450</div>
                <div className="flex items-center text-xs text-green-600">
                  <TrendingUp className="h-3 w-3 mr-1" />
                  +8.3% vs last month
                </div>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Revenue (30d)</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">&pound;14,200</div>
                <p className="text-xs text-muted-foreground">Including one-offs</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Collection Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">96.4%</div>
                <p className="text-xs text-muted-foreground">Payments collected successfully</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Active Customers</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">148</div>
                <p className="text-xs text-muted-foreground">With active mandates</p>
              </CardContent>
            </Card>
          </div>

          {/* Failed Payments */}
          <Card className="border-red-200/50">
            <CardHeader>
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-red-600" />
                <CardTitle>Failed Payments</CardTitle>
              </div>
              <CardDescription>Payments that need attention</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  { customer: "Acme Ltd", amount: 250, reason: "Insufficient funds", date: "Jan 28", retry: "Scheduled Feb 2" },
                  { customer: "TechCo", amount: 180, reason: "Mandate cancelled", date: "Jan 25", retry: "Manual action needed" },
                  { customer: "Smith & Sons", amount: 95, reason: "Bank account closed", date: "Jan 22", retry: "Contact customer" },
                ].map((item, i) => (
                  <div key={i} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div className="flex items-center gap-3">
                      <XCircle className="h-4 w-4 text-red-500 shrink-0" />
                      <div>
                        <p className="text-sm font-medium">{item.customer}</p>
                        <p className="text-xs text-muted-foreground">{item.reason} &middot; {item.date}</p>
                      </div>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold">&pound;{item.amount}</p>
                      <p className="text-xs text-muted-foreground">{item.retry}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Top Customers */}
          <Card>
            <CardHeader>
              <CardTitle>Top Customers by Revenue</CardTitle>
              <CardDescription>Revenue concentration — watch for over-reliance on single customers</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  { name: "Enterprise Corp", revenue: 2400, percent: 19.3 },
                  { name: "Acme Ltd", revenue: 1800, percent: 14.4 },
                  { name: "Global Services", revenue: 1200, percent: 9.6 },
                  { name: "TechCo", revenue: 980, percent: 7.9 },
                  { name: "Smith & Sons", revenue: 750, percent: 6.0 },
                ].map((item) => (
                  <div key={item.name} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{item.name}</span>
                      <span className="text-muted-foreground">
                        &pound;{item.revenue.toLocaleString()}/mo ({item.percent}%)
                      </span>
                    </div>
                    <div className="h-2 rounded-full bg-muted">
                      <div
                        className="h-full rounded-full bg-green-500"
                        style={{ width: `${item.percent * 3}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
              {/* Concentration warning */}
              <div className="mt-4 p-3 rounded-lg bg-yellow-50 dark:bg-yellow-950/20 border border-yellow-200/50">
                <div className="flex items-start gap-2">
                  <AlertTriangle className="h-4 w-4 text-yellow-600 shrink-0 mt-0.5" />
                  <p className="text-xs text-yellow-800 dark:text-yellow-200">
                    Top 2 customers account for 33.7% of revenue. Consider diversifying your customer base.
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
