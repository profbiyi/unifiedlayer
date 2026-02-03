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
import {
  ArrowRight,
  Check,
  Database,
  Workflow,
  BarChart3,
  GitBranch,
  Globe,
  Shield,
  Layers,
  DollarSign,
  FileQuestion,
  UserX,
} from "lucide-react";

const problems = [
  {
    icon: Layers,
    title: "Data trapped in silos",
    description:
      "Your data is fragmented across SaaS tools, databases, and spreadsheets with no way to connect the dots.",
  },
  {
    icon: DollarSign,
    title: "Enterprise tools, enterprise prices",
    description:
      "Existing data platforms are built for large companies with large budgets. Complex to set up, expensive to run.",
  },
  {
    icon: FileQuestion,
    title: "Non-standard data ignored",
    description:
      "Most integration solutions exclude unconventional data sources like mobile money, local payment rails, and messaging platforms.",
  },
  {
    icon: UserX,
    title: "No data team, no insights",
    description:
      "Hiring data analysts and engineers is financially unrealistic for most SMEs. Insights remain locked away.",
  },
];

const solutionFeatures = [
  {
    icon: Database,
    title: "15+ Connectors",
    description:
      "PostgreSQL, MySQL, M-Pesa, Paystack, Flutterwave, WhatsApp, REST APIs, Google Sheets, Xero, GoCardless, Open Banking, MongoDB, and more.",
  },
  {
    icon: BarChart3,
    title: "Unified Analytics",
    description:
      "A single source of truth for all your data with built-in quality checks and reporting.",
  },
  {
    icon: Workflow,
    title: "Pipeline Orchestration",
    description:
      "Automated scheduling, retries, change data capture (CDC), and real-time monitoring.",
  },
  {
    icon: GitBranch,
    title: "Data Lineage",
    description:
      "Track data flow from source to destination. Understand where every row comes from and where it goes.",
  },
  {
    icon: Globe,
    title: "Built for Europe",
    description:
      "Native connectors for HMRC MTD, Open Banking, GoCardless, Stripe, Paystack, Flutterwave, and M-Pesa — ready for UK and EU markets.",
  },
  {
    icon: Shield,
    title: "Enterprise Security",
    description:
      "Encryption at rest, role-based access control, two-factor authentication, audit logs, and GDPR compliance.",
  },
];

const competitors = [
  {
    name: "Fivetran",
    summary:
      "Enterprise pricing with 300+ connectors, but starts at $1/mo per credit. Costs escalate quickly.",
    unifiedLayer:
      "Flat, predictable pricing purpose-built for SMEs. No per-credit billing.",
  },
  {
    name: "Airbyte",
    summary:
      "Open source but requires DevOps expertise to self-host and maintain infrastructure.",
    unifiedLayer:
      "Fully managed platform. Zero ops, zero infrastructure to maintain.",
  },
  {
    name: "Stitch (by Talend)",
    summary:
      "Acquired by Qlik with a limited free tier and uncertain product direction.",
    unifiedLayer:
      "Transparent pricing with no surprises. Independent and focused on SMEs.",
  },
  {
    name: "Hevo Data",
    summary:
      "Good for mid-market companies but limited African payment and mobile money connectors.",
    unifiedLayer:
      "Built-in M-Pesa, Paystack, and Flutterwave connectors from day one.",
  },
];

const plans = [
  {
    name: "Starter",
    price: "Free",
    period: "",
    description: "Get started with 3 connectors and 10,000 rows/month",
    badge: "Free Forever",
    features: [
      "3 connectors",
      "10,000 rows/month",
      "1 user",
      "3 pipelines",
      "Community support",
      "Basic scheduling",
    ],
    highlighted: false,
  },
  {
    name: "Professional",
    price: "\u00a335",
    period: "/month",
    description:
      "Unlimited connectors, quality checks, lineage, and analytics",
    badge: "Most Popular",
    features: [
      "Unlimited connectors",
      "500,000 rows/month",
      "5 users",
      "Unlimited pipelines",
      "Data quality checks",
      "Data lineage tracking",
      "Built-in analytics",
      "Email support",
    ],
    highlighted: true,
  },
  {
    name: "Enterprise",
    price: "Custom",
    period: "",
    description: "For large organisations with custom requirements",
    badge: "Custom",
    features: [
      "Everything in Professional",
      "Unlimited rows",
      "Unlimited users",
      "SLA guarantees",
      "Dedicated support",
      "SSO / SAML",
      "Custom connectors",
      "On-premise option",
    ],
    highlighted: false,
  },
];

export default function Home() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Navigation */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">UnifiedLayer</span>
          </div>
          <nav className="flex items-center gap-4">
            <Link
              href="/developers"
              className="text-sm font-medium text-muted-foreground hover:text-foreground"
            >
              Developers
            </Link>
            <Link href="#pricing">
              <Button variant="ghost" size="sm">
                Pricing
              </Button>
            </Link>
            <Link href="/login">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
            <a href="mailto:hello@unifiedlayer.io">
              <Button size="sm">Request Access</Button>
            </a>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-primary/5 via-background to-background py-24 md:py-36">
        <div className="container relative">
          <div className="mx-auto max-w-3xl text-center">
            <Badge className="mb-6" variant="secondary">
              The data platform for SMEs
            </Badge>
            <h1 className="mb-6 text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
              Turn fragmented data
              <span className="block bg-gradient-to-r from-primary to-blue-600 bg-clip-text text-transparent">
                into clarity
              </span>
            </h1>
            <p className="mx-auto mb-10 max-w-2xl text-lg text-muted-foreground sm:text-xl">
              UnifiedLayer is the data integration and analytics platform built
              for SMEs. Connect all your data sources &mdash; conventional and
              unconventional &mdash; into a single source of truth. No data team
              required.
            </p>
            <div className="flex flex-col gap-4 sm:flex-row sm:justify-center">
              <Link href="/login">
                <Button size="lg" className="w-full sm:w-auto">
                  Sign In
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <a href="mailto:hello@unifiedlayer.io">
                <Button
                  size="lg"
                  variant="outline"
                  className="w-full sm:w-auto"
                >
                  Request Access
                </Button>
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* Problem Section */}
      <section className="border-t py-20 md:py-28">
        <div className="container">
          <div className="mx-auto mb-16 max-w-2xl text-center">
            <h2 className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl">
              The SME data challenge
            </h2>
            <p className="text-lg text-muted-foreground">
              Small and mid-sized businesses face unique data problems that
              enterprise tools were never designed to solve.
            </p>
          </div>
          <div className="mx-auto grid max-w-5xl gap-6 sm:grid-cols-2">
            {problems.map((problem) => {
              const Icon = problem.icon;
              return (
                <Card
                  key={problem.title}
                  className="border-2 transition-colors hover:border-primary/50"
                >
                  <CardHeader className="pb-2">
                    <div className="mb-2 flex h-10 w-10 items-center justify-center rounded-lg bg-destructive/10">
                      <Icon className="h-5 w-5 text-destructive" />
                    </div>
                    <CardTitle className="text-lg">{problem.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      {problem.description}
                    </p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* Solution Section */}
      <section className="border-t bg-muted/30 py-20 md:py-28">
        <div className="container">
          <div className="mx-auto mb-16 max-w-2xl text-center">
            <h2 className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl">
              One platform. All your data.
            </h2>
            <p className="text-lg text-muted-foreground">
              Everything you need to connect, transform, and understand your
              data &mdash; without hiring a data team.
            </p>
          </div>
          <div className="mx-auto grid max-w-6xl gap-8 md:grid-cols-2 lg:grid-cols-3">
            {solutionFeatures.map((feature) => {
              const Icon = feature.icon;
              return (
                <Card
                  key={feature.title}
                  className="border-2 transition-colors hover:border-primary/50"
                >
                  <CardHeader>
                    <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                      <Icon className="h-6 w-6 text-primary" />
                    </div>
                    <CardTitle>{feature.title}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <p className="text-sm text-muted-foreground">
                      {feature.description}
                    </p>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* Comparison Section */}
      <section className="border-t py-20 md:py-28">
        <div className="container">
          <div className="mx-auto mb-4 max-w-2xl text-center">
            <h2 className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl">
              The affordable alternative to enterprise tools
            </h2>
            <p className="text-lg text-muted-foreground">
              We respect what these platforms have built. UnifiedLayer is simply
              built for a different audience.
            </p>
          </div>
          <div className="mx-auto mt-12 grid max-w-5xl gap-6 md:grid-cols-2">
            {competitors.map((c) => (
              <Card key={c.name} className="border-2">
                <CardHeader className="pb-3">
                  <CardTitle className="text-lg">{c.name}</CardTitle>
                  <CardDescription>{c.summary}</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="flex items-start gap-2 rounded-lg bg-primary/5 p-3">
                    <Check className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
                    <p className="text-sm font-medium">
                      UnifiedLayer: {c.unifiedLayer}
                    </p>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="border-t bg-muted/30 py-20 md:py-28">
        <div className="container">
          <div className="mx-auto mb-16 max-w-2xl text-center">
            <h2 className="mb-4 text-3xl font-bold tracking-tight sm:text-4xl">
              Simple, transparent pricing
            </h2>
            <p className="text-lg text-muted-foreground">
              Start free. Upgrade when you need more. No surprises.
            </p>
          </div>
          <div className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-3">
            {plans.map((plan) => (
              <Card
                key={plan.name}
                className={`relative ${
                  plan.highlighted
                    ? "border-primary shadow-lg scale-105"
                    : "border-2"
                }`}
              >
                {plan.highlighted && (
                  <div className="absolute -top-4 left-0 right-0 mx-auto w-fit">
                    <Badge className="bg-primary text-primary-foreground">
                      {plan.badge}
                    </Badge>
                  </div>
                )}
                <CardHeader className="pb-4 pt-6">
                  {!plan.highlighted && plan.badge && (
                    <Badge variant="secondary" className="mb-2 w-fit">
                      {plan.badge}
                    </Badge>
                  )}
                  <CardTitle className="text-2xl">{plan.name}</CardTitle>
                  <div className="mt-2">
                    <span className="text-3xl font-bold">{plan.price}</span>
                    <span className="text-muted-foreground">{plan.period}</span>
                  </div>
                  <CardDescription className="mt-2">
                    {plan.description}
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-6">
                  <div className="space-y-3">
                    {plan.features.map((feature) => (
                      <div key={feature} className="flex items-start gap-2">
                        <Check className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                        <span className="text-sm">{feature}</span>
                      </div>
                    ))}
                  </div>
                  <a href="mailto:hello@unifiedlayer.io" className="block">
                    <Button
                      className="w-full"
                      variant={plan.highlighted ? "default" : "outline"}
                    >
                      Request Access
                    </Button>
                  </a>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-12">
        <div className="container">
          <div className="flex flex-col items-center justify-between gap-6 sm:flex-row">
            <div className="flex items-center gap-2">
              <Database className="h-5 w-5 text-primary" />
              <span className="font-semibold">UnifiedLayer</span>
            </div>
            <nav className="flex flex-wrap items-center justify-center gap-6 text-sm text-muted-foreground">
              <Link href="/login" className="hover:text-foreground">
                Sign In
              </Link>
              <Link href="/developers" className="hover:text-foreground">
                Developers
              </Link>
              <Link href="/privacy" className="hover:text-foreground">
                Privacy
              </Link>
              <Link href="/terms" className="hover:text-foreground">
                Terms
              </Link>
            </nav>
          </div>
          <div className="mt-8 border-t pt-8 text-center">
            <p className="text-sm text-muted-foreground">
              &copy; 2026 UnifiedLayer. All rights reserved.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
