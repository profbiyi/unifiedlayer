"use client";

import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import toast from "react-hot-toast";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export default function SecuritySettingsPage() {
  const queryClient = useQueryClient();
  const { data: currentUser } = useQuery({
    queryKey: ["currentUser"],
    queryFn: async () => {
      const { data } = await api.get("/auth/me");
      return data;
    },
  });

  // Setup flow state
  const [setupDialogOpen, setSetupDialogOpen] = useState(false);
  const [qrCode, setQrCode] = useState("");
  const [secret, setSecret] = useState("");
  const [setupCode, setSetupCode] = useState("");

  // Disable flow state
  const [disableDialogOpen, setDisableDialogOpen] = useState(false);
  const [disableCode, setDisableCode] = useState("");
  const [disablePassword, setDisablePassword] = useState("");

  const is2FAEnabled = currentUser?.two_factor_enabled ?? false;

  // Setup mutation
  const setupMutation = useMutation({
    mutationFn: async () => {
      const { data } = await api.post("/auth/2fa/setup");
      return data;
    },
    onSuccess: (data: any) => {
      setQrCode(data.qr_code);
      setSecret(data.secret);
      setSetupDialogOpen(true);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to start 2FA setup");
    },
  });

  // Verify setup mutation
  const verifySetupMutation = useMutation({
    mutationFn: async (code: string) => {
      const { data } = await api.post("/auth/2fa/verify-setup", { code });
      return data;
    },
    onSuccess: () => {
      toast.success("Two-factor authentication enabled!");
      setSetupDialogOpen(false);
      setSetupCode("");
      setQrCode("");
      setSecret("");
      queryClient.invalidateQueries({ queryKey: ["currentUser"] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Invalid code");
    },
  });

  // Disable mutation
  const disableMutation = useMutation({
    mutationFn: async (payload: { code: string; password: string }) => {
      const { data } = await api.post("/auth/2fa/disable", payload);
      return data;
    },
    onSuccess: () => {
      toast.success("Two-factor authentication disabled");
      setDisableDialogOpen(false);
      setDisableCode("");
      setDisablePassword("");
      queryClient.invalidateQueries({ queryKey: ["currentUser"] });
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to disable 2FA");
    },
  });

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight">Security</h2>
        <p className="text-muted-foreground">
          Manage your account security settings
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Two-Factor Authentication</CardTitle>
          <CardDescription>
            Add an extra layer of security to your account by requiring a
            verification code from your authenticator app when signing in.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <p className="font-medium">
                Status:{" "}
                <span
                  className={
                    is2FAEnabled ? "text-green-600" : "text-muted-foreground"
                  }
                >
                  {is2FAEnabled ? "Enabled" : "Disabled"}
                </span>
              </p>
              <p className="text-sm text-muted-foreground">
                {is2FAEnabled
                  ? "Your account is protected with two-factor authentication."
                  : "Enable two-factor authentication for additional security."}
              </p>
            </div>
            {is2FAEnabled ? (
              <Button
                variant="destructive"
                onClick={() => setDisableDialogOpen(true)}
              >
                Disable 2FA
              </Button>
            ) : (
              <Button
                onClick={() => setupMutation.mutate()}
                disabled={setupMutation.isPending}
              >
                {setupMutation.isPending ? "Setting up..." : "Enable 2FA"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Setup Dialog */}
      <Dialog open={setupDialogOpen} onOpenChange={setSetupDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Set Up Two-Factor Authentication</DialogTitle>
            <DialogDescription>
              Scan the QR code below with your authenticator app (Google
              Authenticator, Authy, etc.), then enter the 6-digit verification
              code.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            {qrCode && (
              <div className="flex justify-center">
                <img
                  src={qrCode}
                  alt="2FA QR Code"
                  className="w-48 h-48"
                />
              </div>
            )}
            {secret && (
              <div className="text-center">
                <p className="text-xs text-muted-foreground mb-1">
                  Or enter this key manually:
                </p>
                <code className="text-sm bg-muted px-2 py-1 rounded font-mono select-all">
                  {secret}
                </code>
              </div>
            )}
            <div className="space-y-2">
              <Label htmlFor="setup-code">Verification Code</Label>
              <Input
                id="setup-code"
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                placeholder="000000"
                value={setupCode}
                onChange={(e) =>
                  setSetupCode(e.target.value.replace(/\D/g, "").slice(0, 6))
                }
                className="text-center text-xl tracking-widest"
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setSetupDialogOpen(false);
                setSetupCode("");
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={() => verifySetupMutation.mutate(setupCode)}
              disabled={
                verifySetupMutation.isPending || setupCode.length !== 6
              }
            >
              {verifySetupMutation.isPending ? "Verifying..." : "Verify & Enable"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Disable Dialog */}
      <Dialog open={disableDialogOpen} onOpenChange={setDisableDialogOpen}>
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Disable Two-Factor Authentication</DialogTitle>
            <DialogDescription>
              Enter your current authenticator code and password to disable
              two-factor authentication.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="disable-code">Authenticator Code</Label>
              <Input
                id="disable-code"
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                placeholder="000000"
                value={disableCode}
                onChange={(e) =>
                  setDisableCode(e.target.value.replace(/\D/g, "").slice(0, 6))
                }
                className="text-center text-xl tracking-widest"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="disable-password">Password</Label>
              <Input
                id="disable-password"
                type="password"
                placeholder="Enter your password"
                value={disablePassword}
                onChange={(e) => setDisablePassword(e.target.value)}
              />
            </div>
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => {
                setDisableDialogOpen(false);
                setDisableCode("");
                setDisablePassword("");
              }}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() =>
                disableMutation.mutate({
                  code: disableCode,
                  password: disablePassword,
                })
              }
              disabled={
                disableMutation.isPending ||
                disableCode.length !== 6 ||
                !disablePassword
              }
            >
              {disableMutation.isPending ? "Disabling..." : "Disable 2FA"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
