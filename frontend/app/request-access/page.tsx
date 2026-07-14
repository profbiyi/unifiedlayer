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
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Database, CheckCircle2, ArrowLeft, Loader2 } from "lucide-react";

// Systems that actually generate data for SMEs in our target markets:
// Nigeria, Ghana, Kenya, and francophone Africa / France
const DIGITAL_SYSTEMS = [
  "Paystack",
  "Flutterwave",
  "M-Pesa",
  "MTN Mobile Money (MoMo)",
  "Wave / Orange Money",
  "POS terminals (Moniepoint, OPay, Interswitch)",
  "Mono / Okra (bank data)",
  "Stripe (France / EU operations)",
  "WhatsApp Business",
  "Accounting software (QuickBooks, Sage, Zoho)",
  "Custom database (PostgreSQL, MySQL, MongoDB)",
  "Spreadsheets (Excel, Google Sheets)",
  "Other",
];

const COUNTRIES = ["Nigeria", "France", "Ghana", "Kenya", "United Kingdom", "Other"];

const SECTORS = [
  { value: "digital_payments", label: "Digital payments" },
  { value: "mobile_wallet", label: "Mobile wallet" },
  { value: "micro_lending", label: "Micro-lending / digital credit" },
  { value: "other_fintech", label: "Other fintech" },
  { value: "retail", label: "Retail / commerce" },
  { value: "other", label: "Other" },
];

const COMPANY_SIZES = ["1-10", "11-50", "51-200", "200+"];

function SectionTitle({ step, children }: { step: number; children: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 border-b pb-2">
      <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-primary text-sm font-semibold text-primary-foreground">
        {step}
      </span>
      <h2 className="font-display text-lg font-semibold">{children}</h2>
    </div>
  );
}

export default function RequestAccessPage() {
  const [companyName, setCompanyName] = useState("");
  const [contactName, setContactName] = useState("");
  const [email, setEmail] = useState("");
  const [country, setCountry] = useState("");
  const [sector, setSector] = useState("");
  const [companySize, setCompanySize] = useState("");
  const [systems, setSystems] = useState<string[]>([]);
  const [dataProblem, setDataProblem] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleSystem = (system: string) => {
    setSystems((prev) =>
      prev.includes(system)
        ? prev.filter((s) => s !== system)
        : [...prev, system]
    );
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    if (systems.length < 2) {
      setError(
        "Please select at least two systems. UnifiedLayer adds the most value when you already generate data in two or more places."
      );
      return;
    }
    if (dataProblem.trim().length < 10) {
      setError("Please tell us a bit more about the problem you are trying to solve.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "/api"}/access-requests`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            company_name: companyName,
            contact_name: contactName,
            email,
            country,
            sector,
            company_size: companySize || null,
            digital_systems: systems,
            data_problem: dataProblem,
          }),
        }
      );
      if (!res.ok) {
        throw new Error("Request failed");
      }
      setSubmitted(true);
    } catch {
      setError(
        "Something went wrong submitting your request. Please try again, or email hello@unifiedlayer.io."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col">
      {/* Navigation */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Database className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">UnifiedLayer</span>
          </Link>
          <nav className="flex items-center gap-4">
            <Link href="/login">
              <Button variant="ghost" size="sm">
                Sign In
              </Button>
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1 bg-gradient-to-b from-primary/5 via-background to-background py-16">
        <div className="container max-w-2xl">
          <Link
            href="/"
            className="mb-6 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to home
          </Link>

          {submitted ? (
            <Card className="border-2">
              <CardHeader className="text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
                  <CheckCircle2 className="h-8 w-8 text-primary" />
                </div>
                <CardTitle className="font-display text-2xl">Got it. We&apos;ll be in touch.</CardTitle>
                <CardDescription className="text-base">
                  Your request is with our team now.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-center text-sm text-muted-foreground">
                <p>
                  Next step is a short call, usually 15 to 20 minutes, so we can
                  understand your setup. If it&apos;s a fit, you start a{" "}
                  <span className="font-medium text-foreground">15-day guided trial</span>{" "}
                  with our team helping you connect your first sources.
                </p>
                <Link href="/" className="inline-block">
                  <Button variant="outline">Back to home</Button>
                </Link>
              </CardContent>
            </Card>
          ) : (
            <Card className="border-2">
              <CardHeader>
                <CardTitle className="font-display text-3xl">Request access</CardTitle>
                <CardDescription className="text-base">
                  We onboard every trial personally. Tell us a bit about your
                  setup, we&apos;ll book a short call, and if it&apos;s a fit
                  you get 15 days on the platform with us helping hands-on.
                  Takes about two minutes.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-8">
                  <SectionTitle step={1}>Your business</SectionTitle>
                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="companyName">Company name</Label>
                      <Input
                        id="companyName"
                        value={companyName}
                        onChange={(e) => setCompanyName(e.target.value)}
                        required
                        minLength={2}
                        placeholder="Acme Payments Ltd"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="contactName">Your name</Label>
                      <Input
                        id="contactName"
                        value={contactName}
                        onChange={(e) => setContactName(e.target.value)}
                        required
                        minLength={2}
                        placeholder="Ada Obi"
                      />
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label htmlFor="email">Work email</Label>
                      <Input
                        id="email"
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        required
                        placeholder="ada@acmepayments.com"
                      />
                    </div>
                    <div className="space-y-2">
                      <Label>Country</Label>
                      <Select value={country} onValueChange={setCountry} required>
                        <SelectTrigger>
                          <SelectValue placeholder="Select country" />
                        </SelectTrigger>
                        <SelectContent>
                          {COUNTRIES.map((c) => (
                            <SelectItem key={c} value={c}>
                              {c}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <div className="grid gap-4 sm:grid-cols-2">
                    <div className="space-y-2">
                      <Label>Sector</Label>
                      <Select value={sector} onValueChange={setSector} required>
                        <SelectTrigger>
                          <SelectValue placeholder="Select sector" />
                        </SelectTrigger>
                        <SelectContent>
                          {SECTORS.map((s) => (
                            <SelectItem key={s.value} value={s.value}>
                              {s.label}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label>Company size</Label>
                      <Select value={companySize} onValueChange={setCompanySize}>
                        <SelectTrigger>
                          <SelectValue placeholder="Number of people" />
                        </SelectTrigger>
                        <SelectContent>
                          {COMPANY_SIZES.map((s) => (
                            <SelectItem key={s} value={s}>
                              {s}
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  <SectionTitle step={2}>Where your data lives today</SectionTitle>
                  <div className="space-y-3">
                    <div className="flex items-center justify-between">
                      <p className="text-sm text-muted-foreground">
                        Pick at least two. That&apos;s where we start connecting.
                      </p>
                      <span
                        className={`shrink-0 rounded-full px-2.5 py-0.5 text-xs font-medium ${
                          systems.length >= 2
                            ? "bg-primary/10 text-primary"
                            : "bg-muted text-muted-foreground"
                        }`}
                      >
                        {systems.length} selected
                      </span>
                    </div>
                    <div className="grid gap-3 sm:grid-cols-2">
                      {DIGITAL_SYSTEMS.map((system) => {
                        const selected = systems.includes(system);
                        return (
                          <label
                            key={system}
                            className={`flex cursor-pointer items-center gap-2 rounded-md border p-3 text-sm transition-colors ${
                              selected
                                ? "border-primary bg-primary/5 font-medium"
                                : "hover:border-primary/50"
                            }`}
                          >
                            <Checkbox
                              checked={selected}
                              onCheckedChange={() => toggleSystem(system)}
                            />
                            <span>{system}</span>
                          </label>
                        );
                      })}
                    </div>
                  </div>

                  <SectionTitle step={3}>The problem you want solved</SectionTitle>
                  <div className="space-y-2">
                    <Label htmlFor="dataProblem">
                      In your own words, what&apos;s the headache?
                    </Label>
                    <Textarea
                      id="dataProblem"
                      value={dataProblem}
                      onChange={(e) => setDataProblem(e.target.value)}
                      required
                      rows={4}
                      placeholder="e.g. Our transactions live in Paystack and our accounts in spreadsheets. Reconciling them for monthly reporting takes days."
                    />
                  </div>

                  {error && (
                    <p className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
                      {error}
                    </p>
                  )}

                  <Button
                    type="submit"
                    size="lg"
                    className="w-full"
                    disabled={submitting || !country || !sector}
                  >
                    {submitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Sending...
                      </>
                    ) : (
                      "Request my guided trial"
                    )}
                  </Button>
                  <p className="text-center text-xs text-muted-foreground">
                    These details only go to our team, and only for the trial.
                    No mailing lists.
                  </p>
                </form>
              </CardContent>
            </Card>
          )}
        </div>
      </main>
    </div>
  );
}
