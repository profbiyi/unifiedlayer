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
  Clock,
  FileText,
  Plug,
} from "lucide-react";
import apiClient from "@/lib/api-client";

export default function InvoicingPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        const [invRes, dashRes] = await Promise.all([
          apiClient.get("/insights/invoicing"),
          apiClient.get("/insights/dashboard"),
        ]);
        setData(invRes.data);
        const sources = dashRes.data.connected_sources || {};
        setConnected(!!sources["xero"]);
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
            <FileText className="h-8 w-8 text-orange-600" />
            Invoice Health
          </h1>
          <p className="text-muted-foreground">
            Overdue invoices, aging report, and collection performance.
          </p>
        </div>
      </div>

      {!connected ? (
        <Card className="border-orange-200 bg-orange-50/50 dark:bg-orange-950/20">
          <CardContent className="pt-6">
            <div className="text-center space-y-4 py-8">
              <div className="flex justify-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-orange-100 dark:bg-orange-900">
                  <Plug className="h-8 w-8 text-orange-600" />
                </div>
              </div>
              <h2 className="text-xl font-semibold">Connect Xero</h2>
              <p className="text-muted-foreground max-w-md mx-auto">
                {data?.description || "Connect Xero to see invoice health and collection metrics."}
              </p>
              <Link href="/sources">
                <Button size="lg" className="mt-2">
                  <Plug className="mr-2 h-4 w-4" />
                  Connect Xero
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
                <CardTitle className="text-sm font-medium">Total Outstanding</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">&pound;24,800</div>
                <p className="text-xs text-muted-foreground">Across 32 invoices</p>
              </CardContent>
            </Card>
            <Card className="border-red-200/50">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Overdue</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-red-600">&pound;8,450</div>
                <p className="text-xs text-muted-foreground">12 invoices past due</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Avg Days to Pay</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">24 days</div>
                <p className="text-xs text-muted-foreground">vs 30 day terms</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Collection Rate</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">87%</div>
                <p className="text-xs text-muted-foreground">Paid on time this month</p>
              </CardContent>
            </Card>
          </div>

          {/* Aging Report */}
          <Card>
            <CardHeader>
              <CardTitle>Invoice Aging Report</CardTitle>
              <CardDescription>Outstanding invoices by age</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {[
                  { period: "Current (not yet due)", amount: 16350, count: 20, color: "bg-green-500", percent: 65.9 },
                  { period: "1-30 days overdue", amount: 4200, count: 6, color: "bg-yellow-500", percent: 16.9 },
                  { period: "31-60 days overdue", amount: 2800, count: 4, color: "bg-orange-500", percent: 11.3 },
                  { period: "60+ days overdue", amount: 1450, count: 2, color: "bg-red-500", percent: 5.8 },
                ].map((item) => (
                  <div key={item.period} className="space-y-1">
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium">{item.period}</span>
                      <span className="text-muted-foreground">
                        &pound;{item.amount.toLocaleString()} ({item.count} invoices)
                      </span>
                    </div>
                    <div className="h-3 rounded-full bg-muted">
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

          {/* Top Debtors */}
          <Card>
            <CardHeader>
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-5 w-5 text-orange-600" />
                <CardTitle>Top Debtors</CardTitle>
              </div>
              <CardDescription>Customers with the highest outstanding balances</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  { name: "MegaCorp Ltd", outstanding: 4200, oldest: "45 days", invoices: 3 },
                  { name: "StartupXYZ", outstanding: 2100, oldest: "62 days", invoices: 2 },
                  { name: "Local Services Co", outstanding: 1800, oldest: "28 days", invoices: 4 },
                  { name: "Digital Agency", outstanding: 1200, oldest: "15 days", invoices: 1 },
                  { name: "Retail Group", outstanding: 950, oldest: "35 days", invoices: 2 },
                ].map((item) => (
                  <div key={item.name} className="flex items-center justify-between py-2 border-b last:border-0">
                    <div>
                      <p className="text-sm font-medium">{item.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {item.invoices} invoice{item.invoices !== 1 ? "s" : ""} &middot; Oldest: {item.oldest}
                      </p>
                    </div>
                    <div className="text-right">
                      <p className="text-sm font-semibold">&pound;{item.outstanding.toLocaleString()}</p>
                      <Badge variant={parseInt(item.oldest) > 30 ? "destructive" : "secondary"} className="text-xs">
                        {parseInt(item.oldest) > 30 ? "Overdue" : "Current"}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}
