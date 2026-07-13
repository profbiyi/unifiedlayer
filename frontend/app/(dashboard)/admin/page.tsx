"use client";

import React, { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useToast } from "@/hooks/use-toast";
import {
  MoreVertical,
  Building2,
  Users,
  Workflow,
  Activity,
  AlertTriangle,
  Power,
  PlayCircle,
  PauseCircle,
  CheckCircle,
  Clock,
  Trash2,
  Plus,
  Eye,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Database,
  HardDrive,
} from "lucide-react";
import { useRouter } from "next/navigation";
import api from "@/lib/api-client";

interface Organization {
  id: number;
  public_id: string;
  name: string;
  slug: string;
  is_active: boolean;
  can_sync_data: boolean;
  subscription_plan: string;
  max_users: number;
  current_user_count: number;
  subscription_status: string;
  admin_onboarded: boolean;
  admin_onboarded_at: string | null;
  created_at: string;
}

interface PlatformStats {
  total_organizations: number;
  active_organizations: number;
  total_users: number;
  active_users: number;
  total_pipelines: number;
  total_runs_today: number;
  total_runs_this_week: number;
  total_runs_this_month: number;
  organizations_by_plan: {
    starter: number;
    professional: number;
    enterprise: number;
  };
}

interface CreateOrgForm {
  name: string;
  slug: string;
  description: string;
  country: string;
  subscription_plan: string;
  max_users: number;
  billing_email: string;
  admin_email: string;
  admin_username: string;
  admin_password: string;
  admin_full_name: string;
}

const initialFormState: CreateOrgForm = {
  name: "",
  slug: "",
  description: "",
  country: "",
  subscription_plan: "starter",
  max_users: 5,
  billing_email: "",
  admin_email: "",
  admin_username: "",
  admin_password: "",
  admin_full_name: "",
};

// Country decides the billing currency (purchasing-power pricing) —
// mirrors COUNTRY_CURRENCY in backend/models/billing.py
const ORG_COUNTRIES: { name: string; currency: string }[] = [
  { name: "Nigeria", currency: "NGN" },
  { name: "Kenya", currency: "KES" },
  { name: "Ghana", currency: "GHS" },
  { name: "United Kingdom", currency: "GBP" },
  { name: "France", currency: "EUR" },
];

const planLimits: Record<string, number> = {
  starter: 5,
  professional: 25,
  enterprise: 100,
};

interface OrgDetails {
  pipelines_count: number;
  sources_count: number;
  destinations_count: number;
  recent_runs_count: number;
}

interface RecentPipeline {
  id: number;
  name: string;
  is_active: boolean;
  last_run_status: string | null;
}

export default function AdminDashboard() {
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [stats, setStats] = useState<PlatformStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [onboardDialogOpen, setOnboardDialogOpen] = useState(false);
  const [onboardLoading, setOnboardLoading] = useState(false);
  const [onboardFormData, setOnboardFormData] = useState<CreateOrgForm>(initialFormState);
  const [onboardResult, setOnboardResult] = useState<{ organization: any; admin_user: any; message: string } | null>(null);
  const [expandedOrgs, setExpandedOrgs] = useState<Set<number>>(new Set());
  const [orgDetails, setOrgDetails] = useState<Record<number, OrgDetails>>({});
  const [orgPipelines, setOrgPipelines] = useState<Record<number, RecentPipeline[]>>({});
  const [deleteDialogOrg, setDeleteDialogOrg] = useState<Organization | null>(null);
  const [deleteConfirmName, setDeleteConfirmName] = useState("");
  const [deleteReason, setDeleteReason] = useState("");
  const [deleteLoading, setDeleteLoading] = useState(false);
  const { toast } = useToast();
  const router = useRouter();

  const fetchOrganizations = async () => {
    try {
      const response = await api.get("/admin/organizations");
      setOrganizations(response.data);
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to fetch organizations",
        variant: "destructive",
      });
    }
  };

  const fetchStats = async () => {
    try {
      const response = await api.get("/admin/stats");
      setStats(response.data);
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to fetch statistics",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrganizations();
    fetchStats();
  }, []);

  const generateSlug = (name: string) => {
    return name
      .toLowerCase()
      .replace(/[^a-z0-9\s-]/g, "")
      .replace(/\s+/g, "-")
      .replace(/-+/g, "-")
      .trim();
  };

  const handleOnboardOrganization = async (e: React.FormEvent) => {
    e.preventDefault();
    setOnboardLoading(true);
    setOnboardResult(null);

    try {
      // Convert empty strings to null for optional email fields
      const cleanedData = {
        ...onboardFormData,
        billing_email: onboardFormData.billing_email || null,
        description: onboardFormData.description || null,
        admin_full_name: onboardFormData.admin_full_name || null,
        country: onboardFormData.country || null,
      };
      const response = await api.post("/admin/onboard-organization", cleanedData);

      setOnboardResult(response.data);

      toast({
        title: "Organization Onboarded",
        description: `Organization "${onboardFormData.name}" onboarded successfully. Welcome email sent to ${onboardFormData.admin_email}.`,
      });

      fetchOrganizations();
      fetchStats();
    } catch (error: any) {
      const errorMessage = error.response?.data?.detail
        || error.response?.data?.message
        || error.message
        || "Failed to onboard organization";
      toast({
        title: "Error",
        description: errorMessage,
        variant: "destructive",
      });
    } finally {
      setOnboardLoading(false);
    }
  };

  const handleDisableSync = async (orgId: number, orgName: string) => {
    if (!confirm(`Disable data syncing for ${orgName}? Users can still login but won't be able to run pipelines.`)) {
      return;
    }

    try {
      await api.patch(`/admin/organizations/${orgId}/disable-sync`);

      toast({
        title: "Success",
        description: `Data syncing disabled for ${orgName}`,
      });

      fetchOrganizations();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to disable sync",
        variant: "destructive",
      });
    }
  };

  const handleEnableSync = async (orgId: number, orgName: string) => {
    try {
      await api.patch(`/admin/organizations/${orgId}/enable-sync`);

      toast({
        title: "Success",
        description: `Data syncing enabled for ${orgName}`,
      });

      fetchOrganizations();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to enable sync",
        variant: "destructive",
      });
    }
  };

  const handleDeactivate = async (orgId: number, orgName: string) => {
    if (!confirm(`COMPLETELY DEACTIVATE ${orgName}? Users will be locked out and unable to login. This is a hard shutdown.`)) {
      return;
    }

    try {
      await api.patch(`/admin/organizations/${orgId}/deactivate`);

      toast({
        title: "Success",
        description: `${orgName} has been deactivated`,
        variant: "destructive",
      });

      fetchOrganizations();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to deactivate organization",
        variant: "destructive",
      });
    }
  };

  const handleActivate = async (orgId: number, orgName: string) => {
    try {
      await api.patch(`/admin/organizations/${orgId}/activate`);

      toast({
        title: "Success",
        description: `${orgName} has been reactivated`,
      });

      fetchOrganizations();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to activate organization",
        variant: "destructive",
      });
    }
  };

  const handleDeletePendingOrg = async (orgId: number, orgName: string) => {
    if (!confirm(
      `Delete pending organization "${orgName}"?\n\n` +
      `This action cannot be undone. The organization and its admin user will be permanently deleted.\n\n` +
      `Note: You can only delete organizations that haven't onboarded yet.`
    )) {
      return;
    }

    try {
      await api.delete(`/admin/organizations/${orgId}`);

      toast({
        title: "Success",
        description: `Pending organization "${orgName}" has been deleted`,
      });

      fetchOrganizations();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to delete organization",
        variant: "destructive",
      });
    }
  };

  const handleForceDeleteOrg = async () => {
    if (!deleteDialogOrg) return;
    if (deleteConfirmName !== deleteDialogOrg.name) return;
    if (!deleteReason.trim()) return;

    setDeleteLoading(true);
    try {
      await api.delete(`/admin/organizations/${deleteDialogOrg.id}/force`, {
        data: { reason: deleteReason.trim() },
      });

      toast({
        title: "Organization Deleted",
        description: `"${deleteDialogOrg.name}" and all its data have been permanently deleted.`,
        variant: "destructive",
      });

      setDeleteDialogOrg(null);
      setDeleteConfirmName("");
      setDeleteReason("");
      fetchOrganizations();
      fetchStats();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to delete organization",
        variant: "destructive",
      });
    } finally {
      setDeleteLoading(false);
    }
  };

  const getPlanBadge = (plan: string) => {
    const variants: Record<string, { variant: any; label: string }> = {
      starter: { variant: "secondary", label: "Starter" },
      professional: { variant: "default", label: "Professional" },
      enterprise: { variant: "outline", label: "Enterprise" },
    };

    const config = variants[plan] || variants.starter;
    return (
      <Badge variant={config.variant as any} className="font-medium">
        {config.label}
      </Badge>
    );
  };

  const toggleOrgExpansion = async (orgId: number) => {
    const newExpanded = new Set(expandedOrgs);
    if (newExpanded.has(orgId)) {
      newExpanded.delete(orgId);
    } else {
      newExpanded.add(orgId);
      // Fetch details if not already loaded
      if (!orgDetails[orgId]) {
        try {
          const [detailsRes, pipelinesRes] = await Promise.all([
            api.get(`/admin/organizations/${orgId}/details`),
            api.get(`/admin/organizations/${orgId}/pipelines?limit=5`),
          ]);
          setOrgDetails((prev) => ({
            ...prev,
            [orgId]: {
              pipelines_count: detailsRes.data.pipelines_count,
              sources_count: detailsRes.data.sources_count,
              destinations_count: detailsRes.data.destinations_count,
              recent_runs_count: detailsRes.data.recent_runs_count,
            },
          }));
          setOrgPipelines((prev) => ({
            ...prev,
            [orgId]: pipelinesRes.data.pipelines || [],
          }));
        } catch {
          // Error handled silently - details will show as "Loading..."
        }
      }
    }
    setExpandedOrgs(newExpanded);
  };

  const handleViewDetails = (slug: string) => {
    router.push(`/admin/organizations/${slug}`);
  };

  const handleStartImpersonation = async (orgId: number, orgName: string) => {
    try {
      const response = await api.post(`/admin/impersonate/${orgId}`);
      toast({
        title: "Impersonation Started",
        description: response.data.message,
      });
      // Refresh page to show impersonation banner
      window.location.reload();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to start impersonation",
        variant: "destructive",
      });
    }
  };

  const getRunStatusColor = (status: string | null) => {
    const colors: Record<string, string> = {
      completed: "bg-green-500",
      running: "bg-blue-500",
      pending: "bg-yellow-500",
      failed: "bg-red-500",
      cancelled: "bg-gray-500",
    };
    return colors[status || ""] || "bg-gray-300";
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Super Admin Dashboard</h1>
          <p className="text-muted-foreground">
            Manage all organizations and monitor platform health
          </p>
        </div>
        <div className="flex gap-2">
        <Dialog open={onboardDialogOpen} onOpenChange={(open) => { setOnboardDialogOpen(open); if (!open) { setOnboardFormData(initialFormState); setOnboardResult(null); } }}>
          <DialogTrigger asChild>
            <Button variant="default">
              <Plus className="mr-2 h-4 w-4" />
              Onboard Organization
            </Button>
          </DialogTrigger>
          <DialogContent
            className="max-w-2xl max-h-[90vh] overflow-y-auto"
            onInteractOutside={(e) => e.preventDefault()}
            onEscapeKeyDown={(e) => e.preventDefault()}
          >
            <DialogHeader>
              <DialogTitle>Onboard New Organization</DialogTitle>
              <DialogDescription>
                Create a new organization and admin account. The admin will receive a welcome email with login credentials.
              </DialogDescription>
            </DialogHeader>

            {onboardResult ? (
              <div className="space-y-4 py-4">
                <div className="rounded-lg border bg-green-50 p-4 text-green-800">
                  <h4 className="font-medium mb-2">Organization Onboarded Successfully</h4>
                  <p className="text-sm">{onboardResult.message}</p>
                </div>
                <div className="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <p className="font-medium text-muted-foreground">Organization</p>
                    <p>{onboardResult.organization?.name}</p>
                  </div>
                  <div>
                    <p className="font-medium text-muted-foreground">Plan</p>
                    <p className="capitalize">{onboardResult.organization?.subscription_plan}</p>
                  </div>
                  <div>
                    <p className="font-medium text-muted-foreground">Admin Email</p>
                    <p>{onboardResult.admin_user?.email}</p>
                  </div>
                  <div>
                    <p className="font-medium text-muted-foreground">Admin Username</p>
                    <p>{onboardResult.admin_user?.username}</p>
                  </div>
                </div>
                <DialogFooter>
                  <Button onClick={() => { setOnboardDialogOpen(false); setOnboardFormData(initialFormState); setOnboardResult(null); }}>
                    Done
                  </Button>
                </DialogFooter>
              </div>
            ) : (
              <form onSubmit={handleOnboardOrganization}>
                <div className="grid gap-4 py-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="onboard_name">Organization Name *</Label>
                      <Input
                        id="onboard_name"
                        placeholder="Acme Corporation"
                        value={onboardFormData.name}
                        onChange={(e) => {
                          const name = e.target.value;
                          setOnboardFormData({ ...onboardFormData, name, slug: generateSlug(name) });
                        }}
                        required
                      />
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="onboard_slug">Slug *</Label>
                      <Input
                        id="onboard_slug"
                        placeholder="acme-corporation"
                        value={onboardFormData.slug}
                        onChange={(e) => setOnboardFormData({ ...onboardFormData, slug: e.target.value })}
                        required
                      />
                    </div>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="onboard_country">Country</Label>
                    <Select
                      value={onboardFormData.country}
                      onValueChange={(value) =>
                        setOnboardFormData({ ...onboardFormData, country: value })
                      }
                    >
                      <SelectTrigger id="onboard_country">
                        <SelectValue placeholder="Select country (sets billing currency)" />
                      </SelectTrigger>
                      <SelectContent>
                        {ORG_COUNTRIES.map((c) => (
                          <SelectItem key={c.name} value={c.name}>
                            {c.name} — billed in {c.currency}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      Sets the billing currency with local market pricing (not an FX conversion). Defaults to GBP if unset.
                    </p>
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label htmlFor="onboard_plan">Plan *</Label>
                      <Select
                        value={onboardFormData.subscription_plan}
                        onValueChange={(value) =>
                          setOnboardFormData({ ...onboardFormData, subscription_plan: value, max_users: planLimits[value] || 5 })
                        }
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select plan" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="starter">Starter (5 users)</SelectItem>
                          <SelectItem value="professional">Professional (25 users)</SelectItem>
                          <SelectItem value="enterprise">Enterprise (100 users)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div className="space-y-2">
                      <Label htmlFor="onboard_max_users">Max Users</Label>
                      <Input
                        id="onboard_max_users"
                        type="number"
                        min={1}
                        value={onboardFormData.max_users}
                        onChange={(e) => setOnboardFormData({ ...onboardFormData, max_users: parseInt(e.target.value) || 5 })}
                      />
                    </div>
                  </div>

                  <div className="border-t pt-4 mt-2">
                    <h4 className="font-medium mb-3">Organization Admin Account</h4>
                    <div className="grid grid-cols-2 gap-4">
                      <div className="space-y-2">
                        <Label htmlFor="onboard_admin_email">Admin Email *</Label>
                        <Input
                          id="onboard_admin_email"
                          type="email"
                          placeholder="admin@acme.com"
                          value={onboardFormData.admin_email}
                          onChange={(e) => setOnboardFormData({ ...onboardFormData, admin_email: e.target.value })}
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="onboard_admin_username">Admin Username *</Label>
                        <Input
                          id="onboard_admin_username"
                          placeholder="johndoe"
                          value={onboardFormData.admin_username}
                          onChange={(e) => setOnboardFormData({ ...onboardFormData, admin_username: e.target.value })}
                          required
                        />
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-4 mt-4">
                      <div className="space-y-2">
                        <Label htmlFor="onboard_admin_full_name">Full Name *</Label>
                        <Input
                          id="onboard_admin_full_name"
                          placeholder="John Doe"
                          value={onboardFormData.admin_full_name}
                          onChange={(e) => setOnboardFormData({ ...onboardFormData, admin_full_name: e.target.value })}
                          required
                        />
                      </div>
                      <div className="space-y-2">
                        <Label htmlFor="onboard_admin_password">Temporary Password *</Label>
                        <Input
                          id="onboard_admin_password"
                          type="password"
                          placeholder="Min 8 characters"
                          value={onboardFormData.admin_password}
                          onChange={(e) => setOnboardFormData({ ...onboardFormData, admin_password: e.target.value })}
                          required
                          minLength={8}
                        />
                      </div>
                    </div>
                  </div>
                </div>
                <DialogFooter>
                  <Button type="button" variant="outline" onClick={() => setOnboardDialogOpen(false)}>
                    Cancel
                  </Button>
                  <Button type="submit" disabled={onboardLoading}>
                    {onboardLoading ? "Onboarding..." : "Onboard Organization"}
                  </Button>
                </DialogFooter>
              </form>
            )}
          </DialogContent>
        </Dialog>
        </div>
      </div>

      {/* Platform Statistics */}
      {stats && (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Organizations</CardTitle>
              <Building2 className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_organizations}</div>
              <p className="text-xs text-muted-foreground">
                {stats.active_organizations} active
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Users</CardTitle>
              <Users className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_users}</div>
              <p className="text-xs text-muted-foreground">
                {stats.active_users} active
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Total Pipelines</CardTitle>
              <Workflow className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_pipelines}</div>
              <p className="text-xs text-muted-foreground">
                Across all organizations
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">Runs Today</CardTitle>
              <Activity className="h-4 w-4 text-muted-foreground" />
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stats.total_runs_today}</div>
              <p className="text-xs text-muted-foreground">
                {stats.total_runs_this_week} this week
              </p>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Force Delete Confirmation Dialog */}
      <Dialog
        open={!!deleteDialogOrg}
        onOpenChange={(open) => {
          if (!open) {
            setDeleteDialogOrg(null);
            setDeleteConfirmName("");
            setDeleteReason("");
          }
        }}
      >
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle className="text-destructive flex items-center gap-2">
              <Trash2 className="h-5 w-5" />
              Permanently Delete Organization
            </DialogTitle>
            <DialogDescription>
              This will permanently delete <strong>{deleteDialogOrg?.name}</strong> and
              all its data including users, pipelines, sources, destinations, and billing
              records. <strong>This cannot be undone.</strong>
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-2">
            <div className="space-y-2">
              <Label>Reason for deletion</Label>
              <Textarea
                placeholder="e.g. Customer requested account closure, fraud, etc."
                value={deleteReason}
                onChange={(e) => setDeleteReason(e.target.value)}
                rows={2}
              />
            </div>
            <div className="space-y-2">
              <Label>
                Type <strong>{deleteDialogOrg?.name}</strong> to confirm
              </Label>
              <Input
                placeholder={deleteDialogOrg?.name}
                value={deleteConfirmName}
                onChange={(e) => setDeleteConfirmName(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setDeleteDialogOrg(null);
                setDeleteConfirmName("");
                setDeleteReason("");
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              disabled={
                deleteConfirmName !== deleteDialogOrg?.name ||
                !deleteReason.trim() ||
                deleteLoading
              }
              onClick={handleForceDeleteOrg}
            >
              {deleteLoading ? "Deleting..." : "Delete Permanently"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Organizations Table */}
      <Card>
        <CardHeader>
          <CardTitle>All Organizations</CardTitle>
          <CardDescription>
            Manage all organizations on the platform
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">Loading...</div>
          ) : organizations.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No organizations yet
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Organization</TableHead>
                  <TableHead>Onboarding</TableHead>
                  <TableHead>Plan</TableHead>
                  <TableHead>Users</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Sync</TableHead>
                  <TableHead>Created</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {organizations.map((org) => (
                  <React.Fragment key={org.id}>
                    <TableRow key={`row-${org.id}`} className="cursor-pointer hover:bg-muted/50" onClick={() => toggleOrgExpansion(org.id)}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          {expandedOrgs.has(org.id) ? (
                            <ChevronUp className="h-4 w-4 text-muted-foreground" />
                          ) : (
                            <ChevronDown className="h-4 w-4 text-muted-foreground" />
                          )}
                          <div>
                            <div className="font-medium">{org.name}</div>
                            <div className="text-sm text-muted-foreground">{org.slug}</div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell>
                        {org.admin_onboarded ? (
                          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 gap-1">
                            <CheckCircle className="h-3 w-3" />
                            Onboarded
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="bg-yellow-50 text-yellow-700 border-yellow-200 gap-1">
                            <Clock className="h-3 w-3" />
                            Pending
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>{getPlanBadge(org.subscription_plan)}</TableCell>
                      <TableCell>
                        <div className="text-sm">
                          <span className="font-medium">{org.current_user_count}</span>
                          {" / "}
                          <span className="text-muted-foreground">{org.max_users}</span>
                        </div>
                      </TableCell>
                      <TableCell>
                        {org.is_active ? (
                          <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200 gap-1">
                            <PlayCircle className="h-3 w-3" />
                            Active
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="bg-red-50 text-red-700 border-red-200 gap-1">
                            <Power className="h-3 w-3" />
                            Deactivated
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell>
                        {org.can_sync_data ? (
                          <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-200">
                            Enabled
                          </Badge>
                        ) : (
                          <Badge variant="outline" className="bg-orange-50 text-orange-700 border-orange-200 gap-1">
                            <AlertTriangle className="h-3 w-3" />
                            Disabled
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {new Date(org.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right" onClick={(e) => e.stopPropagation()}>
                        <DropdownMenu>
                          <DropdownMenuTrigger asChild>
                            <Button variant="ghost" size="sm">
                              <MoreVertical className="h-4 w-4" />
                            </Button>
                          </DropdownMenuTrigger>
                          <DropdownMenuContent align="end">
                            <DropdownMenuLabel>Organization Controls</DropdownMenuLabel>
                            <DropdownMenuSeparator />

                            {/* View Details */}
                            <DropdownMenuItem onClick={() => handleViewDetails(org.slug)}>
                              <ExternalLink className="mr-2 h-4 w-4" />
                              View Details
                            </DropdownMenuItem>

                            {/* Impersonate */}
                            <DropdownMenuItem onClick={() => handleStartImpersonation(org.id, org.name)}>
                              <Eye className="mr-2 h-4 w-4" />
                              Impersonate
                            </DropdownMenuItem>

                            <DropdownMenuSeparator />

                            {/* Sync Controls */}
                            {org.can_sync_data ? (
                              <DropdownMenuItem
                                onClick={() => handleDisableSync(org.id, org.name)}
                                className="text-orange-600"
                              >
                                <PauseCircle className="mr-2 h-4 w-4" />
                                Disable Data Sync (Warning)
                              </DropdownMenuItem>
                            ) : (
                              <DropdownMenuItem
                                onClick={() => handleEnableSync(org.id, org.name)}
                              >
                                <PlayCircle className="mr-2 h-4 w-4" />
                                Enable Data Sync
                              </DropdownMenuItem>
                            )}

                            <DropdownMenuSeparator />

                            {/* Activation Controls */}
                            {org.is_active ? (
                              <DropdownMenuItem
                                onClick={() => handleDeactivate(org.id, org.name)}
                                className="text-destructive"
                              >
                                <Power className="mr-2 h-4 w-4" />
                                Deactivate (Hard Shutdown)
                              </DropdownMenuItem>
                            ) : (
                              <DropdownMenuItem
                                onClick={() => handleActivate(org.id, org.name)}
                              >
                                <PlayCircle className="mr-2 h-4 w-4" />
                                Reactivate Organization
                              </DropdownMenuItem>
                            )}

                            {/* Delete Organization */}
                            <DropdownMenuSeparator />
                            {!org.admin_onboarded ? (
                              <DropdownMenuItem
                                onClick={() => handleDeletePendingOrg(org.id, org.name)}
                                className="text-destructive"
                              >
                                <Trash2 className="mr-2 h-4 w-4" />
                                Delete Pending Organization
                              </DropdownMenuItem>
                            ) : (
                              <DropdownMenuItem
                                onClick={() => {
                                  setDeleteDialogOrg(org);
                                  setDeleteConfirmName("");
                                  setDeleteReason("");
                                }}
                                className="text-destructive"
                              >
                                <Trash2 className="mr-2 h-4 w-4" />
                                Permanently Delete
                              </DropdownMenuItem>
                            )}
                          </DropdownMenuContent>
                        </DropdownMenu>
                      </TableCell>
                    </TableRow>

                    {/* Expanded Details Row */}
                    {expandedOrgs.has(org.id) && (
                      <TableRow className="bg-muted/30">
                        <TableCell colSpan={8} className="p-4">
                          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* Resource Stats */}
                            <div className="space-y-3">
                              <h4 className="font-medium text-sm">Resources</h4>
                              {orgDetails[org.id] ? (
                                <div className="grid grid-cols-4 gap-2">
                                  <div className="flex items-center gap-2 p-2 rounded-lg bg-background">
                                    <Workflow className="h-4 w-4 text-muted-foreground" />
                                    <div>
                                      <p className="text-lg font-bold">{orgDetails[org.id].pipelines_count}</p>
                                      <p className="text-xs text-muted-foreground">Pipelines</p>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-2 p-2 rounded-lg bg-background">
                                    <Database className="h-4 w-4 text-muted-foreground" />
                                    <div>
                                      <p className="text-lg font-bold">{orgDetails[org.id].sources_count}</p>
                                      <p className="text-xs text-muted-foreground">Sources</p>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-2 p-2 rounded-lg bg-background">
                                    <HardDrive className="h-4 w-4 text-muted-foreground" />
                                    <div>
                                      <p className="text-lg font-bold">{orgDetails[org.id].destinations_count}</p>
                                      <p className="text-xs text-muted-foreground">Destinations</p>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-2 p-2 rounded-lg bg-background">
                                    <Activity className="h-4 w-4 text-muted-foreground" />
                                    <div>
                                      <p className="text-lg font-bold">{orgDetails[org.id].recent_runs_count}</p>
                                      <p className="text-xs text-muted-foreground">Runs (7d)</p>
                                    </div>
                                  </div>
                                </div>
                              ) : (
                                <p className="text-sm text-muted-foreground">Loading...</p>
                              )}
                            </div>

                            {/* Recent Pipelines */}
                            <div className="space-y-3">
                              <h4 className="font-medium text-sm">Recent Pipelines</h4>
                              {orgPipelines[org.id] ? (
                                orgPipelines[org.id].length > 0 ? (
                                  <div className="space-y-2">
                                    {orgPipelines[org.id].map((pipeline) => (
                                      <div key={pipeline.id} className="flex items-center justify-between p-2 rounded-lg bg-background">
                                        <div className="flex items-center gap-2">
                                          <div className={`h-2 w-2 rounded-full ${getRunStatusColor(pipeline.last_run_status)}`} />
                                          <span className="text-sm">{pipeline.name}</span>
                                        </div>
                                        {pipeline.is_active ? (
                                          <Badge variant="outline" className="text-xs">Active</Badge>
                                        ) : (
                                          <Badge variant="secondary" className="text-xs">Inactive</Badge>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                ) : (
                                  <p className="text-sm text-muted-foreground">No pipelines</p>
                                )
                              ) : (
                                <p className="text-sm text-muted-foreground">Loading...</p>
                              )}
                            </div>
                          </div>

                          {/* Quick Actions */}
                          <div className="flex gap-2 mt-4 pt-4 border-t">
                            <Button variant="outline" size="sm" onClick={() => handleViewDetails(org.slug)}>
                              <ExternalLink className="h-4 w-4 mr-1" />
                              View Full Details
                            </Button>
                            <Button variant="outline" size="sm" onClick={() => handleStartImpersonation(org.id, org.name)}>
                              <Eye className="h-4 w-4 mr-1" />
                              Impersonate
                            </Button>
                          </div>
                        </TableCell>
                      </TableRow>
                    )}
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
