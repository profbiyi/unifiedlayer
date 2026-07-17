"use client";

import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ArrowRight,
  Building2,
  CreditCard,
  Database,
  FileSpreadsheet,
  Landmark,
  Plug,
  Smartphone,
  Zap,
  Shield,
  RefreshCw,
} from "lucide-react";

const integrationCategories = [
  {
    icon: CreditCard,
    title: "Payment Processors",
    description: "Connect Paystack, Flutterwave, and Stripe to track revenue and transactions across all your channels.",
    examples: ["Paystack", "Flutterwave", "Stripe"],
  },
  {
    icon: Smartphone,
    title: "Mobile Money",
    description: "Sync M-Pesa and MTN MoMo wallets to reconcile mobile money alongside the rest of your business data.",
    examples: ["M-Pesa", "MTN MoMo"],
  },
  {
    icon: Landmark,
    title: "Banking & Open Banking",
    description: "Connect bank accounts via Mono for African banks — plus TrueLayer for operations in Europe.",
    examples: ["Mono", "TrueLayer"],
  },
  {
    icon: Building2,
    title: "Accounting Software",
    description: "Sync your books from Xero today — QuickBooks and Sage connectors are on the roadmap.",
    examples: ["Xero", "QuickBooks (soon)", "Sage (soon)"],
  },
  {
    icon: Database,
    title: "Databases",
    description: "Pull data from PostgreSQL, MySQL, or MongoDB into your analytics warehouse.",
    examples: ["PostgreSQL", "MySQL", "MongoDB"],
  },
  {
    icon: FileSpreadsheet,
    title: "Files & Spreadsheets",
    description: "Upload CSV files or sync Google Sheets directly — where most SME record-keeping lives.",
    examples: ["CSV", "Google Sheets"],
  },
];

const benefits = [
  {
    icon: Zap,
    title: "No Code Required",
    description: "Connect your tools in clicks, not code. No engineers needed.",
  },
  {
    icon: RefreshCw,
    title: "Automatic Syncs",
    description: "Set it and forget it. Your data stays fresh with scheduled syncs.",
  },
  {
    icon: Shield,
    title: "Secure by Default",
    description: "Bank-level encryption. Your credentials are always protected.",
  },
];

export default function IntegrationsPage() {
  return (
    <div className="force-light flex min-h-screen flex-col bg-background text-foreground">
      {/* Navigation */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-6 w-6 text-primary" />
            <Link href="/" className="text-xl font-bold">
              UnifiedLayer
            </Link>
          </div>
          <nav className="flex items-center gap-4">
            <Link href="/integrations" className="text-sm font-medium text-primary">
              Integrations
            </Link>
            <Link href="/login">
              <Button variant="ghost">Sign In</Button>
            </Link>
            <Link href="/request-access">
              <Button>Request Access</Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="border-b bg-gradient-to-b from-primary/5 to-background py-16">
        <div className="container">
          <div className="mx-auto max-w-3xl text-center">
            <Badge variant="secondary" className="mb-4">
              <Plug className="mr-1 h-3 w-3" />
              15+ Integrations
            </Badge>
            <h1 className="mb-4 text-4xl font-bold tracking-tight sm:text-5xl">
              Connect your tools in minutes
            </h1>
            <p className="mb-8 text-lg text-muted-foreground">
              UnifiedLayer connects to the tools you already use—payment processors,
              accounting software, banks, and more. No coding required.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
              <Link href="/integrations/connectors">
                <Button size="lg">
                  Browse All Integrations
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link href="/request-access">
                <Button size="lg" variant="outline">
                  Request Access
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Benefits */}
      <section className="py-12 border-b">
        <div className="container">
          <div className="grid gap-8 md:grid-cols-3">
            {benefits.map((benefit) => {
              const Icon = benefit.icon;
              return (
                <div key={benefit.title} className="flex items-start gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                    <Icon className="h-5 w-5 text-primary" />
                  </div>
                  <div>
                    <h3 className="font-semibold">{benefit.title}</h3>
                    <p className="text-sm text-muted-foreground">{benefit.description}</p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Integration Categories */}
      <section className="py-16">
        <div className="container">
          <div className="text-center mb-12">
            <h2 className="text-3xl font-bold mb-4">What can you connect?</h2>
            <p className="text-muted-foreground max-w-2xl mx-auto">
              From payment processors to accounting software to your bank—bring all your business data together.
            </p>
          </div>
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {integrationCategories.map((category) => {
              const Icon = category.icon;
              return (
                <Card key={category.title} className="hover:shadow-md transition-shadow">
                  <CardHeader>
                    <div className="flex items-center gap-3 mb-2">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <Icon className="h-5 w-5 text-primary" />
                      </div>
                      <CardTitle className="text-lg">{category.title}</CardTitle>
                    </div>
                    <CardDescription>{category.description}</CardDescription>
                    <div className="flex flex-wrap gap-2 pt-3">
                      {category.examples.map((example) => (
                        <Badge key={example} variant="secondary" className="text-xs">
                          {example}
                        </Badge>
                      ))}
                    </div>
                  </CardHeader>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* CTA */}
      <section className="border-t bg-muted/30 py-16">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <h2 className="mb-4 text-2xl font-bold">Ready to unify your data?</h2>
            <p className="mb-6 text-muted-foreground">
              Request access to start your 15-day guided trial. We help you
              connect your first sources, hands-on.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
              <Link href="/request-access">
                <Button size="lg">
                  Request Access
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link href="/integrations/connectors">
                <Button size="lg" variant="outline">
                  View All Connectors
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8">
        <div className="container flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5 text-primary" />
            <span className="font-semibold">UnifiedLayer</span>
          </div>
          <p className="text-sm text-muted-foreground">
            &copy; 2026 UnifiedLayer. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
