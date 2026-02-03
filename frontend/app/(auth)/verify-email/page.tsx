"use client";

import { Suspense, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import { useVerifyEmail } from "@/hooks/queries/useAuth";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function Wrapper({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-screen items-center justify-center p-4">
      <div className="w-full max-w-md">{children}</div>
    </div>
  );
}

function VerifyEmailContent() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const verifyMutation = useVerifyEmail();

  useEffect(() => {
    if (token && !verifyMutation.isSuccess && !verifyMutation.isPending && !verifyMutation.isError) {
      verifyMutation.mutate(token);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token]);

  if (!token) {
    return (
      <Wrapper>
        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl font-bold">Invalid link</CardTitle>
            <CardDescription>
              No verification token was provided. Please check your email for the
              correct link.
            </CardDescription>
          </CardHeader>
          <CardFooter>
            <Link href="/login" className="w-full">
              <Button variant="outline" className="w-full">Go to Login</Button>
            </Link>
          </CardFooter>
        </Card>
      </Wrapper>
    );
  }

  if (verifyMutation.isPending) {
    return (
      <Wrapper>
        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl font-bold">Verifying...</CardTitle>
            <CardDescription>
              Please wait while we verify your email address.
            </CardDescription>
          </CardHeader>
        </Card>
      </Wrapper>
    );
  }

  if (verifyMutation.isError) {
    const errorMessage =
      (verifyMutation.error as any)?.response?.data?.detail ||
      "Verification failed. The link may be invalid or expired.";

    return (
      <Wrapper>
        <Card>
          <CardHeader className="space-y-1">
            <CardTitle className="text-2xl font-bold">Verification failed</CardTitle>
            <CardDescription>{errorMessage}</CardDescription>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Try registering again or contact support if the problem persists.
            </p>
          </CardContent>
          <CardFooter>
            <Link href="/login" className="w-full">
              <Button variant="outline" className="w-full">Go to Login</Button>
            </Link>
          </CardFooter>
        </Card>
      </Wrapper>
    );
  }

  return (
    <Wrapper>
      <Card>
        <CardHeader className="space-y-1">
          <CardTitle className="text-2xl font-bold">Email verified</CardTitle>
          <CardDescription>
            Your email has been verified successfully. You can now log in to your
            account.
          </CardDescription>
        </CardHeader>
        <CardFooter>
          <Link href="/login" className="w-full">
            <Button className="w-full">Go to Login</Button>
          </Link>
        </CardFooter>
      </Card>
    </Wrapper>
  );
}

export default function VerifyEmailPage() {
  return (
    <Suspense
      fallback={
        <Wrapper>
          <Card>
            <CardHeader className="space-y-1">
              <CardTitle className="text-2xl font-bold">Loading...</CardTitle>
            </CardHeader>
          </Card>
        </Wrapper>
      }
    >
      <VerifyEmailContent />
    </Suspense>
  );
}
