import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { PricingSection } from "@/components/pricing/PricingSection";
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
  Server,
  Lock,
  MapPin,
} from "lucide-react";

const problems = [
  {
    icon: Layers,
    title: "Nothing talks to anything",
    description:
      "Sales in one app, settlements in another, expenses in a spreadsheet. Month-end means exporting CSVs and praying the numbers agree.",
  },
  {
    icon: DollarSign,
    title: "Enterprise tools, enterprise prices",
    description:
      "The big data platforms price for Fortune 500 budgets. A Lagos SME should not pay San Francisco rates to see its own numbers.",
  },
  {
    icon: FileQuestion,
    title: "Built abroad, blind to Africa",
    description:
      "Mobile money, USSD payments, WhatsApp orders. Most integration tools do not even have connectors for how business actually happens here.",
  },
  {
    icon: UserX,
    title: "No data team, no answers",
    description:
      "You cannot hire two data engineers just to know your margins. You should not have to.",
  },
];

const solutionFeatures = [
  {
    icon: Database,
    title: "15+ Connectors",
    description:
      "Paystack, Flutterwave, M-Pesa, MTN MoMo, Mono, WhatsApp, PostgreSQL, MySQL, MongoDB, Google Sheets, REST APIs, and more.",
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
    title: "Built for Africa First",
    description:
      "Native connectors for Paystack, Flutterwave, M-Pesa, MTN MoMo, Mono, and WhatsApp — the systems African businesses actually run on. Plus Stripe and bank connections for operations in France and the EU.",
  },
  {
    icon: Shield,
    title: "Enterprise Security",
    description:
      "Encryption at rest, role-based access control, two-factor authentication, audit logs, and GDPR compliance.",
  },
];

const whyUnifiedLayer = [
  {
    title: "Built for SMEs, not enterprises",
    description:
      "Flat, predictable pricing with no per-credit billing or hidden fees. Start free and scale as you grow.",
  },
  {
    title: "Zero infrastructure to manage",
    description:
      "Fully managed platform. No DevOps expertise required. We handle the complexity so you can focus on insights.",
  },
  {
    title: "Unconventional data sources included",
    description:
      "Native connectors for M-Pesa, Paystack, Flutterwave, WhatsApp, and other sources that enterprise tools ignore.",
  },
  {
    title: "Up and running in minutes",
    description:
      "Connect your first data source in under 5 minutes. No consultants, no lengthy onboarding, no training required.",
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
              href="/integrations"
              className="text-sm font-medium text-muted-foreground hover:text-foreground"
            >
              Integrations
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
            <Link href="/request-access">
              <Button size="sm">Request Access</Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero Section */}
      <section className="relative overflow-hidden bg-gradient-to-b from-primary/10 via-sky-50/40 to-background py-24 md:py-36 dark:via-background">
        <div className="container relative">
          <div className="mx-auto max-w-3xl text-center">
            <Badge className="mb-6" variant="secondary">
              Made for African SMEs
            </Badge>
            <h1 className="mb-6 font-display text-4xl font-bold tracking-tight sm:text-5xl md:text-6xl lg:text-7xl">
              See your whole business
              <span className="block bg-gradient-to-r from-blue-600 via-sky-500 to-emerald-500 bg-clip-text text-transparent">
                in one place
              </span>
            </h1>
            <p className="mx-auto mb-10 max-w-2xl text-lg text-muted-foreground sm:text-xl">
              Your payments live in Paystack. Your wallet data sits with
              M-Pesa. Your books are still in a spreadsheet. UnifiedLayer
              pulls it all into one warehouse you control, so you finally know
              what&apos;s going on without hiring a data team.
            </p>
            <div className="flex flex-col gap-4 sm:flex-row sm:justify-center">
              <Link href="/request-access">
                <Button size="lg" className="w-full sm:w-auto">
                  Request Access
                  <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </Link>
              <Link href="/login">
                <Button
                  size="lg"
                  variant="outline"
                  className="w-full sm:w-auto"
                >
                  Sign In
                </Button>
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Problem Section */}
      <section className="border-t py-20 md:py-28">
        <div className="container">
          <div className="mx-auto mb-16 max-w-2xl text-center">
            <h2 className="mb-4 font-display text-3xl font-bold tracking-tight sm:text-4xl">
              Sound familiar?
            </h2>
            <p className="text-lg text-muted-foreground">
              If you run a business in Lagos, Nairobi, or Accra, you already
              know these problems by name.
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
            <h2 className="mb-4 font-display text-3xl font-bold tracking-tight sm:text-4xl">
              One platform. All your data.
            </h2>
            <p className="text-lg text-muted-foreground">
              Connect your tools, clean the data, get answers. That&apos;s the
              whole job.
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

      {/* Why UnifiedLayer Section */}
      <section className="border-t py-20 md:py-28">
        <div className="container">
          <div className="mx-auto mb-16 max-w-2xl text-center">
            <h2 className="mb-4 font-display text-3xl font-bold tracking-tight sm:text-4xl">
              Why choose UnifiedLayer?
            </h2>
            <p className="text-lg text-muted-foreground">
              Because it was built for businesses like yours, not scaled down
              from something built for banks.
            </p>
          </div>
          <div className="mx-auto grid max-w-4xl gap-6 md:grid-cols-2">
            {whyUnifiedLayer.map((item) => (
              <div
                key={item.title}
                className="flex items-start gap-4 rounded-lg border-2 p-6 transition-colors hover:border-primary/50"
              >
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary/10">
                  <Check className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-semibold">{item.title}</h3>
                  <p className="mt-1 text-sm text-muted-foreground">
                    {item.description}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Data Sovereignty Section */}
      <section className="border-t bg-primary/5 py-20 md:py-28">
        <div className="container">
          <div className="mx-auto mb-16 max-w-2xl text-center">
            <Badge className="mb-4" variant="secondary">
              Data Sovereignty
            </Badge>
            <h2 className="mb-4 font-display text-3xl font-bold tracking-tight sm:text-4xl">
              Your data. Your country. Your control.
            </h2>
            <p className="text-lg text-muted-foreground">
              Most global platforms quietly ship your data to servers in the
              US or Europe. We built UnifiedLayer the other way around. You
              decide where your data lives and who can touch it.
            </p>
          </div>
          <div className="mx-auto grid max-w-5xl gap-6 md:grid-cols-3">
            <Card className="border-2 transition-colors hover:border-primary/50">
              <CardHeader>
                <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                  <MapPin className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>Local data residency</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Keep your data in-country. Regional hosting options mean your
                  business data doesn&apos;t have to leave your jurisdiction to be
                  useful.
                </p>
              </CardContent>
            </Card>
            <Card className="border-2 transition-colors hover:border-primary/50">
              <CardHeader>
                <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                  <Lock className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>Regulation-ready</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Designed with NDPR (Nigeria), GDPR (EU), and local financial
                  reporting requirements in mind &mdash; compliance is built into
                  the platform, not bolted on.
                </p>
              </CardContent>
            </Card>
            <Card className="border-2 transition-colors hover:border-primary/50">
              <CardHeader>
                <div className="mb-2 flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                  <Server className="h-6 w-6 text-primary" />
                </div>
                <CardTitle>You own the pipeline</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm text-muted-foreground">
                  Credentials encrypted at rest, full audit logs, role-based
                  access, and data export at any time. Your data is never sold,
                  shared, or mined.
                </p>
              </CardContent>
            </Card>
          </div>
        </div>
      </section>

      {/* Pricing Section — purchasing-power pricing per market */}
      <PricingSection />

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
              <Link href="/integrations" className="hover:text-foreground">
                Integrations
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
