"use client";

import { useState } from "react";
import { useCurrentUser } from "@/hooks/queries/useAuth";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Separator } from "@/components/ui/separator";
import { useToast } from "@/hooks/use-toast";
import { User, Mail, Lock, Camera, Loader2, Bell, GitBranch, Shield, CreditCard, Brain } from "lucide-react";
import api from "@/lib/api-client";
import Link from "next/link";

export default function SettingsPage() {
  const { data: user, refetch } = useCurrentUser();
  const { toast } = useToast();

  // Profile form state
  const [fullName, setFullName] = useState(user?.full_name || "");
  const [email, setEmail] = useState(user?.email || "");
  const [isUpdatingProfile, setIsUpdatingProfile] = useState(false);

  // Password form state
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [isUpdatingPassword, setIsUpdatingPassword] = useState(false);

  const handleUpdateProfile = async () => {
    setIsUpdatingProfile(true);
    try {
      await api.patch("/auth/me", {
        full_name: fullName || null,
        email: email,
      });

      toast({
        title: "Success",
        description: "Profile updated successfully",
      });

      refetch();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to update profile",
        variant: "destructive",
      });
    } finally {
      setIsUpdatingProfile(false);
    }
  };

  const handleChangePassword = async () => {
    if (newPassword !== confirmPassword) {
      toast({
        title: "Error",
        description: "New passwords do not match",
        variant: "destructive",
      });
      return;
    }

    if (newPassword.length < 8) {
      toast({
        title: "Error",
        description: "Password must be at least 8 characters",
        variant: "destructive",
      });
      return;
    }

    setIsUpdatingPassword(true);
    try {
      await api.post("/auth/change-password", {
        current_password: currentPassword,
        new_password: newPassword,
      });

      toast({
        title: "Success",
        description: "Password changed successfully",
      });

      // Clear password fields
      setCurrentPassword("");
      setNewPassword("");
      setConfirmPassword("");
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to change password",
        variant: "destructive",
      });
    } finally {
      setIsUpdatingPassword(false);
    }
  };

  // Initialize form when user data loads
  if (user && !fullName && user.full_name) {
    setFullName(user.full_name);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Settings</h1>
        <p className="text-muted-foreground">
          Manage your account and preferences
        </p>
      </div>

      {/* Quick Links */}
      <div className="grid gap-4 md:grid-cols-5">
        <Link href="/settings/alerts">
          <Card className="hover:bg-accent transition-colors cursor-pointer">
            <CardContent className="flex items-center gap-3 p-4">
              <Bell className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">Alerts</p>
                <p className="text-xs text-muted-foreground">Notifications & rules</p>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link href="/settings/dbt">
          <Card className="hover:bg-accent transition-colors cursor-pointer">
            <CardContent className="flex items-center gap-3 p-4">
              <GitBranch className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">dbt Projects</p>
                <p className="text-xs text-muted-foreground">Transformations</p>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link href="/settings/ai-modeling">
          <Card className="hover:bg-accent transition-colors cursor-pointer">
            <CardContent className="flex items-center gap-3 p-4">
              <Brain className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">AI Modeling</p>
                <p className="text-xs text-muted-foreground">Auto star schema</p>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link href="/settings/security">
          <Card className="hover:bg-accent transition-colors cursor-pointer">
            <CardContent className="flex items-center gap-3 p-4">
              <Shield className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">Security</p>
                <p className="text-xs text-muted-foreground">2FA & sessions</p>
              </div>
            </CardContent>
          </Card>
        </Link>
        <Link href="/settings/billing">
          <Card className="hover:bg-accent transition-colors cursor-pointer">
            <CardContent className="flex items-center gap-3 p-4">
              <CreditCard className="h-5 w-5 text-primary" />
              <div>
                <p className="font-medium">Billing</p>
                <p className="text-xs text-muted-foreground">Plans & invoices</p>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-3">
        {/* Profile Section */}
        <div className="lg:col-span-2 space-y-6">
          {/* Profile Information */}
          <Card>
            <CardHeader>
              <CardTitle>Profile Information</CardTitle>
              <CardDescription>
                Update your personal information and email address
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              {/* Profile Photo */}
              <div className="flex items-center gap-4">
                <Avatar className="h-20 w-20">
                  <AvatarImage src={user?.avatar_url} />
                  <AvatarFallback className="text-lg">
                    {user?.full_name?.charAt(0) || user?.username?.charAt(0) || "U"}
                  </AvatarFallback>
                </Avatar>
                <div className="space-y-1">
                  <Button variant="outline" size="sm" disabled>
                    <Camera className="mr-2 h-4 w-4" />
                    Upload Photo
                  </Button>
                  <p className="text-xs text-muted-foreground">
                    Photo upload coming soon
                  </p>
                </div>
              </div>

              <Separator />

              {/* Form Fields */}
              <div className="space-y-4">
                <div className="grid gap-4 md:grid-cols-2">
                  <div className="space-y-2">
                    <Label htmlFor="username">
                      <User className="inline h-4 w-4 mr-1" />
                      Username
                    </Label>
                    <Input
                      id="username"
                      value={user?.username || ""}
                      disabled
                      className="bg-muted"
                    />
                    <p className="text-xs text-muted-foreground">
                      Username cannot be changed
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor="fullName">Full Name</Label>
                    <Input
                      id="fullName"
                      placeholder="Enter your full name"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                    />
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor="email">
                    <Mail className="inline h-4 w-4 mr-1" />
                    Email Address
                  </Label>
                  <Input
                    id="email"
                    type="email"
                    placeholder="your.email@company.com"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                  />
                  <p className="text-xs text-muted-foreground">
                    Used for notifications and account recovery
                  </p>
                </div>
              </div>
            </CardContent>
            <CardFooter>
              <Button
                onClick={handleUpdateProfile}
                disabled={isUpdatingProfile}
              >
                {isUpdatingProfile ? (
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

          {/* Password Change */}
          <Card>
            <CardHeader>
              <CardTitle>
                <Lock className="inline h-5 w-5 mr-2" />
                Change Password
              </CardTitle>
              <CardDescription>
                Update your password to keep your account secure
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="currentPassword">Current Password</Label>
                <Input
                  id="currentPassword"
                  type="password"
                  placeholder="Enter current password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="newPassword">New Password</Label>
                <Input
                  id="newPassword"
                  type="password"
                  placeholder="Enter new password (min 8 characters)"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="confirmPassword">Confirm New Password</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="Confirm new password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                />
              </div>
            </CardContent>
            <CardFooter>
              <Button
                onClick={handleChangePassword}
                disabled={isUpdatingPassword || !currentPassword || !newPassword || !confirmPassword}
                variant="default"
              >
                {isUpdatingPassword ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Updating...
                  </>
                ) : (
                  "Update Password"
                )}
              </Button>
            </CardFooter>
          </Card>
        </div>

        {/* Sidebar */}
        <div className="space-y-6">
          {/* Account Info */}
          <Card>
            <CardHeader>
              <CardTitle>Account Information</CardTitle>
            </CardHeader>
            <CardContent className="space-y-3 text-sm">
              <div>
                <p className="text-muted-foreground">Organization</p>
                <p className="font-medium">{user?.organization?.name || "N/A"}</p>
              </div>
              <Separator />
              <div>
                <p className="text-muted-foreground">Role</p>
                <p className="font-medium">
                  {user?.roles?.join(", ") || "User"}
                </p>
              </div>
              <Separator />
              <div>
                <p className="text-muted-foreground">Member Since</p>
                <p className="font-medium">
                  {user?.created_at ? new Date(user.created_at).toLocaleDateString() : "N/A"}
                </p>
              </div>
              <Separator />
              <div>
                <p className="text-muted-foreground">Last Login</p>
                <p className="font-medium">
                  {user?.last_login ? new Date(user.last_login).toLocaleString() : "Never"}
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Danger Zone */}
          <Card className="border-destructive">
            <CardHeader>
              <CardTitle className="text-destructive">Danger Zone</CardTitle>
              <CardDescription>
                Irreversible and destructive actions
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-3">
              <Button variant="destructive" className="w-full" disabled>
                Delete Account
              </Button>
              <p className="text-xs text-muted-foreground">
                Account deletion coming soon. Contact support to delete your account.
              </p>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
