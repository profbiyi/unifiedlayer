"use client";

import { Fragment, useCallback, useEffect, useState } from "react";
import Link from "next/link";
import api from "@/lib/api-client";
import { useToast } from "@/hooks/use-toast";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import {
  ArrowLeft,
  CheckCircle2,
  Copy,
  Inbox,
  KeyRound,
  Loader2,
  Mail,
  RefreshCw,
  Rocket,
  Trash2,
  UserPlus,
} from "lucide-react";

// Onboarding is only meaningful once a lead has been vetted on a call.
const ONBOARDABLE_STATUSES = new Set(["qualified", "trial_active"]);

interface OnboardResult {
  organization_id: number;
  organization_slug: string;
  admin_email: string;
  admin_username: string;
  temporary_password: string;
  message: string;
}

interface AccessRequestItem {
  id: number;
  company_name: string;
  contact_name: string;
  email: string;
  country: string;
  sector: string;
  company_size: string | null;
  digital_systems: string[];
  data_problem: string;
  research_consent: boolean;
  status: string;
  notes: string | null;
  created_at: string;
}

// Gated trial funnel: request → discovery call → guided trial
const STATUSES = [
  { value: "new", label: "New" },
  { value: "contacted", label: "Contacted" },
  { value: "discovery_scheduled", label: "Discovery Scheduled" },
  { value: "qualified", label: "Qualified" },
  { value: "trial_active", label: "Trial Active" },
  { value: "declined", label: "Declined" },
];

const STATUS_COLORS: Record<string, string> = {
  new: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-100",
  contacted: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-100",
  discovery_scheduled: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-100",
  qualified: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-100",
  trial_active: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900 dark:text-emerald-100",
  declined: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-100",
};

const SECTOR_LABELS: Record<string, string> = {
  digital_payments: "Digital payments",
  mobile_wallet: "Mobile wallet",
  micro_lending: "Micro-lending",
  other_fintech: "Other fintech",
  retail: "Retail",
  other: "Other",
};

export default function AccessRequestsPage() {
  const { toast } = useToast();
  const [requests, setRequests] = useState<AccessRequestItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [noteDraft, setNoteDraft] = useState("");
  const [savingNote, setSavingNote] = useState(false);
  const [onboardingId, setOnboardingId] = useState<number | null>(null);
  const [onboardResult, setOnboardResult] = useState<OnboardResult | null>(null);
  const [confirmTarget, setConfirmTarget] = useState<AccessRequestItem | null>(null);
  const [planChoice, setPlanChoice] = useState<string>("professional");

  const fetchRequests = useCallback(async () => {
    setLoading(true);
    try {
      const response = await api.get("/access-requests");
      setRequests(response.data);
    } catch {
      toast({
        title: "Error",
        description: "Failed to load access requests.",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  }, [toast]);

  useEffect(() => {
    fetchRequests();
  }, [fetchRequests]);

  const deleteRequest = async (id: number, company: string) => {
    if (
      !confirm(
        `Permanently delete the request from "${company}"? Real leads should be marked Declined instead so the funnel history stays complete.`
      )
    ) {
      return;
    }
    try {
      await api.delete(`/access-requests/${id}`);
      setRequests((prev) => prev.filter((r) => r.id !== id));
      toast({ title: "Deleted", description: `Request from ${company} removed.` });
    } catch {
      toast({
        title: "Error",
        description: "Failed to delete the request.",
        variant: "destructive",
      });
    }
  };

  const updateRequest = async (
    id: number,
    changes: { status?: string; notes?: string }
  ) => {
    try {
      const response = await api.patch(`/access-requests/${id}`, changes);
      setRequests((prev) =>
        prev.map((r) => (r.id === id ? { ...r, ...response.data } : r))
      );
      toast({ title: "Updated", description: "Access request updated." });
    } catch {
      toast({
        title: "Error",
        description: "Failed to update the request.",
        variant: "destructive",
      });
    }
  };

  const openOnboardConfirm = (r: AccessRequestItem) => {
    setPlanChoice("professional");
    setConfirmTarget(r);
  };

  const confirmOnboard = async () => {
    const r = confirmTarget;
    if (!r) return;
    setOnboardingId(r.id);
    try {
      const response = await api.post(`/access-requests/${r.id}/onboard`, {
        subscription_plan: planChoice,
      });
      const result: OnboardResult = response.data;
      setConfirmTarget(null);
      setOnboardResult(result);
      // reflect the new status locally
      setRequests((prev) =>
        prev.map((x) => (x.id === r.id ? { ...x, status: "trial_active" } : x))
      );
      toast({
        title: "Onboarded",
        description: `${r.company_name} now has an account.`,
      });
    } catch (err: any) {
      toast({
        title: "Could not onboard",
        description:
          err?.response?.data?.detail ||
          "Failed to onboard this request. Please try again.",
        variant: "destructive",
      });
    } finally {
      setOnboardingId(null);
    }
  };

  const counts = STATUSES.reduce<Record<string, number>>((acc, s) => {
    acc[s.value] = requests.filter((r) => r.status === s.value).length;
    return acc;
  }, {});

  const visible =
    statusFilter === "all"
      ? requests
      : requests.filter((r) => r.status === statusFilter);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <Link
            href="/admin"
            className="mb-1 inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Admin
          </Link>
          <h1 className="text-3xl font-bold tracking-tight">Access Requests</h1>
          <p className="text-muted-foreground">
            Trial requests from the public form — each one is a research data
            point. Move them through the funnel: discovery call → guided trial.
          </p>
        </div>
        <Button variant="outline" onClick={fetchRequests} disabled={loading}>
          <RefreshCw className="mr-2 h-4 w-4" />
          Refresh
        </Button>
      </div>

      {/* Funnel counts */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {STATUSES.map((s) => (
          <Card
            key={s.value}
            className={`cursor-pointer transition-colors ${
              statusFilter === s.value ? "border-primary" : ""
            }`}
            onClick={() =>
              setStatusFilter(statusFilter === s.value ? "all" : s.value)
            }
          >
            <CardHeader className="p-4 pb-1">
              <CardTitle className="text-xs font-medium text-muted-foreground">
                {s.label}
              </CardTitle>
            </CardHeader>
            <CardContent className="p-4 pt-0">
              <span className="text-2xl font-bold">{counts[s.value] ?? 0}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      {loading ? (
        <div className="flex h-64 items-center justify-center">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : visible.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center gap-2 py-16 text-center">
            <Inbox className="h-10 w-10 text-muted-foreground" />
            <p className="font-medium">
              {statusFilter === "all"
                ? "No access requests yet"
                : `No requests with status "${statusFilter.replace("_", " ")}"`}
            </p>
            <p className="text-sm text-muted-foreground">
              New submissions from unifiedlayer.io/request-access will appear
              here (you also get an email).
            </p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Company</TableHead>
                  <TableHead>Contact</TableHead>
                  <TableHead>Country</TableHead>
                  <TableHead>Sector</TableHead>
                  <TableHead>Systems</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Received</TableHead>
                  <TableHead className="w-10" />
                </TableRow>
              </TableHeader>
              <TableBody>
                {visible.map((r) => (
                  <Fragment key={r.id}>
                    <TableRow
                      className="cursor-pointer"
                      onClick={() => {
                        setExpandedId(expandedId === r.id ? null : r.id);
                        setNoteDraft(r.notes || "");
                      }}
                    >
                      <TableCell className="font-medium">
                        {r.company_name}
                        {r.research_consent && (
                          <Badge variant="outline" className="ml-2 border-primary/40 text-primary text-[10px]">
                            Research pilot
                          </Badge>
                        )}
                        {r.company_size && (
                          <span className="block text-xs text-muted-foreground">
                            {r.company_size} people
                          </span>
                        )}
                      </TableCell>
                      <TableCell>
                        {r.contact_name}
                        <span className="block text-xs text-muted-foreground">
                          {r.email}
                        </span>
                      </TableCell>
                      <TableCell>{r.country}</TableCell>
                      <TableCell>{SECTOR_LABELS[r.sector] || r.sector}</TableCell>
                      <TableCell>
                        <div className="flex max-w-[220px] flex-wrap gap-1">
                          {r.digital_systems.slice(0, 3).map((s) => (
                            <Badge key={s} variant="secondary" className="text-xs">
                              {s.split(" (")[0]}
                            </Badge>
                          ))}
                          {r.digital_systems.length > 3 && (
                            <Badge variant="outline" className="text-xs">
                              +{r.digital_systems.length - 3}
                            </Badge>
                          )}
                        </div>
                      </TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        <Select
                          value={r.status}
                          onValueChange={(value) =>
                            updateRequest(r.id, { status: value })
                          }
                        >
                          <SelectTrigger className="h-8 w-[170px]">
                            <SelectValue>
                              <Badge className={STATUS_COLORS[r.status] || ""}>
                                {r.status.replace("_", " ")}
                              </Badge>
                            </SelectValue>
                          </SelectTrigger>
                          <SelectContent>
                            {STATUSES.map((s) => (
                              <SelectItem key={s.value} value={s.value}>
                                {s.label}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {new Date(r.created_at).toLocaleDateString("en-GB", {
                          day: "numeric",
                          month: "short",
                        })}
                      </TableCell>
                      <TableCell onClick={(e) => e.stopPropagation()}>
                        {(() => {
                          const eligible = ONBOARDABLE_STATUSES.has(r.status);
                          return (
                            <div className="flex items-center justify-end gap-1">
                              <TooltipProvider delayDuration={200}>
                                <Tooltip>
                                  <TooltipTrigger asChild>
                                    {/* span keeps the tooltip working while the button is disabled */}
                                    <span tabIndex={0}>
                                      <Button
                                        variant={eligible ? "default" : "outline"}
                                        size="sm"
                                        className="h-8"
                                        onClick={() => openOnboardConfirm(r)}
                                        disabled={!eligible || onboardingId === r.id}
                                        aria-label={`Onboard ${r.company_name}`}
                                      >
                                        {onboardingId === r.id ? (
                                          <Loader2 className="h-4 w-4 animate-spin" />
                                        ) : (
                                          <Rocket className="h-4 w-4" />
                                        )}
                                        <span className="ml-1.5 hidden sm:inline">
                                          Onboard
                                        </span>
                                      </Button>
                                    </span>
                                  </TooltipTrigger>
                                  <TooltipContent>
                                    {eligible
                                      ? "Create their organization + admin login"
                                      : "Mark this request Qualified after your call to enable onboarding"}
                                  </TooltipContent>
                                </Tooltip>
                              </TooltipProvider>
                              <Button
                                variant="ghost"
                                size="sm"
                                className="h-8 w-8 p-0 text-muted-foreground hover:text-destructive"
                                onClick={() => deleteRequest(r.id, r.company_name)}
                                aria-label={`Delete request from ${r.company_name}`}
                              >
                                <Trash2 className="h-4 w-4" />
                              </Button>
                            </div>
                          );
                        })()}
                      </TableCell>
                    </TableRow>
                    {expandedId === r.id && (
                      <TableRow>
                        <TableCell colSpan={8} className="bg-muted/30">
                          <div className="space-y-4 p-2">
                            <div>
                              <p className="mb-1 text-sm font-medium">
                                Data problem
                              </p>
                              <p className="text-sm text-muted-foreground">
                                {r.data_problem}
                              </p>
                            </div>
                            <div>
                              <p className="mb-1 text-sm font-medium">
                                All systems ({r.digital_systems.length})
                              </p>
                              <div className="flex flex-wrap gap-1">
                                {r.digital_systems.map((s) => (
                                  <Badge
                                    key={s}
                                    variant="secondary"
                                    className="text-xs"
                                  >
                                    {s}
                                  </Badge>
                                ))}
                              </div>
                            </div>
                            <div>
                              <p className="mb-1 text-sm font-medium">
                                Internal notes (discovery call outcome, next steps)
                              </p>
                              <Textarea
                                value={noteDraft}
                                onChange={(e) => setNoteDraft(e.target.value)}
                                rows={3}
                                placeholder="e.g. Call booked for Thursday. Uses Paystack + spreadsheets, strong fit."
                              />
                              <Button
                                size="sm"
                                className="mt-2"
                                disabled={savingNote}
                                onClick={async () => {
                                  setSavingNote(true);
                                  await updateRequest(r.id, { notes: noteDraft });
                                  setSavingNote(false);
                                }}
                              >
                                {savingNote ? (
                                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                                ) : null}
                                Save notes
                              </Button>
                            </div>
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </Fragment>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}

      {/* Confirm onboarding */}
      <Dialog
        open={confirmTarget !== null}
        onOpenChange={(open) => !open && onboardingId === null && setConfirmTarget(null)}
      >
        <DialogContent>
          <DialogHeader>
            <div className="flex items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10 text-primary">
                <Rocket className="h-5 w-5" />
              </span>
              <DialogTitle className="text-lg">
                Onboard {confirmTarget?.company_name}
              </DialogTitle>
            </div>
            <DialogDescription>
              Spin up their workspace and admin login from this request — no manual
              re-entry.
            </DialogDescription>
          </DialogHeader>

          {confirmTarget && (
            <div className="space-y-4">
              <div className="rounded-lg border bg-muted/40 p-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">Contact</span>
                  <span className="font-medium">{confirmTarget.contact_name}</span>
                </div>
                <div className="mt-1 flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">Admin login</span>
                  <span className="font-mono text-xs">{confirmTarget.email}</span>
                </div>
                <div className="mt-1 flex items-center justify-between gap-3">
                  <span className="text-muted-foreground">Country · Sector</span>
                  <span className="font-medium">
                    {confirmTarget.country} ·{" "}
                    {SECTOR_LABELS[confirmTarget.sector] || confirmTarget.sector}
                  </span>
                </div>
              </div>

              <div className="space-y-1.5">
                <label className="text-sm font-medium">Trial plan</label>
                <Select value={planChoice} onValueChange={setPlanChoice}>
                  <SelectTrigger className="h-9">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="starter">Starter</SelectItem>
                    <SelectItem value="professional">Professional</SelectItem>
                    <SelectItem value="enterprise">Enterprise</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <ul className="space-y-1.5 text-sm text-muted-foreground">
                {[
                  "Creates their organization + an ORG_ADMIN login",
                  "Emails them a welcome message with the temporary password",
                  "Marks this request as Trial Active",
                ].map((line) => (
                  <li key={line} className="flex items-start gap-2">
                    <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-500" />
                    {line}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setConfirmTarget(null)}
              disabled={onboardingId !== null}
            >
              Cancel
            </Button>
            <Button onClick={confirmOnboard} disabled={onboardingId !== null}>
              {onboardingId !== null ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating…
                </>
              ) : (
                <>
                  <Rocket className="mr-2 h-4 w-4" />
                  Create account
                </>
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Result: generated credentials */}
      <Dialog
        open={onboardResult !== null}
        onOpenChange={(open) => !open && setOnboardResult(null)}
      >
        <DialogContent>
          <DialogHeader>
            <div className="flex items-center gap-2">
              <span className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600 dark:text-emerald-400">
                <CheckCircle2 className="h-5 w-5" />
              </span>
              <DialogTitle className="text-lg">Account created</DialogTitle>
            </div>
            <DialogDescription>
              {onboardResult?.message} Share these if the email doesn&apos;t arrive —
              the temporary password is shown only once.
            </DialogDescription>
          </DialogHeader>
          {onboardResult && (
            <div className="divide-y rounded-lg border text-sm">
              {([
                ["Login email", onboardResult.admin_email, Mail],
                ["Username", onboardResult.admin_username, UserPlus],
                ["Temporary password", onboardResult.temporary_password, KeyRound],
                ["Organization", onboardResult.organization_slug, Rocket],
              ] as [string, string, typeof Mail][]).map(([label, value, Icon]) => (
                <div
                  key={label}
                  className="flex items-center justify-between gap-3 px-3 py-2"
                >
                  <span className="flex items-center gap-2 text-muted-foreground">
                    <Icon className="h-4 w-4" />
                    {label}
                  </span>
                  <span className="flex items-center gap-2 font-mono text-xs">
                    {value}
                    <button
                      type="button"
                      className="text-muted-foreground hover:text-foreground"
                      onClick={() => {
                        navigator.clipboard?.writeText(value);
                        toast({ title: "Copied", description: `${label} copied.` });
                      }}
                      aria-label={`Copy ${label}`}
                    >
                      <Copy className="h-3.5 w-3.5" />
                    </button>
                  </span>
                </div>
              ))}
            </div>
          )}
          <DialogFooter>
            <Button onClick={() => setOnboardResult(null)}>Done</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
