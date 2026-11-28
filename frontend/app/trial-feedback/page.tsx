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
import { Database, CheckCircle2, ArrowLeft, Loader2 } from "lucide-react";

// Q5: tick the single most important feature
const TOP_FEATURES = [
  { value: "connecting_sources", label: "Connecting my data sources" },
  { value: "data_location", label: "Controlling where my data is stored" },
  { value: "dashboards", label: "Dashboards and reporting" },
  { value: "ai_insights", label: "AI insights" },
  { value: "local_connectors", label: "Local connectors (M-Pesa, MTN, Paystack, etc.)" },
];

// Q7: fixed monthly price bands, in naira or euro
const PRICE_BANDS_NGN = [
  { value: "ngn_under_25k", label: "Under ₦25,000" },
  { value: "ngn_25k_75k", label: "₦25,000 – ₦75,000" },
  { value: "ngn_75k_150k", label: "₦75,000 – ₦150,000" },
  { value: "ngn_150k_300k", label: "₦150,000 – ₦300,000" },
  { value: "ngn_over_300k", label: "Over ₦300,000" },
];
const PRICE_BANDS_EUR = [
  { value: "eur_under_25", label: "Under €25" },
  { value: "eur_25_75", label: "€25 – €75" },
  { value: "eur_75_150", label: "€75 – €150" },
  { value: "eur_150_300", label: "€150 – €300" },
  { value: "eur_over_300", label: "Over €300" },
];
const PRICE_OTHER = [
  { value: "would_not_pay", label: "I would not pay for it" },
  { value: "other", label: "Other amount or currency" },
];

const ATTRIBUTION = [
  { value: "full", label: "My name, role and company" },
  { value: "name_role", label: "My name and role only" },
  { value: "role_company_type", label: "My role only (e.g. “Head of Finance, fintech company”)" },
  { value: "anonymous", label: "Anonymous (“Trial participant”)" },
];

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

function Scale({
  label,
  value,
  onChange,
  min = 1,
  max = 5,
  low,
  high,
}: {
  label: string;
  value: number | null;
  onChange: (v: number) => void;
  min?: number;
  max?: number;
  low: string;
  high: string;
}) {
  const options = Array.from({ length: max - min + 1 }, (_, i) => min + i);
  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium">{label}</legend>
      <div className="flex flex-wrap gap-1.5" role="radiogroup">
        {options.map((n) => (
          <button
            key={n}
            type="button"
            role="radio"
            aria-checked={value === n}
            onClick={() => onChange(n)}
            className={`h-10 min-w-10 rounded-md border px-2 text-sm transition-colors ${
              value === n
                ? "border-primary bg-primary text-primary-foreground"
                : "hover:border-primary/50"
            }`}
          >
            {n}
          </button>
        ))}
      </div>
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{low}</span>
        <span>{high}</span>
      </div>
    </fieldset>
  );
}

function Pills({
  options,
  value,
  onChange,
}: {
  options: { value: string; label: string }[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2" role="radiogroup">
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={value === o.value}
          onClick={() => onChange(o.value)}
          className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
            value === o.value
              ? "border-primary bg-primary/10 font-medium text-primary"
              : "hover:border-primary/50"
          }`}
        >
          {o.label}
        </button>
      ))}
    </div>
  );
}

function OpenQuestion({
  id,
  label,
  value,
  onChange,
  placeholder,
}: {
  id: string;
  label: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
}) {
  return (
    <div className="space-y-2">
      <Label htmlFor={id}>{label}</Label>
      <Textarea
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={3}
        maxLength={5000}
        placeholder={placeholder}
      />
    </div>
  );
}

export default function TrialFeedbackPage() {
  // About you
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [role, setRole] = useState("");
  const [company, setCompany] = useState("");
  // Section A
  const [relevance, setRelevance] = useState<number | null>(null);
  const [hardestSystems, setHardestSystems] = useState("");
  const [concern, setConcern] = useState("");
  // Section B
  const [continueLikelihood, setContinueLikelihood] = useState<number | null>(null);
  const [topFeature, setTopFeature] = useState("");
  const [topFeatureReason, setTopFeatureReason] = useState("");
  const [localStorageImportance, setLocalStorageImportance] = useState<number | null>(null);
  // Section C
  const [priceBand, setPriceBand] = useState("");
  const [priceOther, setPriceOther] = useState("");
  const [nps, setNps] = useState<number | null>(null);
  const [other, setOther] = useState("");
  // Consent + testimonial
  const [researchConsent, setResearchConsent] = useState(false);
  const [quoteConsent, setQuoteConsent] = useState(false);
  const [testimonial, setTestimonial] = useState("");
  const [testimonialConsent, setTestimonialConsent] = useState(false);
  const [attribution, setAttribution] = useState("anonymous");

  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const ratings = [relevance, continueLikelihood, localStorageImportance, nps];
    if (ratings.some((r) => r === null)) {
      setError("Please answer the four rating questions (1, 4, 6 and 8).");
      return;
    }
    const wantsPublish = testimonialConsent && testimonial.trim().length > 0;
    if (wantsPublish) {
      if ((attribution === "full" || attribution === "name_role") && (!name.trim() || !role.trim())) {
        setError("Please add your name and role in section 1, or choose a different attribution.");
        return;
      }
      if (attribution === "full" && !company.trim()) {
        setError("Please add your company in section 1, or choose a different attribution.");
        return;
      }
      if (attribution === "role_company_type" && !role.trim()) {
        setError("Please add your role in section 1, or choose anonymous.");
        return;
      }
    }

    setSubmitting(true);
    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "/api"}/trial-feedback`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email,
          respondent_name: name || null,
          role: role || null,
          company_name: company || null,
          problem_relevance: relevance,
          hardest_systems: hardestSystems,
          biggest_concern: concern,
          continue_likelihood: continueLikelihood,
          top_feature: topFeature || null,
          top_feature_reason: topFeatureReason,
          local_storage_importance: localStorageImportance,
          price_band: priceBand || null,
          price_other: priceBand === "other" ? priceOther : null,
          nps,
          other_comments: other,
          research_consent: researchConsent,
          quote_consent: quoteConsent,
          testimonial: testimonial || null,
          testimonial_consent: testimonialConsent,
          testimonial_attribution: attribution,
        }),
      });
      if (!res.ok) throw new Error("Request failed");
      setSubmitted(true);
      window.scrollTo({ top: 0 });
    } catch {
      setError(
        "Something went wrong sending your feedback. Please try again, or email hello@unifiedlayer.io."
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="force-light flex min-h-screen flex-col bg-background text-foreground">
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Database className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">UnifiedLayer</span>
          </Link>
        </div>
      </header>

      <main className="relative flex-1 overflow-hidden bg-gradient-to-b from-primary/10 via-sky-50/60 to-background py-16">
        <div className="container max-w-2xl">
          <Link
            href="/"
            className="mb-6 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to home
          </Link>

          {submitted ? (
            <Card className="border shadow-xl shadow-primary/5">
              <CardHeader className="text-center">
                <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-primary/10">
                  <CheckCircle2 className="h-8 w-8 text-primary" />
                </div>
                <CardTitle className="font-display text-2xl">Thank you.</CardTitle>
                <CardDescription className="text-base">
                  Your feedback is with our team and shapes what we build next.
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4 text-center text-sm text-muted-foreground">
                {testimonialConsent && testimonial.trim() && (
                  <p>
                    We&apos;ll check your testimonial before anything goes on the site, and
                    it will only ever be credited the way you chose.
                  </p>
                )}
                <Link href="/" className="inline-block">
                  <Button variant="outline">Back to home</Button>
                </Link>
              </CardContent>
            </Card>
          ) : (
            <Card className="border shadow-xl shadow-primary/5">
              <CardHeader>
                <CardTitle className="font-display text-3xl">How was your trial?</CardTitle>
                <CardDescription className="space-y-2 text-base">
                  <span className="block">
                    Thank you for taking part in the UnifiedLayer trial. Your responses form part of
                    doctoral research at MASH International School of Business. All answers are
                    treated in strict confidence and are fully anonymised: your organisation will
                    never be named, and only a sector-and-size label is used in any analysis.
                  </span>
                  <span className="block">
                    Please answer as honestly as possible. Critical feedback is just as valuable to
                    this research as positive feedback. It takes about 5 minutes.
                  </span>
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit} className="space-y-8">
                  <SectionTitle step={1}>About you</SectionTitle>
                  <div className="space-y-2">
                    <Label htmlFor="email">Email you used for the trial</Label>
                    <Input
                      id="email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      required
                      placeholder="ada@acmepayments.com"
                    />
                    <p className="text-xs text-muted-foreground">
                      Only used to match your answers to your trial. Never published.
                    </p>
                  </div>
                  <div className="grid gap-4 sm:grid-cols-3">
                    <div className="space-y-2">
                      <Label htmlFor="name">Your name</Label>
                      <Input id="name" value={name} onChange={(e) => setName(e.target.value)} placeholder="Ada Obi" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="role">Your role</Label>
                      <Input id="role" value={role} onChange={(e) => setRole(e.target.value)} placeholder="Head of Finance" />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="company">Company</Label>
                      <Input id="company" value={company} onChange={(e) => setCompany(e.target.value)} placeholder="Acme Payments" />
                    </div>
                  </div>

                  <SectionTitle step={2}>A. The problem and the fit</SectionTitle>
                  <div className="space-y-6">
                    <Scale
                      label="1. How relevant is the data integration problem that UnifiedLayer addresses to your business?"
                      value={relevance}
                      onChange={setRelevance}
                      low="1 = Not relevant"
                      high="5 = Highly relevant"
                    />
                    <OpenQuestion
                      id="hardestSystems"
                      label="2. Which of your systems generate data that is currently hardest to bring together?"
                      value={hardestSystems}
                      onChange={setHardestSystems}
                      placeholder="e.g. Paystack, our core banking database and Excel"
                    />
                    <OpenQuestion
                      id="concern"
                      label="3. What is your biggest concern about adopting a platform like this?"
                      value={concern}
                      onChange={setConcern}
                    />
                  </div>

                  <SectionTitle step={3}>B. Value and priorities</SectionTitle>
                  <div className="space-y-6">
                    <Scale
                      label="4. After this trial, how likely are you to continue using UnifiedLayer?"
                      value={continueLikelihood}
                      onChange={setContinueLikelihood}
                      low="1 = Very unlikely"
                      high="5 = Very likely"
                    />
                    <fieldset className="space-y-2">
                      <legend className="text-sm font-medium">
                        5. Which feature mattered most to you during the trial? (Pick one)
                      </legend>
                      <div className="space-y-2">
                        {TOP_FEATURES.map((f) => (
                          <label
                            key={f.value}
                            className={`flex cursor-pointer items-center gap-3 rounded-md border p-3 text-sm transition-colors ${
                              topFeature === f.value ? "border-primary bg-primary/5 font-medium" : "hover:border-primary/50"
                            }`}
                          >
                            <input
                              type="radio"
                              name="topFeature"
                              value={f.value}
                              checked={topFeature === f.value}
                              onChange={() => setTopFeature(f.value)}
                              className="accent-[hsl(var(--primary))]"
                            />
                            <span>{f.label}</span>
                          </label>
                        ))}
                      </div>
                      <Textarea
                        aria-label="Why did that feature matter most? (optional)"
                        value={topFeatureReason}
                        onChange={(e) => setTopFeatureReason(e.target.value)}
                        rows={2}
                        maxLength={5000}
                        placeholder="Why? (optional)"
                      />
                    </fieldset>
                    <Scale
                      label="6. How important is it that your data is stored locally, in a location you control?"
                      value={localStorageImportance}
                      onChange={setLocalStorageImportance}
                      low="1 = Not important"
                      high="5 = Essential"
                    />
                  </div>

                  <SectionTitle step={4}>C. Pricing and recommendation</SectionTitle>
                  <div className="space-y-6">
                    <fieldset className="space-y-3">
                      <legend className="text-sm font-medium">
                        7. What would be an acceptable monthly price for your business to use this platform?
                      </legend>
                      <div className="space-y-1.5">
                        <p className="text-xs font-medium uppercase text-muted-foreground">Naira (₦)</p>
                        <Pills options={PRICE_BANDS_NGN} value={priceBand} onChange={setPriceBand} />
                      </div>
                      <div className="space-y-1.5">
                        <p className="text-xs font-medium uppercase text-muted-foreground">Euro (€)</p>
                        <Pills options={PRICE_BANDS_EUR} value={priceBand} onChange={setPriceBand} />
                      </div>
                      <Pills options={PRICE_OTHER} value={priceBand} onChange={setPriceBand} />
                      {priceBand === "other" && (
                        <Input
                          aria-label="Acceptable monthly price, with currency"
                          value={priceOther}
                          onChange={(e) => setPriceOther(e.target.value)}
                          maxLength={200}
                          placeholder="Amount and currency, e.g. KES 5,000 or GHS 400"
                        />
                      )}
                    </fieldset>
                    <Scale
                      label="8. How likely are you to recommend UnifiedLayer to another organisation?"
                      value={nps}
                      onChange={setNps}
                      min={0}
                      max={10}
                      low="0 = Not at all likely"
                      high="10 = Extremely likely"
                    />
                    <OpenQuestion
                      id="other"
                      label="Is there anything else you would like to add about your experience with the platform? (Optional)"
                      value={other}
                      onChange={setOther}
                    />
                  </div>

                  <SectionTitle step={5}>Testimonial (optional)</SectionTitle>
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="testimonial">
                        If you&apos;d recommend UnifiedLayer, a sentence or two we could share on our website
                      </Label>
                      <Textarea
                        id="testimonial"
                        value={testimonial}
                        onChange={(e) => setTestimonial(e.target.value)}
                        rows={3}
                        maxLength={600}
                        placeholder="e.g. We used to spend two days reconciling Paystack against our books. UnifiedLayer had it in one dashboard within a week."
                      />
                      <p className="text-right text-xs text-muted-foreground">{testimonial.length}/600</p>
                    </div>

                    <label className="flex cursor-pointer items-start gap-3 rounded-md border bg-muted/30 p-4 text-sm">
                      <Checkbox
                        checked={testimonialConsent}
                        onCheckedChange={(v) => setTestimonialConsent(v === true)}
                        className="mt-0.5"
                      />
                      <span className="text-muted-foreground">
                        <span className="font-medium text-foreground">Yes, UnifiedLayer may publish my testimonial</span>{" "}
                        on its website and marketing, credited as I choose below. We may
                        shorten it for length, but we won&apos;t change its meaning. You can ask
                        us to remove it at any time by emailing hello@unifiedlayer.io.
                      </span>
                    </label>

                    {testimonialConsent && (
                      <fieldset className="space-y-2">
                        <legend className="text-sm font-medium">How should we credit you?</legend>
                        <div className="space-y-2">
                          {ATTRIBUTION.map((a) => (
                            <label
                              key={a.value}
                              className={`flex cursor-pointer items-center gap-3 rounded-md border p-3 text-sm transition-colors ${
                                attribution === a.value ? "border-primary bg-primary/5 font-medium" : "hover:border-primary/50"
                              }`}
                            >
                              <input
                                type="radio"
                                name="attribution"
                                value={a.value}
                                checked={attribution === a.value}
                                onChange={() => setAttribution(a.value)}
                                className="accent-[hsl(var(--primary))]"
                              />
                              <span>{a.label}</span>
                            </label>
                          ))}
                        </div>
                      </fieldset>
                    )}
                    {!testimonialConsent && testimonial.trim() && (
                      <p className="text-xs text-muted-foreground">
                        Without the tick above, your words stay private and are used only as feedback.
                      </p>
                    )}
                  </div>

                  <SectionTitle step={6}>Research consent</SectionTitle>
                  <div className="space-y-3">
                    <label className="flex cursor-pointer items-start gap-3 rounded-md border bg-muted/30 p-4 text-sm">
                      <Checkbox
                        checked={researchConsent}
                        onCheckedChange={(v) => setResearchConsent(v === true)}
                        className="mt-0.5"
                      />
                      <span className="text-muted-foreground">
                        I agree that my answers may be used, anonymised, in the doctoral research
                        described in the{" "}
                        <Link href="/research-pilot" target="_blank" className="text-primary hover:underline">
                          participant information notice
                        </Link>
                        . Neither I nor my organisation will be named.
                      </span>
                    </label>
                    <label className="flex cursor-pointer items-start gap-3 rounded-md border bg-muted/30 p-4 text-sm">
                      <Checkbox
                        checked={quoteConsent}
                        onCheckedChange={(v) => setQuoteConsent(v === true)}
                        className="mt-0.5"
                      />
                      <span className="text-muted-foreground">
                        I agree that short, anonymised quotes from my written answers may appear in
                        the research, attributed only to a participant reference (e.g. &ldquo;P2,
                        digital payments, 11–50 staff&rdquo;).
                      </span>
                    </label>
                    <p className="text-xs text-muted-foreground">
                      Both are optional. Your feedback still counts without them.
                    </p>
                  </div>

                  {error && (
                    <p className="rounded-md border border-destructive/50 bg-destructive/10 p-3 text-sm text-destructive">
                      {error}
                    </p>
                  )}

                  <Button type="submit" size="lg" className="w-full" disabled={submitting}>
                    {submitting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Sending...
                      </>
                    ) : (
                      "Send my feedback"
                    )}
                  </Button>
                  <p className="text-center text-xs text-muted-foreground">
                    Your answers go only to the UnifiedLayer team. Your email is never published.
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
