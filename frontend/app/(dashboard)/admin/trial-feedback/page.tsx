"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import api from "@/lib/api-client";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, Check, Download, Inbox, Loader2, RefreshCw, X } from "lucide-react";

interface FeedbackItem {
  id: number;
  email: string;
  respondent_name: string | null;
  role: string | null;
  company_name: string | null;
  participant_label: string | null;
  sector_label: string | null;
  size_label: string | null;
  problem_relevance: number | null;
  hardest_systems: string | null;
  biggest_concern: string | null;
  continue_likelihood: number | null;
  top_feature: string | null;
  top_feature_reason: string | null;
  local_storage_importance: number | null;
  price_band: string | null;
  price_other: string | null;
  nps: number;
  other_comments: string | null;
  research_consent: boolean;
  quote_consent: boolean;
  testimonial: string | null;
  testimonial_consent: boolean;
  testimonial_attribution: string;
  testimonial_status: string;
  testimonial_display_text: string | null;
  notes: string | null;
  created_at: string;
}

const ATTRIBUTION_LABELS: Record<string, string> = {
  full: "Name, role, company",
  name_role: "Name and role",
  role_company_type: "Role only",
  anonymous: "Anonymous",
};

const OPEN_QUESTIONS: [keyof FeedbackItem, string][] = [
  ["hardest_systems", "Q2. Hardest systems to bring together"],
  ["biggest_concern", "Q3. Biggest concern about adopting"],
  ["top_feature_reason", "Q5. Why that feature"],
  ["other_comments", "Anything else"],
];

const FEATURE_LABELS: Record<string, string> = {
  connecting_sources: "Connecting data sources",
  data_location: "Controlling where data is stored",
  dashboards: "Dashboards and reporting",
  ai_insights: "AI insights",
  local_connectors: "Local connectors",
};

const PRICE_LABELS: Record<string, string> = {
  ngn_under_25k: "Under ₦25k",
  ngn_25k_75k: "₦25k–75k",
  ngn_75k_150k: "₦75k–150k",
  ngn_150k_300k: "₦150k–300k",
  ngn_over_300k: "Over ₦300k",
  eur_under_25: "Under €25",
  eur_25_75: "€25–75",
  eur_75_150: "€75–150",
  eur_150_300: "€150–300",
  eur_over_300: "Over €300",
  would_not_pay: "Would not pay",
  other: "Other",
};

function npsSummary(items: FeedbackItem[]) {
  if (!items.length) return null;
  const promoters = items.filter((i) => i.nps >= 9).length;
  const detractors = items.filter((i) => i.nps <= 6).length;
  return Math.round(((promoters - detractors) / items.length) * 100);
}

function avg(items: FeedbackItem[], key: keyof FeedbackItem) {
  const vals = items.map((i) => i[key]).filter((v): v is number => typeof v === "number");
  if (!vals.length) return "-";
  return (vals.reduce((s, v) => s + v, 0) / vals.length).toFixed(1);
}

export default function TrialFeedbackAdminPage() {
  const { toast } = useToast();
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [drafts, setDrafts] = useState<
    Record<number, { label: string; sector: string; size: string; display: string }>
  >({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/trial-feedback");
      setItems(res.data);
      setDrafts(
        Object.fromEntries(
          res.data.map((i: FeedbackItem) => [
            i.id,
            {
              label: i.participant_label || "",
              sector: i.sector_label || "",
              size: i.size_label || "",
              display: i.testimonial_display_text || i.testimonial || "",
            },
          ])
        )
      );
    } catch {
      toast({ title: "Could not load feedback", variant: "destructive" });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    load();
  }, [load]);

  const patch = async (id: number, changes: Record<string, unknown>, ok: string) => {
    try {
      const res = await api.patch(`/trial-feedback/${id}`, changes);
      setItems((prev) => prev.map((i) => (i.id === id ? res.data : i)));
      toast({ title: ok });
    } catch (err: unknown) {
      const detail =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        "Update failed";
      toast({ title: detail, variant: "destructive" });
    }
  };

  const exportCsv = async () => {
    try {
      const res = await api.get("/trial-feedback/export.csv", { responseType: "blob" });
      const url = URL.createObjectURL(res.data);
      const a = document.createElement("a");
      a.href = url;
      a.download = "trial-feedback-anonymised.csv";
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      toast({ title: "Export failed", variant: "destructive" });
    }
  };

  const nps = npsSummary(items);

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <Link href="/admin" className="mb-2 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
            <ArrowLeft className="h-4 w-4" /> Admin
          </Link>
          <h1 className="text-3xl font-bold tracking-tight">Trial Feedback</h1>
          <p className="text-muted-foreground">
            Post-trial questionnaire responses and testimonials. Public form: /trial-feedback
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={load}>
            <RefreshCw className="mr-2 h-4 w-4" /> Refresh
          </Button>
          <Button onClick={exportCsv} disabled={!items.length}>
            <Download className="mr-2 h-4 w-4" /> Anonymised CSV
          </Button>
        </div>
      </div>

      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-5">
        {[
          ["Responses", String(items.length)],
          ["NPS (Q8)", nps === null ? "-" : String(nps)],
          ["Problem relevance (Q1)", avg(items, "problem_relevance")],
          ["Continue using (Q4)", avg(items, "continue_likelihood")],
          ["Local storage (Q6)", avg(items, "local_storage_importance")],
        ].map(([label, v]) => (
          <Card key={label}>
            <CardContent className="p-4">
              <p className="text-xs text-muted-foreground">{label}</p>
              <p className="text-2xl font-semibold">{v}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin" />
        </div>
      ) : !items.length ? (
        <Card>
          <CardContent className="flex flex-col items-center gap-2 py-12 text-muted-foreground">
            <Inbox className="h-8 w-8" />
            No feedback yet.
          </CardContent>
        </Card>
      ) : (
        items.map((i) => (
          <Card key={i.id}>
            <CardHeader className="flex flex-row flex-wrap items-start justify-between gap-2">
              <div>
                <CardTitle className="text-lg">
                  {i.participant_label ? `${i.participant_label} · ` : ""}
                  {i.company_name || i.email}
                </CardTitle>
                <p className="text-sm text-muted-foreground">
                  {[i.respondent_name, i.role, i.email].filter(Boolean).join(" · ")} ·{" "}
                  {new Date(i.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <Badge variant={i.research_consent ? "default" : "secondary"}>
                  {i.research_consent ? "Research consent" : "No research consent"}
                </Badge>
                <Badge variant={i.quote_consent ? "default" : "secondary"}>
                  {i.quote_consent ? "Quotes OK" : "No quotes"}
                </Badge>
                <Badge variant="outline">NPS {i.nps}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-muted-foreground">Research labels</span>
                <Input
                  className="h-8 w-20"
                  value={drafts[i.id]?.label ?? ""}
                  placeholder="P1"
                  aria-label="Participant reference"
                  onChange={(e) => setDrafts((d) => ({ ...d, [i.id]: { ...d[i.id], label: e.target.value } }))}
                />
                <Input
                  className="h-8 w-44"
                  value={drafts[i.id]?.sector ?? ""}
                  placeholder="Sector, e.g. Digital payments"
                  aria-label="Sector label"
                  onChange={(e) => setDrafts((d) => ({ ...d, [i.id]: { ...d[i.id], sector: e.target.value } }))}
                />
                <Input
                  className="h-8 w-28"
                  value={drafts[i.id]?.size ?? ""}
                  placeholder="Size, e.g. 11-50"
                  aria-label="Size label"
                  onChange={(e) => setDrafts((d) => ({ ...d, [i.id]: { ...d[i.id], size: e.target.value } }))}
                />
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() =>
                    patch(
                      i.id,
                      {
                        participant_label: drafts[i.id]?.label || "",
                        sector_label: drafts[i.id]?.sector || "",
                        size_label: drafts[i.id]?.size || "",
                      },
                      "Labels saved"
                    )
                  }
                >
                  Save
                </Button>
              </div>

              {i.problem_relevance !== null ? (
                <p className="text-muted-foreground">
                  Q1 relevance {i.problem_relevance}/5 · Q4 continue {i.continue_likelihood ?? "-"}/5 · Q5{" "}
                  {i.top_feature ? FEATURE_LABELS[i.top_feature] || i.top_feature : "-"} · Q6 local storage{" "}
                  {i.local_storage_importance ?? "-"}/5 · Q7{" "}
                  {i.price_band === "other" ? i.price_other || "Other" : i.price_band ? PRICE_LABELS[i.price_band] : "-"}
                  {" "}· Q8 NPS {i.nps}
                </p>
              ) : (
                <p className="text-muted-foreground">Submitted on the earlier draft form (NPS {i.nps}).</p>
              )}

              <dl className="grid gap-3 sm:grid-cols-2">
                {OPEN_QUESTIONS.filter(([k]) => i[k]).map(([k, label]) => (
                  <div key={k}>
                    <dt className="text-xs font-medium uppercase text-muted-foreground">{label}</dt>
                    <dd className="whitespace-pre-wrap">{i[k] as string}</dd>
                  </div>
                ))}
              </dl>

              {i.testimonial && (
                <div className="space-y-2 rounded-md border bg-muted/30 p-4">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-medium">Testimonial</span>
                    <Badge variant="outline">{i.testimonial_status}</Badge>
                    {i.testimonial_consent ? (
                      <Badge>Consent to publish · {ATTRIBUTION_LABELS[i.testimonial_attribution]}</Badge>
                    ) : (
                      <Badge variant="secondary">No consent: private feedback only</Badge>
                    )}
                  </div>
                  <p className="italic">&ldquo;{i.testimonial}&rdquo;</p>
                  {i.testimonial_consent && (
                    <>
                      <Textarea
                        rows={2}
                        maxLength={600}
                        value={drafts[i.id]?.display ?? ""}
                        onChange={(e) => setDrafts((d) => ({ ...d, [i.id]: { ...d[i.id], display: e.target.value } }))}
                      />
                      <p className="text-xs text-muted-foreground">
                        Text shown on the site. Shorten if needed, but keep the meaning.
                      </p>
                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          onClick={() =>
                            patch(
                              i.id,
                              { testimonial_status: "approved", testimonial_display_text: drafts[i.id]?.display || "" },
                              "Testimonial published"
                            )
                          }
                        >
                          <Check className="mr-1 h-4 w-4" /> Approve and publish
                        </Button>
                        <Button size="sm" variant="outline" onClick={() => patch(i.id, { testimonial_status: "rejected" }, "Testimonial hidden")}>
                          <X className="mr-1 h-4 w-4" /> Hide
                        </Button>
                      </div>
                    </>
                  )}
                </div>
              )}
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
}
