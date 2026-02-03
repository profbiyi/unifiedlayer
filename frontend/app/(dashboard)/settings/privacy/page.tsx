"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useToast } from "@/hooks/use-toast";
import { Download, Trash2, Loader2, AlertTriangle, ShieldCheck } from "lucide-react";
import api from "@/lib/api-client";

export default function PrivacySettingsPage() {
  const { toast } = useToast();

  // Export state
  const [isExporting, setIsExporting] = useState(false);

  // Delete state
  const [confirmation, setConfirmation] = useState("");
  const [password, setPassword] = useState("");
  const [isDeleting, setIsDeleting] = useState(false);

  const handleExportData = async () => {
    setIsExporting(true);
    try {
      const response = await api.get("/gdpr/export-my-data", {
        responseType: "blob",
      });

      const blob = new Blob([response.data], { type: "application/json" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = "my_data_export.json";
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      toast({
        title: "Export complete",
        description: "Your data has been downloaded.",
      });
    } catch (error: any) {
      toast({
        title: "Export failed",
        description:
          error.response?.data?.detail || "Could not export your data. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsExporting(false);
    }
  };

  const handleDeleteAccount = async () => {
    if (confirmation !== "DELETE") {
      toast({
        title: "Confirmation required",
        description: 'Please type "DELETE" to confirm.',
        variant: "destructive",
      });
      return;
    }

    if (!password) {
      toast({
        title: "Password required",
        description: "Please enter your current password.",
        variant: "destructive",
      });
      return;
    }

    setIsDeleting(true);
    try {
      await api.delete("/gdpr/delete-my-account", {
        data: { password, confirmation },
      });

      toast({
        title: "Account deleted",
        description: "Your account has been permanently deleted.",
      });

      // Redirect to home after short delay
      setTimeout(() => {
        window.location.href = "/";
      }, 2000);
    } catch (error: any) {
      toast({
        title: "Deletion failed",
        description:
          error.response?.data?.detail || "Could not delete your account. Please try again.",
        variant: "destructive",
      });
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Privacy &amp; Data</h1>
        <p className="text-muted-foreground">
          Manage your personal data and exercise your privacy rights
        </p>
      </div>

      {/* Export Data */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5" />
            Export My Data
          </CardTitle>
          <CardDescription>
            Download a copy of all personal data we hold about you, including your profile,
            organisation details, pipeline configurations, and run history. The export is provided as
            a machine-readable JSON file (GDPR Article 20 &mdash; Right to Data Portability).
          </CardDescription>
        </CardHeader>
        <CardFooter>
          <Button onClick={handleExportData} disabled={isExporting}>
            {isExporting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="mr-2 h-4 w-4" />
                Download My Data
              </>
            )}
          </Button>
        </CardFooter>
      </Card>

      {/* Delete Account */}
      <Card className="border-destructive">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-destructive">
            <Trash2 className="h-5 w-5" />
            Delete My Account
          </CardTitle>
          <CardDescription>
            Permanently delete your account and anonymise all associated personal data. This action
            cannot be undone.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <Alert variant="destructive">
            <AlertTriangle className="h-4 w-4" />
            <AlertDescription>
              Deleting your account will immediately deactivate your login and anonymise your email,
              username, and profile information. Organisation resources (pipelines, sources,
              destinations) will remain available to other members.
            </AlertDescription>
          </Alert>

          <div className="space-y-2">
            <Label htmlFor="confirmation">
              Type <span className="font-mono font-bold">DELETE</span> to confirm
            </Label>
            <Input
              id="confirmation"
              placeholder="DELETE"
              value={confirmation}
              onChange={(e) => setConfirmation(e.target.value)}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="password">Current Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>
        </CardContent>
        <CardFooter>
          <Button
            variant="destructive"
            onClick={handleDeleteAccount}
            disabled={isDeleting || confirmation !== "DELETE" || !password}
          >
            {isDeleting ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Deleting...
              </>
            ) : (
              "Permanently Delete My Account"
            )}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
}
