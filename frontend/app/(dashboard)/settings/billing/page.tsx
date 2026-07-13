"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Activity,
  Check,
  CreditCard,
  Download,
  ExternalLink,
  Loader2,
  BarChart3,
  Zap,
  RefreshCw,
} from "lucide-react";
import apiClient from "@/lib/api-client";

interface Plan {
  id: string;
  name: string;
  price: number | null;
  currency: string;
  interval: string;
  features: string[];
}

interface Subscription {
  plan: string;
  status: string;
  current_period_start: string;
  current_period_end: string;
  cancel_at_period_end?: boolean;
  currency?: string;
  payment_provider?: string;
}

interface Usage {
  period: string;
  rows_synced: number;
  api_calls: number;
  pipeline_runs: number;
  rows_limit: number;
  api_calls_limit: number;
  usage_percent: {
    rows: number;
    api_calls: number;
  };
}

interface Invoice {
  id: string;
  date: string;
  amount: number;
  currency: string;
  status: string;
  pdf_url?: string;
}

const PAYSTACK_CURRENCIES = ["NGN", "KES", "GHS"] as const;
type PaystackCurrency = (typeof PAYSTACK_CURRENCIES)[number];

function isPaystackCurrency(currency?: string): currency is PaystackCurrency {
  return PAYSTACK_CURRENCIES.includes(currency?.toUpperCase() as PaystackCurrency);
}

// Purchasing-power pricing per market \u2014 mirrors REGIONAL_PRICING in
// backend/models/billing.py (the source of truth). Each price is set against
// local affordability, not an FX conversion.
const PAYSTACK_PRICES: Record<PaystackCurrency, { professional: string; amount: number }> = {
  NGN: { professional: "\u20A615,000/mo", amount: 15000 },
  KES: { professional: "KES 2,000/mo", amount: 2000 },
  GHS: { professional: "GH\u20B5200/mo", amount: 200 },
};

const STRIPE_PRICES: Record<string, string> = {
  GBP: "\u00A335/mo",
  EUR: "\u20AC39/mo",
};

const CURRENCY_SYMBOLS: Record<string, string> = {
  GBP: "\u00a3",
  USD: "$",
  NGN: "\u20A6",
  KES: "KES ",
  GHS: "GH\u20B5",
};

function formatNumber(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toLocaleString();
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

const planDetails = [
  {
    id: "starter",
    name: "Free Trial",
    price: "Free",
    description: "Try UnifiedLayer for 30 days",
    features: [
      "5,000 rows synced",
      "1 pipeline sync",
      "1 data source",
      "30-day trial period",
      "Trial ends at 5k rows or 30 days",
    ],
  },
  {
    id: "professional",
    name: "Professional",
    price: "Contact Us",
    description: "For growing businesses",
    features: [
      "Up to 3 team members",
      "100,000 rows synced / month",
      "10,000 API calls / month",
      "Unlimited pipeline runs",
      "Unlimited data sources",
      "Priority support",
      "Custom schedules",
      "Webhooks",
    ],
    highlighted: true,
  },
  {
    id: "enterprise",
    name: "Enterprise",
    price: "Custom",
    description: "For large organisations",
    features: [
      "Unlimited rows synced",
      "Unlimited API calls",
      "Unlimited pipeline runs",
      "Dedicated infrastructure",
      "SLA guarantee",
      "SSO / SAML",
      "Dedicated account manager",
    ],
  },
];

export default function BillingPage() {
  const [subscription, setSubscription] = useState<Subscription | null>(null);
  const [usage, setUsage] = useState<Usage | null>(null);
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [portalLoading, setPortalLoading] = useState(false);

  useEffect(() => {
    async function fetchData() {
      try {
        const [subRes, usageRes, invoicesRes] = await Promise.all([
          apiClient.get("/billing/subscription"),
          apiClient.get("/billing/usage"),
          apiClient.get("/billing/invoices"),
        ]);
        setSubscription(subRes.data);
        setUsage(usageRes.data);
        setInvoices(invoicesRes.data);
      } catch (err) {
        setError("Failed to load billing information. Please try again.");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  const usePaystack = isPaystackCurrency(subscription?.currency);
  const orgCurrency = (subscription?.currency || "GBP").toUpperCase();

  async function handleCheckout(plan: string) {
    try {
      setCheckoutLoading(plan);

      if (usePaystack) {
        // Use Paystack for African currencies
        const res = await apiClient.post("/billing/paystack/checkout", {
          plan,
          currency: orgCurrency,
          success_url: `${window.location.origin}/settings/billing?success=true`,
          cancel_url: `${window.location.origin}/settings/billing`,
        });
        window.location.href = res.data.authorization_url;
      } else {
        // Use Stripe for other currencies
        const res = await apiClient.post("/billing/checkout", {
          plan,
          success_url: `${window.location.origin}/settings/billing?success=true`,
          cancel_url: `${window.location.origin}/settings/billing`,
        });
        window.location.href = res.data.checkout_url;
      }
    } catch (err) {
    } finally {
      setCheckoutLoading(null);
    }
  }

  async function handleManageSubscription() {
    try {
      setPortalLoading(true);
      const res = await apiClient.post("/billing/portal");
      window.location.href = res.data.portal_url;
    } catch (err) {
    } finally {
      setPortalLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Activity className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-96 gap-4">
        <p className="text-muted-foreground">{error}</p>
        <Button variant="outline" onClick={() => window.location.reload()}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Retry
        </Button>
      </div>
    );
  }

  const statusColor: Record<string, string> = {
    active: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100",
    trialing: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100",
    past_due: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100",
    canceled: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100",
    unpaid: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100",
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Billing</h1>
          <p className="text-muted-foreground">
            Manage your subscription, usage, and invoices.
          </p>
        </div>
        {subscription && subscription.plan !== "starter" && (
          <Button onClick={handleManageSubscription} disabled={portalLoading}>
            {portalLoading ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <ExternalLink className="mr-2 h-4 w-4" />
            )}
            Manage Subscription
          </Button>
        )}
      </div>

      {/* Current Plan */}
      {subscription && (
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <CreditCard className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <CardTitle className="text-base">Current Plan</CardTitle>
                  <CardDescription>
                    {subscription.plan.charAt(0).toUpperCase() + subscription.plan.slice(1)} plan
                  </CardDescription>
                </div>
              </div>
              <Badge className={statusColor[subscription.status] || "bg-gray-100 text-gray-800"}>
                {subscription.status.replace("_", " ")}
              </Badge>
            </div>
          </CardHeader>
          <CardContent>
            <div className="flex flex-col sm:flex-row gap-6 text-sm">
              <div>
                <p className="text-muted-foreground">Current period</p>
                <p className="font-medium">
                  {formatDate(subscription.current_period_start)} &mdash; {formatDate(subscription.current_period_end)}
                </p>
              </div>
              {subscription.cancel_at_period_end && (
                <div>
                  <p className="text-muted-foreground">Cancellation</p>
                  <p className="font-medium text-red-600">
                    Cancels at end of period
                  </p>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Usage Meters */}
      {usage && (
        <div>
          <h2 className="text-xl font-semibold mb-4">Usage This Period</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Rows Synced</CardTitle>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(usage.rows_synced)}</div>
                <p className="text-xs text-muted-foreground mb-2">
                  of {formatNumber(usage.rows_limit)} limit
                </p>
                <Progress value={Math.min(usage.usage_percent.rows, 100)} className="h-2" />
                <p className="text-xs text-muted-foreground mt-1">
                  {usage.usage_percent.rows.toFixed(1)}% used
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">API Calls</CardTitle>
                <Zap className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(usage.api_calls)}</div>
                <p className="text-xs text-muted-foreground mb-2">
                  of {formatNumber(usage.api_calls_limit)} limit
                </p>
                <Progress value={Math.min(usage.usage_percent.api_calls, 100)} className="h-2" />
                <p className="text-xs text-muted-foreground mt-1">
                  {usage.usage_percent.api_calls.toFixed(1)}% used
                </p>
              </CardContent>
            </Card>

            <Card>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium">Pipeline Runs</CardTitle>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <div className="text-2xl font-bold">{formatNumber(usage.pipeline_runs)}</div>
                <p className="text-xs text-muted-foreground">this billing period</p>
              </CardContent>
            </Card>
          </div>
        </div>
      )}

      {/* Plan Comparison */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Plans</h2>
        <div className="grid gap-6 md:grid-cols-3">
          {planDetails.map((plan) => {
            const isCurrent = subscription?.plan === plan.id;
            return (
              <Card
                key={plan.id}
                className={`relative ${plan.highlighted ? "border-primary shadow-md" : ""}`}
              >
                {plan.highlighted && (
                  <div className="absolute -top-3 left-1/2 -translate-x-1/2">
                    <Badge className="bg-primary text-primary-foreground">Most Popular</Badge>
                  </div>
                )}
                <CardHeader>
                  <CardTitle>{plan.name}</CardTitle>
                  <CardDescription>{plan.description}</CardDescription>
                  <p className="text-3xl font-bold mt-2">
                    {plan.id === "professional"
                      ? (usePaystack
                          ? PAYSTACK_PRICES[orgCurrency as PaystackCurrency]?.professional
                          : STRIPE_PRICES[orgCurrency]) ?? plan.price
                      : plan.price}
                  </p>
                </CardHeader>
                <CardContent>
                  <ul className="space-y-2 mb-6">
                    {plan.features.map((feature) => (
                      <li key={feature} className="flex items-start gap-2 text-sm">
                        <Check className="h-4 w-4 text-green-600 shrink-0 mt-0.5" />
                        <span>{feature}</span>
                      </li>
                    ))}
                  </ul>
                  {isCurrent ? (
                    <Button variant="outline" className="w-full" disabled>
                      Current Plan
                    </Button>
                  ) : plan.id === "enterprise" ? (
                    <Button
                      variant="outline"
                      className="w-full"
                      onClick={() => handleCheckout("enterprise")}
                      disabled={checkoutLoading === "enterprise"}
                    >
                      {checkoutLoading === "enterprise" && (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      )}
                      Contact Sales
                    </Button>
                  ) : plan.id === "starter" ? (
                    <Button variant="outline" className="w-full" disabled={isCurrent}>
                      {isCurrent ? "Current Plan" : "Downgrade"}
                    </Button>
                  ) : (
                    <Button
                      className="w-full"
                      onClick={() => handleCheckout(plan.id)}
                      disabled={checkoutLoading === plan.id}
                    >
                      {checkoutLoading === plan.id && (
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                      )}
                      Upgrade
                    </Button>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      </div>

      {/* Invoice History */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Invoice History</h2>
        {invoices.length === 0 ? (
          <Card>
            <CardContent className="py-8 text-center">
              <p className="text-muted-foreground">No invoices yet.</p>
            </CardContent>
          </Card>
        ) : (
          <Card>
            <CardContent className="p-0">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Date</TableHead>
                    <TableHead>Amount</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="text-right">Invoice</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {invoices.map((invoice) => (
                    <TableRow key={invoice.id}>
                      <TableCell>{formatDate(invoice.date)}</TableCell>
                      <TableCell>
                        {CURRENCY_SYMBOLS[invoice.currency.toUpperCase()] || invoice.currency}
                        {(invoice.amount / 100).toFixed(2)}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={invoice.status === "paid" ? "default" : "secondary"}
                          className={
                            invoice.status === "paid"
                              ? "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100"
                              : ""
                          }
                        >
                          {invoice.status}
                        </Badge>
                      </TableCell>
                      <TableCell className="text-right">
                        {invoice.pdf_url && (
                          <Button variant="ghost" size="sm" asChild>
                            <a href={invoice.pdf_url} target="_blank" rel="noopener noreferrer">
                              <Download className="h-4 w-4" />
                            </a>
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
}
