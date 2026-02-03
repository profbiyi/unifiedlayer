"use client";

import { useState } from "react";
import { useCurrentUser } from "@/hooks/queries/useAuth";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { Building2, Upload, Loader2, Crown, Users, Workflow, Calendar } from "lucide-react";
import api from "@/lib/api-client";

export default function OrganizationSettingsPage() {
  const { data: user } = useCurrentUser();
  const { toast } = useToast();

  // Check if user is org admin
  const isOrgAdmin = user?.roles?.includes("ORG_ADMIN") || user?.roles?.includes("SUPER_ADMIN");

  // Organization form state
  const [orgName, setOrgName] = useState(user?.organization?.name || "");
  const [orgSlug, setOrgSlug] = useState(user?.organization?.slug || "");
  const [isUpdating, setIsUpdating] = useState(false);

  const handleUpdateOrganization = async () => {
    if (!isOrgAdmin) {
      toast({
        title: "Permission Denied",
        description: "Only organization admins can update organization settings",
        variant: "destructive",
      });
      return;
    }

    setIsUpdating(true);
    try {
      await api.patch("/organizations/me", {
        name: orgName,
        slug: orgSlug,
      });

      toast({
        title: "Success",
        description: "Organization updated successfully",
      });

      // Reload to fetch updated org data
      window.location.reload();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to update organization",
        variant: "destructive",
      });
    } finally {
      setIsUpdating(false);
    }
  };

  if (!user) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Organization Settings</h1>
        <p className="text-muted-foreground">
          Manage your organization details and preferences
        </p>
      </div>

      {!isOrgAdmin && (
        <Card className="border-yellow-200 bg-yellow-50/50">
          <CardContent className="pt-6">
            <p className="text-sm text-yellow-800">
              <strong>Note:</strong> Only organization administrators can modify these settings.
              You can view organization information below.
            </p>
          </CardContent>
        </Card>
      )}

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Organization Details */}
        <div className="lg:col-span-2 space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Organization Information</CardTitle>
              <CardDescription>
                Update your organization details and branding
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Organization Logo */}
              <div className="flex items-center gap-4">
                <Avatar className="h-20 w-20 rounded-lg">
                  <AvatarImage src={user.organization?.logo_url} />
                  <AvatarFallback className="text-lg rounded-lg">
                    <Building2 className="h-8 w-8" />
                  </AvatarFallback>
                </Avatar>
                <div className="space-y-1">
                  <Button variant="outline" size="sm" disabled={!isOrgAdmin}>
                    <Upload className="mr-2 h-4 w-4" />
                    Upload Logo
                  </Button>
                  <p className="text-xs text-muted-foreground">
                    Logo upload coming soon
                  </p>
                </div>
              </div>

              <Separator />

              {/* Form Fields */}
              <div className="space-y-4">
                <div className="space-y-2">
                  <Label htmlFor="orgName">
                    <Building2 className="inline h-4 w-4 mr-1" />
                    Organization Name
                  </Label>
                  <Input
                    id="orgName"
                    placeholder="Acme Corporation"
                    value={orgName}
                    onChange={(e) => setOrgName(e.target.value)}
                    disabled={!isOrgAdmin}
                  />
                  <p className="text-xs text-muted-foreground">
                    This is your organization's display name
                  </p>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="orgSlug">Organization Slug</Label>
                  <Input
                    id="orgSlug"
                    placeholder="acme-corp"
                    value={orgSlug}
                    onChange={(e) => setOrgSlug(e.target.value.toLowerCase().replace(/\s+/g, '-'))}
                    disabled={!isOrgAdmin}
                  />
                  <p className="text-xs text-muted-foreground">
                    Used in URLs and API calls. Lowercase letters, numbers, and hyphens only.
                  </p>
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button
                onClick={handleUpdateOrganization}
                disabled={isUpdating || !isOrgAdmin}
              >
                {isUpdating ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Saving...
                  </>
                ) : (
                  "Save Changes"
                )}
              </Button>
            </CardFooter>
          </Card>

          {/* Advanced Settings */}
          <Card>
            <CardHeader>
              <CardTitle>Advanced Settings</CardTitle>
              <CardDescription>
                Configure advanced organization features
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="font-medium">SSO Configuration</p>
                  <p className="text-sm text-muted-foreground">
                    Enable single sign-on for your organization
                  </p>
                </div>
                <Button variant="outline" size="sm" disabled>
                  Configure
                </Button>
              </div>

              <Separator />

              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="font-medium">Audit Logs</p>
                  <p className="text-sm text-muted-foreground">
                    View detailed activity logs for compliance
                  </p>
                </div>
                <Button variant="outline" size="sm" disabled>
                  View Logs
                </Button>
              </div>

              <Separator />

              <div className="flex items-center justify-between py-2">
                <div>
                  <p className="font-medium">API Webhooks</p>
                  <p className="text-sm text-muted-foreground">
                    Configure webhooks for pipeline events
                  </p>
                </div>
                <Button variant="outline" size="sm" disabled>
                  Manage
                </Button>
              </div>

              <p className="text-xs text-muted-foreground mt-4">
                Advanced features coming soon
              </p>
            </CardContent>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Organization Stats */}
          <Card>
            <CardHeader>
              <CardTitle>Organization Overview</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Crown className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">Plan</span>
                </div>
                <Badge variant="default">
                  {user.organization?.subscription_plan || "Starter"}
                </Badge>
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">Team Members</span>
                </div>
                <span className="font-medium">{user.organization?.current_user_count || 0}</span>
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Workflow className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">Active Pipelines</span>
                </div>
                <span className="font-medium">-</span>
              </div>

              <Separator />

              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Calendar className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm">Created</span>
                </div>
                <span className="font-medium text-sm">
                  {user.organization?.created_at
                    ? new Date(user.organization.created_at).toLocaleDateString()
                    : "N/A"}
                </span>
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <Button variant="outline" className="w-full justify-start" disabled={!isOrgAdmin}>
                <Users className="mr-2 h-4 w-4" />
                Invite Team Members
              </Button>
              <Button variant="outline" className="w-full justify-start" disabled={!isOrgAdmin}>
                <Crown className="mr-2 h-4 w-4" />
                Upgrade Plan
              </Button>
            </CardContent>
          </Card>

          {/* Danger Zone */}
          {isOrgAdmin && (
            <Card className="border-destructive">
              <CardHeader>
                <CardTitle className="text-destructive">Danger Zone</CardTitle>
                <CardDescription>
                  Irreversible and destructive actions
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-3">
                <Button variant="destructive" className="w-full" disabled>
                  Delete Organization
                </Button>
                <p className="text-xs text-muted-foreground">
                  Organization deletion coming soon. Contact support to delete your organization.
                </p>
              </CardContent>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
