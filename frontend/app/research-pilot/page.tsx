import Link from "next/link";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Database, ArrowLeft, ArrowRight, CheckCircle2 } from "lucide-react";

export const metadata = {
  title: "Fintech SME Research Pilot | UnifiedLayer",
  description:
    "UnifiedLayer is recruiting a limited cohort of fintech SMEs in Nigeria and France for a 15-day guided data-integration trial, as part of a Doctorate in Business Administration research project.",
};

const ELIGIBILITY = [
  "You are a digital payment provider, mobile wallet platform, micro-lender, or another fintech-oriented SME",
  "You operate in Nigeria, or you are connected to the Francophone African fintech ecosystem through France",
  "Your business already generates real operational or transactional data",
  "You use at least two active digital systems (e.g. Paystack + spreadsheets, M-Pesa + a database)",
  "You are willing to complete a short pre-trial and post-trial assessment",
];

const PARTICIPATION_STEPS = [
  {
    step: "1",
    title: "Access request",
    body: "You fill the same short form as every trial applicant, ticking the research-consent box.",
  },
  {
    step: "2",
    title: "Discovery call",
    body: "A 15–20 minute conversation about your data setup, so we both confirm the trial is worth your time.",
  },
  {
    step: "3",
    title: "15-day guided trial",
    body: "You use UnifiedLayer on your real data with hands-on onboarding support throughout.",
  },
  {
    step: "4",
    title: "Structured feedback",
    body: "A short questionnaire at the end. Your answers become anonymised data points in the research.",
  },
];

const RIGHTS = [
  "Participation is entirely voluntary — you can decline or withdraw at any time, without giving a reason, and withdrawal does not affect any commercial relationship with UnifiedLayer",
  "Your organisation is anonymised in all research outputs: the thesis refers to participants only by sector and size labels (e.g. \"a Nigerian payment provider, 11–50 staff\"), never by name",
  "Anonymised quotes from calls or feedback forms may appear in the thesis; you can ask for any quote to be excluded",
  "We collect: your form answers, discovery-call notes, platform usage measures (e.g. sources connected, rows synced), and your questionnaire responses. We do not analyse the contents of your business data for research",
  "Research records are kept securely for the duration of the doctoral programme and deleted afterwards",
  "Calls are not recorded unless you explicitly agree beforehand",
];

export default function ResearchPilotPage() {
  return (
    <div className="force-light flex min-h-screen flex-col bg-background text-foreground">
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="container flex h-16 items-center justify-between">
          <Link href="/" className="flex items-center gap-2">
            <Database className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">UnifiedLayer</span>
          </Link>
          <nav className="flex items-center gap-4">
            <Link href="/request-access">
              <Button size="sm">Request Access</Button>
            </Link>
          </nav>
        </div>
      </header>

      <main className="flex-1 bg-gradient-to-b from-primary/10 via-sky-50/60 to-background py-16">
        <div className="container max-w-3xl">
          <Link
            href="/"
            className="mb-6 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to home
          </Link>

          <Badge variant="secondary" className="mb-4">
            DBA Phase 2 Research Pilot
          </Badge>
          <h1 className="mb-4 font-display text-3xl font-bold tracking-tight sm:text-4xl">
            Fintech SME Research Pilot
          </h1>
          <p className="mb-10 text-lg text-muted-foreground">
            UnifiedLayer is recruiting a limited cohort of fintech SMEs in
            Nigeria and France to take part in a 15-day guided
            data-integration trial. The trial is part of a Doctorate in
            Business Administration (DBA) research project studying how
            Africa-centric data infrastructure serves fintech SMEs. This page
            is the participant information notice — please read it before
            applying.
          </p>

          {/* Eligibility */}
          <section className="mb-10">
            <h2 className="mb-4 font-display text-xl font-semibold">
              Who can take part
            </h2>
            <ul className="space-y-3">
              {ELIGIBILITY.map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                  <span className="text-muted-foreground">{item}</span>
                </li>
              ))}
            </ul>
          </section>

          {/* What participation involves */}
          <section className="mb-10">
            <h2 className="mb-4 font-display text-xl font-semibold">
              What participation involves
            </h2>
            <div className="grid gap-4 sm:grid-cols-2">
              {PARTICIPATION_STEPS.map((s) => (
                <div key={s.step} className="rounded-lg border bg-card p-4">
                  <div className="mb-2 flex items-center gap-2">
                    <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary text-xs font-semibold text-primary-foreground">
                      {s.step}
                    </span>
                    <h3 className="font-medium">{s.title}</h3>
                  </div>
                  <p className="text-sm text-muted-foreground">{s.body}</p>
                </div>
              ))}
            </div>
            <p className="mt-4 text-sm text-muted-foreground">
              The trial itself is free, and the guided onboarding means our
              team helps you connect your first sources. What we ask in
              return is honest feedback and about an hour of your time
              across the calls and questionnaires.
            </p>
          </section>

          {/* Rights and data */}
          <section className="mb-10">
            <h2 className="mb-4 font-display text-xl font-semibold">
              Your rights and how research data is handled
            </h2>
            <ul className="space-y-3">
              {RIGHTS.map((item) => (
                <li key={item} className="flex items-start gap-3 text-sm">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-primary" />
                  <span className="text-muted-foreground">{item}</span>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-sm text-muted-foreground">
              Before a trial begins, participating organisations receive a
              full consent form covering these points in detail. Questions
              about the study at any time:{" "}
              <a
                href="mailto:hello@unifiedlayer.io"
                className="text-primary hover:underline"
              >
                hello@unifiedlayer.io
              </a>
              .
            </p>
          </section>

          {/* CTA */}
          <div className="rounded-lg border bg-card p-6 text-center shadow-xl shadow-primary/5">
            <h2 className="mb-2 font-display text-xl font-semibold">
              Ready to take part?
            </h2>
            <p className="mb-4 text-sm text-muted-foreground">
              Fill the access request form and tick the research-consent box.
              We&apos;ll be in touch to book the discovery call.
            </p>
            <Link href="/request-access">
              <Button size="lg">
                Apply for the pilot
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </Link>
          </div>
        </div>
      </main>
    </div>
  );
}
