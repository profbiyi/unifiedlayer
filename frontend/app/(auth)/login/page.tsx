"use client";

import { useState } from "react";
import Link from "next/link";
import { useLogin, useVerify2FA } from "@/hooks/queries/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Loader2, ShieldCheck } from "lucide-react";

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [requires2FA, setRequires2FA] = useState(false);
  const [tempToken, setTempToken] = useState("");
  const [totpCode, setTotpCode] = useState("");
  const loginMutation = useLogin({
    on2FARequired: (token: string) => {
      setTempToken(token);
      setRequires2FA(true);
    },
  });
  const verify2FAMutation = useVerify2FA();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loginMutation.mutate({ username, password });
  };

  const handle2FASubmit = (e: React.FormEvent) => {
    e.preventDefault();
    verify2FAMutation.mutate({ temp_token: tempToken, code: totpCode });
  };

  if (requires2FA) {
    return (
      <Card className="border-0 shadow-none sm:border sm:shadow-sm">
        <CardHeader className="space-y-1 text-center">
          <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10">
            <ShieldCheck className="h-6 w-6 text-primary" />
          </div>
          <CardTitle className="text-2xl font-bold">
            Two-Factor Authentication
          </CardTitle>
          <CardDescription>
            Enter the 6-digit code from your authenticator app
          </CardDescription>
        </CardHeader>
        <form onSubmit={handle2FASubmit}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="totp-code">Verification Code</Label>
              <Input
                id="totp-code"
                type="text"
                inputMode="numeric"
                pattern="[0-9]{6}"
                maxLength={6}
                placeholder="000000"
                value={totpCode}
                onChange={(e) =>
                  setTotpCode(e.target.value.replace(/\D/g, "").slice(0, 6))
                }
                required
                disabled={verify2FAMutation.isPending}
                autoFocus
                className="text-center text-2xl tracking-widest"
              />
            </div>
          </CardContent>
          <CardFooter className="flex flex-col space-y-3">
            <Button
              type="submit"
              className="w-full"
              disabled={verify2FAMutation.isPending || totpCode.length !== 6}
            >
              {verify2FAMutation.isPending && (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              )}
              {verify2FAMutation.isPending ? "Verifying..." : "Verify"}
            </Button>
            <Button
              type="button"
              variant="ghost"
              className="w-full"
              onClick={() => {
                setRequires2FA(false);
                setTempToken("");
                setTotpCode("");
              }}
            >
              Back to login
            </Button>
          </CardFooter>
        </form>
      </Card>
    );
  }

  return (
    <Card className="border-0 shadow-none sm:border sm:shadow-sm">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold">Welcome back</CardTitle>
        <CardDescription>
          Sign in to your UnifiedLayer account
        </CardDescription>
      </CardHeader>
      <form onSubmit={handleSubmit}>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="username">Email</Label>
            <Input
              id="username"
              type="text"
              placeholder="name@company.com"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              disabled={loginMutation.isPending}
              autoFocus
            />
          </div>
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label htmlFor="password">Password</Label>
              <Link
                href="/forgot-password"
                className="text-xs text-muted-foreground hover:text-primary transition-colors"
              >
                Forgot password?
              </Link>
            </div>
            <Input
              id="password"
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              disabled={loginMutation.isPending}
            />
          </div>

          {loginMutation.isError && (
            <p className="text-sm text-destructive">
              Invalid email or password. Please try again.
            </p>
          )}
        </CardContent>
        <CardFooter className="flex flex-col space-y-4">
          <Button
            type="submit"
            className="w-full"
            disabled={loginMutation.isPending}
          >
            {loginMutation.isPending && (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            )}
            {loginMutation.isPending ? "Signing in..." : "Sign In"}
          </Button>

          <div className="relative my-2">
            <div className="absolute inset-0 flex items-center">
              <span className="w-full border-t" />
            </div>
            <div className="relative flex justify-center text-xs uppercase">
              <span className="bg-background px-2 text-muted-foreground">
                Or continue with
              </span>
            </div>
          </div>

          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={() => {
              window.location.href = `${process.env.NEXT_PUBLIC_API_URL}/auth/google/login`;
            }}
          >
            <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24">
              <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Sign in with Google
          </Button>

          <p className="text-xs text-muted-foreground text-center">
            Access is invitation-only.{" "}
            <a
              href="mailto:hello@unifiedlayer.io"
              className="text-primary hover:underline"
            >
              Request access
            </a>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
}
