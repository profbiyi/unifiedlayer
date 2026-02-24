"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useCurrentUser } from "@/hooks/queries/useAuth";
import { OnboardingWidget } from "@/components/onboarding/OnboardingWidget";
import {
  LayoutDashboard,
  Workflow,
  Database,
  HardDrive,
  Activity,
  GitBranch,
  Users,
  Settings,
  Shield,
  Sparkles,
  BarChart3,
  Lightbulb,
  MessageSquareText,
  Rocket,
  Boxes,
} from "lucide-react";

const navItems = [
  {
    title: "Overview",
    href: "/overview",
    icon: LayoutDashboard,
  },
  {
    title: "Get Started",
    href: "/onboarding",
    icon: Rocket,
  },
  {
    title: "Templates",
    href: "/templates",
    icon: Sparkles,
  },
  {
    title: "Ask AI",
    href: "/ask",
    icon: MessageSquareText,
  },
  {
    title: "Pipelines",
    href: "/pipelines",
    icon: Workflow,
  },
  {
    title: "Sources",
    href: "/sources",
    icon: Database,
  },
  {
    title: "Destinations",
    href: "/destinations",
    icon: HardDrive,
  },
  {
    title: "Runs",
    href: "/runs",
    icon: Activity,
  },
  {
    title: "Lineage",
    href: "/lineage",
    icon: GitBranch,
  },
  {
    title: "Models",
    href: "/models",
    icon: Boxes,
  },
  {
    title: "Analytics",
    href: "/analytics",
    icon: BarChart3,
  },
  {
    title: "Insights",
    href: "/insights",
    icon: Lightbulb,
  },
  {
    title: "Team",
    href: "/team",
    icon: Users,
  },
  {
    title: "Admin",
    href: "/admin",
    icon: Shield,
    superAdminOnly: true, // Only show to super admins
  },
  {
    title: "Settings",
    href: "/settings",
    icon: Settings,
  },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { data: user } = useCurrentUser();

  const isSuperAdmin = user?.roles?.some(
    (role: string) => role.toLowerCase() === "super_admin" || role === "SUPER_ADMIN"
  );

  const visibleItems = navItems.filter(
    (item) => !(item as any).superAdminOnly || isSuperAdmin
  );

  return (
    <div className="flex h-full w-64 flex-col border-r bg-card">
      <div className="flex h-16 items-center border-b px-6">
        <h1 className="text-xl font-bold">UnifiedLayer</h1>
      </div>
      <nav className="flex-1 space-y-1 p-4 overflow-y-auto">
        {visibleItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href;

          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                isActive
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              <Icon className="h-5 w-5" />
              {item.title}
            </Link>
          );
        })}
      </nav>
      {/* Onboarding progress widget */}
      <div className="p-4 border-t">
        <OnboardingWidget />
      </div>
    </div>
  );
}
