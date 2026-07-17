import Link from "next/link";
import { Database, BarChart3, Workflow, Shield, Globe } from "lucide-react";

export default function AuthLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    // force-light: auth pages are public-facing — always render bright,
    // regardless of any stored in-app theme preference.
    <div className="force-light grid min-h-screen bg-background text-foreground lg:grid-cols-2">
      {/* Left panel — branding */}
      <div className="hidden lg:flex flex-col justify-between bg-gradient-to-br from-blue-700 via-blue-600 to-sky-500 p-10 text-white">
        <div>
          <Link href="/" className="flex items-center gap-2">
            <Database className="h-7 w-7" />
            <span className="text-xl font-bold">UnifiedLayer</span>
          </Link>
        </div>

        <div className="space-y-8">
          <div>
            <h1 className="font-display text-3xl font-bold leading-tight xl:text-4xl">
              Welcome back.
              <br />
              Your numbers are waiting.
            </h1>
            <p className="mt-4 max-w-md text-white/80">
              Paystack, M-Pesa, your bank, your books. Everything your
              business does, together in one place you control.
            </p>
          </div>

          <div className="grid grid-cols-2 gap-4 max-w-md">
            <div className="flex items-center gap-3 rounded-lg bg-white/10 px-4 py-3">
              <BarChart3 className="h-5 w-5 shrink-0" />
              <span className="text-sm font-medium">Unified Analytics</span>
            </div>
            <div className="flex items-center gap-3 rounded-lg bg-white/10 px-4 py-3">
              <Workflow className="h-5 w-5 shrink-0" />
              <span className="text-sm font-medium">Orchestration</span>
            </div>
            <div className="flex items-center gap-3 rounded-lg bg-white/10 px-4 py-3">
              <Globe className="h-5 w-5 shrink-0" />
              <span className="text-sm font-medium">15+ Connectors</span>
            </div>
            <div className="flex items-center gap-3 rounded-lg bg-white/10 px-4 py-3">
              <Shield className="h-5 w-5 shrink-0" />
              <span className="text-sm font-medium">NDPA &amp; GDPR Ready</span>
            </div>
          </div>
        </div>

        <p className="text-xs text-white/60">
          &copy; 2026 UnifiedLayer. All rights reserved.
        </p>
      </div>

      {/* Right panel — form */}
      <div className="flex flex-col items-center justify-center bg-background p-6 sm:p-10">
        {/* Mobile logo */}
        <div className="mb-8 flex items-center gap-2 lg:hidden">
          <Link href="/" className="flex items-center gap-2">
            <Database className="h-6 w-6 text-primary" />
            <span className="text-xl font-bold">UnifiedLayer</span>
          </Link>
        </div>

        <div className="w-full max-w-md">{children}</div>
      </div>
    </div>
  );
}
