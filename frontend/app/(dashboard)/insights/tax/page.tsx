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
  Calendar,
  CheckCircle2,
  Clock,
  Plug,
  PoundSterling,
} from "lucide-react";
import apiClient from "@/lib/api-client";

export default function TaxReadinessPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        const [taxRes, dashRes] = await Promise.all([
          apiClient.get("/insights/tax-readiness"),
          apiClient.get("/insights/dashboard"),
        ]);
        setData(taxRes.data);
        const sources = dashRes.data.connected_sources || {};
        setConnected(!!sources["hmrc_mtd"]);
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
            <PoundSterling className="h-8 w-8 text-purple-600" />
            Tax Readiness
          </h1>
          <p className="text-muted-foreground">
            VAT obligations, estimated liability, and filing deadlines.
          </p>
        </div>
      </div>

      {!connected ? (
        <Card className="border-purple-200 bg-purple-50/50 dark:bg-purple-950/20">
          <CardContent className="pt-6">
            <div className="text-center space-y-4 py-8">
              <div className="flex justify-center">
                <div className="flex h-16 w-16 items-center justify-center rounded-full bg-purple-100 dark:bg-purple-900">
                  <Plug className="h-8 w-8 text-purple-600" />
                </div>
              </div>
              <h2 className="text-xl font-semibold">Connect HMRC MTD</h2>
              <p className="text-muted-foreground max-w-md mx-auto">
                {data?.description || "Connect HMRC Making Tax Digital to track VAT obligations."}
              </p>
              <Link href="/sources">
                <Button size="lg" className="mt-2">
                  <Plug className="mr-2 h-4 w-4" />
                  Connect HMRC MTD
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Next Deadline Alert */}
          <Card className="border-purple-300/50 bg-gradient-to-r from-purple-50 to-purple-100/50 dark:from-purple-950/30 dark:to-purple-900/20">
            <CardContent className="pt-6">
              <div className="flex items-start gap-4">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-purple-200 dark:bg-purple-800">
                  <Calendar className="h-6 w-6 text-purple-700 dark:text-purple-300" />
                </div>
                <div>
                  <p className="text-lg font-semibold">Next VAT Return Due: 7 May 2026</p>
                  <p className="text-sm text-muted-foreground">Period: 1 Jan 2026 — 31 Mar 2026</p>
                  <div className="flex items-center gap-2 mt-2">
                    <Badge className="bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100">
                      <Clock className="h-3 w-3 mr-1" />
                      95 days remaining
                    </Badge>
                    <Badge variant="outline">Estimated: &pound;3,200</Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* KPI Row */}
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Estimated VAT Liability</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">&pound;3,200</div>
                <p className="text-xs text-muted-foreground">Current quarter to date</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Outstanding Payments</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">&pound;0</div>
                <p className="text-xs text-green-600">All caught up</p>
              </CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm font-medium">Compliance Score</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold text-green-600">100%</div>
                <p className="text-xs text-muted-foreground">All returns filed on time</p>
              </CardContent>
            </Card>
          </div>

          {/* VAT History */}
          <Card>
            <CardHeader>
              <CardTitle>VAT Return History</CardTitle>
              <CardDescription>Previous submissions and payments</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {[
                  { period: "Q3 2025 (Jul-Sep)", amount: 2850, status: "Paid", filedOn: "2 Nov 2025", onTime: true },
                  { period: "Q2 2025 (Apr-Jun)", amount: 3100, status: "Paid", filedOn: "28 Jul 2025", onTime: true },
                  { period: "Q1 2025 (Jan-Mar)", amount: 2600, status: "Paid", filedOn: "5 May 2025", onTime: true },
                  { period: "Q4 2024 (Oct-Dec)", amount: 3400, status: "Paid", filedOn: "1 Feb 2025", onTime: true },
                ].map((item) => (
                  <div key={item.period} className="flex items-center justify-between py-3 border-b last:border-0">
                    <div>
                      <p className="text-sm font-medium">{item.period}</p>
                      <p className="text-xs text-muted-foreground">Filed: {item.filedOn}</p>
                    </div>
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-semibold">&pound;{item.amount.toLocaleString()}</span>
                      <Badge variant="outline" className="text-green-700 border-green-300">
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        {item.status}
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
