"use client";

import { useState } from "react";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check } from "lucide-react";

// Purchasing-power pricing per market. Mirrors REGIONAL_PRICING in
// backend/models/billing.py — that table is the source of truth; keep the
// two in sync when prices change.
const MARKETS = [
  { currency: "NGN", country: "Nigeria", flag: "🇳🇬", symbol: "₦", monthly: 15000 },
  { currency: "KES", country: "Kenya", flag: "🇰🇪", symbol: "KSh ", monthly: 2000 },
  { currency: "GHS", country: "Ghana", flag: "🇬🇭", symbol: "GH₵", monthly: 200 },
  { currency: "GBP", country: "United Kingdom", flag: "🇬🇧", symbol: "£", monthly: 35 },
  { currency: "EUR", country: "France / EU", flag: "🇪🇺", symbol: "€", monthly: 39 },
];

const guidedTrialFeatures = [
  "15 days with onboarding support",
  "We help you connect your first sources",
  "5,000 rows synced",
  "1 pipeline sync",
  "1 data source",
  "1 user",
];

const professionalFeatures = [
  "Up to 3 team members",
  "Unlimited connectors",
  "500,000 rows/month",
  "Unlimited pipelines",
  "Data quality checks",
  "Data lineage tracking",
  "Built-in analytics",
  "Email support",
];

const enterpriseFeatures = [
  "Everything in Professional",
  "Unlimited rows",
  "Unlimited users",
  "SLA guarantees",
  "Dedicated support",
  "SSO / SAML",
  "Custom connectors",
  "On-premise option",
];

export function PricingSection() {
  const [market, setMarket] = useState(MARKETS[0]); // Nigeria first — Africa-first

  const formattedPrice = `${market.symbol}${market.monthly.toLocaleString()}`;

  return (
    <section id="pricing" className="border-t bg-muted/30 py-20 md:py-28">
      <div className="container">
        <div className="mx-auto mb-10 max-w-2xl text-center">
          <h2 className="mb-4 font-display text-3xl font-bold tracking-tight sm:text-4xl">
            Priced for your market
          </h2>
          <p className="text-lg text-muted-foreground">
            We price for your economy instead of converting a London price. A
            Lagos business pays Lagos rates. Start with a free guided trial
            and upgrade when it earns its keep.
          </p>
        </div>

        {/* Market selector */}
        <div className="mx-auto mb-4 flex max-w-3xl flex-wrap justify-center gap-2">
          {MARKETS.map((m) => (
            <button
              key={m.currency}
              type="button"
              onClick={() => setMarket(m)}
              className={`rounded-full border px-4 py-2 text-sm font-medium transition-colors ${
                market.currency === m.currency
                  ? "border-primary bg-primary text-primary-foreground"
                  : "bg-background text-muted-foreground hover:border-primary/50 hover:text-foreground"
              }`}
            >
              {m.flag} {m.country}
            </button>
          ))}
        </div>
        <p className="mb-12 text-center text-sm text-muted-foreground">
          Billed in {market.currency} via{" "}
          {["NGN", "KES", "GHS"].includes(market.currency)
            ? "Paystack"
            : "Stripe"}{" "}
          &mdash; no foreign-exchange surprises.
        </p>

        <div className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-3">
          {/* Guided Trial */}
          <Card className="relative border-2">
            <CardHeader className="pb-4 pt-6">
              <Badge variant="secondary" className="mb-2 w-fit">
                15-Day Guided Trial
              </Badge>
              <CardTitle className="text-2xl">Guided Trial</CardTitle>
              <div className="mt-2">
                <span className="text-3xl font-bold">Free</span>
              </div>
              <CardDescription className="mt-2">
                A 15-day guided trial with hands-on onboarding &mdash; request
                access to get started
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                {guidedTrialFeatures.map((feature) => (
                  <div key={feature} className="flex items-start gap-2">
                    <Check className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                    <span className="text-sm">{feature}</span>
                  </div>
                ))}
              </div>
              <Link href="/request-access" className="block">
                <Button className="w-full" variant="outline">
                  Request Access
                </Button>
              </Link>
            </CardContent>
          </Card>

          {/* Professional */}
          <Card className="relative border-primary shadow-lg scale-105">
            <div className="absolute -top-4 left-0 right-0 mx-auto w-fit">
              <Badge className="bg-primary text-primary-foreground">
                Most Popular
              </Badge>
            </div>
            <CardHeader className="pb-4 pt-6">
              <CardTitle className="text-2xl">Professional</CardTitle>
              <div className="mt-2">
                <span className="text-3xl font-bold">{formattedPrice}</span>
                <span className="text-muted-foreground">/month</span>
              </div>
              <CardDescription className="mt-2">
                Unlimited connectors, quality checks, lineage, and analytics
                &mdash; priced for {market.country}
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                {professionalFeatures.map((feature) => (
                  <div key={feature} className="flex items-start gap-2">
                    <Check className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                    <span className="text-sm">{feature}</span>
                  </div>
                ))}
              </div>
              <Link href="/request-access" className="block">
                <Button className="w-full">Request Access</Button>
              </Link>
            </CardContent>
          </Card>

          {/* Enterprise */}
          <Card className="relative border-2">
            <CardHeader className="pb-4 pt-6">
              <Badge variant="secondary" className="mb-2 w-fit">
                Custom
              </Badge>
              <CardTitle className="text-2xl">Enterprise</CardTitle>
              <div className="mt-2">
                <span className="text-3xl font-bold">Custom</span>
              </div>
              <CardDescription className="mt-2">
                For large organisations with custom requirements
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-3">
                {enterpriseFeatures.map((feature) => (
                  <div key={feature} className="flex items-start gap-2">
                    <Check className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                    <span className="text-sm">{feature}</span>
                  </div>
                ))}
              </div>
              <Link href="/request-access" className="block">
                <Button className="w-full" variant="outline">
                  Request Access
                </Button>
              </Link>
            </CardContent>
          </Card>
        </div>
      </div>
    </section>
  );
}
