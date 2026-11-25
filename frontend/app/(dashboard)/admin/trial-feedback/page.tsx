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
  ease_of_use: number;
  setup_experience: number;
  data_trust: number;
  value_rating: number;
  adoption_likelihood: number;
  nps: number;
  time_saved: string | null;
  willingness_to_pay: string | null;
  features_used: string[];
  problem_solved: string | null;
  most_valuable: string | null;
  biggest_frustration: string | null;
  missing_for_adoption: string | null;
  compared_to_before: string | null;
  other_comments: string | null;
  research_consent: boolean;
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
  ["problem_solved", "Problem hoped to solve, and did it?"],
  ["most_valuable", "Most useful"],
  ["biggest_frustration", "Frustrations"],
  ["missing_for_adoption", "Needed before adopting"],
  ["compared_to_before", "Compared with before"],
  ["other_comments", "Other"],
];

function npsSummary(items: FeedbackItem[]) {
  if (!items.length) return null;
  const promoters = items.filter((i) => i.nps >= 9).length;
  const detractors = items.filter((i) => i.nps <= 6).length;
  return Math.round(((promoters - detractors) / items.length) * 100);
}

function avg(items: FeedbackItem[], key: keyof FeedbackItem) {
  if (!items.length) return "-";
  return (items.reduce((s, i) => s + (i[key] as number), 0) / items.length).toFixed(1);
}

export default function TrialFeedbackAdminPage() {
  const { toast } = useToast();
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [drafts, setDrafts] = useState<Record<number, { label: string; display: string }>>({});

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/trial-feedback");
      setItems(res.data);
      setDrafts(
        Object.fromEntries(
          res.data.map((i: FeedbackItem) => [
            i.id,
            { label: i.participant_label || "", display: i.testimonial_display_text || i.testimonial || "" },
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

      <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-7">
        {[
          ["Responses", String(items.length)],
          ["NPS", nps === null ? "-" : String(nps)],
          ["Ease of use", avg(items, "ease_of_use")],
          ["Setup", avg(items, "setup_experience")],
          ["Data trust", avg(items, "data_trust")],
          ["Value", avg(items, "value_rating")],
          ["Adoption", avg(items, "adoption_likelihood")],
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
                <Badge variant="outline">NPS {i.nps}</Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4 text-sm">
              <div className="flex flex-wrap items-center gap-2">
                <span className="text-muted-foreground">Participant label</span>
                <Input
                  className="h-8 w-24"
                  value={drafts[i.id]?.label ?? ""}
                  placeholder="P1"
                  onChange={(e) => setDrafts((d) => ({ ...d, [i.id]: { ...d[i.id], label: e.target.value } }))}
                />
                <Button size="sm" variant="outline" onClick={() => patch(i.id, { participant_label: drafts[i.id]?.label || "" }, "Label saved")}>
                  Save
                </Button>
              </div>

              <p className="text-muted-foreground">
                Ease {i.ease_of_use}/5 · Setup {i.setup_experience}/5 · Trust {i.data_trust}/5 · Value{" "}
                {i.value_rating}/5 · Adoption {i.adoption_likelihood}/5 · Time saved: {i.time_saved || "-"} · Would
                pay: {i.willingness_to_pay || "-"}
                {i.features_used?.length ? ` · Used: ${i.features_used.join(", ")}` : ""}
              </p>

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
