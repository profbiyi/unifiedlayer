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

const FEATURES = [
  "Connecting data sources",
  "Scheduled syncs / pipelines",
  "Dashboards and reports",
  "Data quality checks",
  "SQL transformations",
  "AI assistant / insights",
  "Exports to a warehouse or spreadsheet",
  "Alerts and notifications",
];

const TIME_SAVED = [
  "None yet",
  "Under 1 hour",
  "1-3 hours",
  "3-8 hours",
  "More than 8 hours",
  "Not sure",
];

const WTP = [
  "Would not pay",
  "Under $50 / month",
  "$50-150 / month",
  "$150-300 / month",
  "Over $300 / month",
  "Not sure",
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

function Choice({
  label,
  options,
  value,
  onChange,
}: {
  label: string;
  options: string[];
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <fieldset className="space-y-2">
      <legend className="text-sm font-medium">{label}</legend>
      <div className="flex flex-wrap gap-2">
        {options.map((o) => (
          <button
            key={o}
            type="button"
            onClick={() => onChange(o)}
            className={`rounded-full border px-3 py-1.5 text-sm transition-colors ${
              value === o
                ? "border-primary bg-primary/10 font-medium text-primary"
                : "hover:border-primary/50"
            }`}
          >
            {o}
          </button>
        ))}
      </div>
    </fieldset>
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
  // Ratings
  const [easeOfUse, setEaseOfUse] = useState<number | null>(null);
  const [setup, setSetup] = useState<number | null>(null);
  const [dataTrust, setDataTrust] = useState<number | null>(null);
  const [value, setValue] = useState<number | null>(null);
  const [adoption, setAdoption] = useState<number | null>(null);
  const [nps, setNps] = useState<number | null>(null);
  const [timeSaved, setTimeSaved] = useState("");
  const [wtp, setWtp] = useState("");
  const [features, setFeatures] = useState<string[]>([]);
  // Open questions
  const [problemSolved, setProblemSolved] = useState("");
  const [mostValuable, setMostValuable] = useState("");
  const [frustration, setFrustration] = useState("");
  const [missing, setMissing] = useState("");
  const [compared, setCompared] = useState("");
  const [other, setOther] = useState("");
  // Consent + testimonial
  const [researchConsent, setResearchConsent] = useState(false);
  const [testimonial, setTestimonial] = useState("");
  const [testimonialConsent, setTestimonialConsent] = useState(false);
  const [attribution, setAttribution] = useState("anonymous");

  const [submitting, setSubmitting] = useState(false);
  const [submitted, setSubmitted] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggleFeature = (f: string) =>
    setFeatures((prev) => (prev.includes(f) ? prev.filter((x) => x !== f) : [...prev, f]));

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);

    const ratings = [easeOfUse, setup, dataTrust, value, adoption, nps];
    if (ratings.some((r) => r === null)) {
      setError("Please answer all the rating questions in section 2.");
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
          ease_of_use: easeOfUse,
          setup_experience: setup,
          data_trust: dataTrust,
          value_rating: value,
          adoption_likelihood: adoption,
          nps,
          time_saved: timeSaved || null,
          willingness_to_pay: wtp || null,
          features_used: features,
          problem_solved: problemSolved,
          most_valuable: mostValuable,
          biggest_frustration: frustration,
          missing_for_adoption: missing,
          compared_to_before: compared,
          other_comments: other,
          research_consent: researchConsent,
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
                <CardDescription className="text-base">
                  Thanks for testing UnifiedLayer. This takes about 8 minutes. Honest
                  answers help most, including what didn&apos;t work. Only your email
                  and the rating questions are required.
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

                  <SectionTitle step={2}>Your ratings</SectionTitle>
                  <div className="space-y-6">
                    <Scale label="How easy was UnifiedLayer to use?" value={easeOfUse} onChange={setEaseOfUse} low="Very difficult" high="Very easy" />
                    <Scale label="How smooth was connecting your data sources and getting set up?" value={setup} onChange={setSetup} low="Very difficult" high="Very smooth" />
                    <Scale label="How much do you trust the data and numbers it produced?" value={dataTrust} onChange={setDataTrust} low="Not at all" high="Completely" />
                    <Scale label="How valuable would UnifiedLayer be to your business?" value={value} onChange={setValue} low="Not valuable" high="Extremely valuable" />
                    <Scale label="How likely is your team to keep using it or adopt it after the trial?" value={adoption} onChange={setAdoption} low="Very unlikely" high="Very likely" />
                    <Scale
                      label="How likely are you to recommend UnifiedLayer to a colleague or another business?"
                      value={nps}
                      onChange={setNps}
                      min={0}
                      max={10}
                      low="0 = Not at all likely"
                      high="10 = Extremely likely"
                    />
                    <Choice label="Roughly how much time per week could it save your team on data work?" options={TIME_SAVED} value={timeSaved} onChange={setTimeSaved} />
                    <Choice label="What would you realistically pay for it per month?" options={WTP} value={wtp} onChange={setWtp} />
                    <fieldset className="space-y-2">
                      <legend className="text-sm font-medium">Which parts did you use during the trial?</legend>
                      <div className="grid gap-2 sm:grid-cols-2">
                        {FEATURES.map((f) => {
                          const selected = features.includes(f);
                          return (
                            <label
                              key={f}
                              className={`flex cursor-pointer items-center gap-2 rounded-md border p-3 text-sm transition-colors ${
                                selected ? "border-primary bg-primary/5 font-medium" : "hover:border-primary/50"
                              }`}
                            >
                              <Checkbox checked={selected} onCheckedChange={() => toggleFeature(f)} />
                              <span>{f}</span>
                            </label>
                          );
                        })}
                      </div>
                    </fieldset>
                  </div>

                  <SectionTitle step={3}>In your own words</SectionTitle>
                  <div className="space-y-5">
                    <OpenQuestion id="problemSolved" label="What problem did you hope UnifiedLayer would solve, and did it?" value={problemSolved} onChange={setProblemSolved} />
                    <OpenQuestion id="mostValuable" label="What was the most useful thing it did for you?" value={mostValuable} onChange={setMostValuable} />
                    <OpenQuestion id="frustration" label="What frustrated you or got in the way?" value={frustration} onChange={setFrustration} />
                    <OpenQuestion id="missing" label="What would need to change, or be added, before you'd adopt it?" value={missing} onChange={setMissing} placeholder="e.g. a connector we use, pricing in naira, on-site support, security sign-off" />
                    <OpenQuestion id="compared" label="How does it compare with how you handled this data before the trial?" value={compared} onChange={setCompared} />
                    <OpenQuestion id="other" label="Anything else you'd like to tell us?" value={other} onChange={setOther} />
                  </div>

                  <SectionTitle step={4}>Testimonial (optional)</SectionTitle>
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

                  <SectionTitle step={5}>Research consent</SectionTitle>
                  <label className="flex cursor-pointer items-start gap-3 rounded-md border bg-muted/30 p-4 text-sm">
                    <Checkbox
                      checked={researchConsent}
                      onCheckedChange={(v) => setResearchConsent(v === true)}
                      className="mt-0.5"
                    />
                    <span className="text-muted-foreground">
                      I agree that my answers may be used, anonymised, in the fintech SME
                      research study described in the{" "}
                      <Link href="/research-pilot" target="_blank" className="text-primary hover:underline">
                        participant information notice
                      </Link>
                      . Neither I nor my company will be named in it.{" "}
                      <span className="text-xs">(Optional: your feedback still counts without this.)</span>
                    </span>
                  </label>

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
