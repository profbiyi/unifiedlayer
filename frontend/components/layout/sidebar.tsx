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
  X,
  Plug,
} from "lucide-react";

// Grouped navigation: a flat 16-item list read as noise. Sections give the
// eye resting points and make the product feel calmer.
const navSections = [
  {
    label: null,
    items: [
      { title: "Overview", href: "/overview", icon: LayoutDashboard },
      { title: "Connect", href: "/connect", icon: Plug, highlight: true },
    ],
  },
  {
    label: "Build",
    items: [
      { title: "Pipelines", href: "/pipelines", icon: Workflow },
      { title: "Sources", href: "/sources", icon: Database },
      { title: "Destinations", href: "/destinations", icon: HardDrive },
      { title: "Runs", href: "/runs", icon: Activity },
    ],
  },
  {
    label: "Understand",
    items: [
      { title: "Ask AI", href: "/ask", icon: MessageSquareText },
      { title: "Insights", href: "/insights", icon: Lightbulb },
      { title: "Analytics", href: "/analytics", icon: BarChart3 },
      { title: "Models", href: "/models", icon: Boxes },
      { title: "Lineage", href: "/lineage", icon: GitBranch },
    ],
  },
  {
    label: "Library",
    items: [
      { title: "Templates", href: "/templates", icon: Sparkles },
      { title: "Get Started", href: "/onboarding", icon: Rocket },
    ],
  },
  {
    label: "Manage",
    items: [
      { title: "Team", href: "/team", icon: Users },
      { title: "Admin", href: "/admin", icon: Shield, superAdminOnly: true },
      { title: "Settings", href: "/settings", icon: Settings },
    ],
  },
];

interface SidebarProps {
  /** Whether the mobile drawer is open (controlled by the parent layout). */
  isOpen?: boolean;
  /** Called when the user dismisses the mobile drawer (close button or overlay click). */
  onClose?: () => void;
}

export default function Sidebar({ isOpen = false, onClose }: SidebarProps) {
  const pathname = usePathname();
  const { data: user } = useCurrentUser();

  const isSuperAdmin = user?.roles?.some(
    (role: string) => role.toLowerCase() === "super_admin" || role === "SUPER_ADMIN"
  );

  const visibleSections = navSections
    .map((section) => ({
      ...section,
      items: section.items.filter(
        (item) => !(item as any).superAdminOnly || isSuperAdmin
      ),
    }))
    .filter((section) => section.items.length > 0);

  const handleLinkClick = () => {
    // Close the mobile drawer when navigating
    if (onClose) onClose();
  };

  const sidebarContent = (
    <div className="flex h-full w-64 flex-col border-r bg-card">
      <div className="flex h-16 items-center justify-between border-b px-6">
        <h1 className="text-xl font-bold">UnifiedLayer</h1>
        {/* Close button — only visible on mobile */}
        <button
          onClick={onClose}
          className="md:hidden p-1 rounded-md text-muted-foreground hover:text-foreground hover:bg-accent"
          aria-label="Close menu"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
      <nav className="flex-1 space-y-5 p-4 overflow-y-auto">
        {visibleSections.map((section, sectionIndex) => (
          <div key={section.label ?? sectionIndex} className="space-y-1">
            {section.label && (
              <p className="px-3 pb-1 text-[11px] font-semibold uppercase tracking-wider text-muted-foreground/70">
                {section.label}
              </p>
            )}
            {section.items.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              const isHighlight = !isActive && (item as any).highlight;

              return (
                <Link
                  key={item.href}
                  href={item.href}
                  onClick={handleLinkClick}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary text-primary-foreground"
                      : isHighlight
                      ? "text-primary bg-primary/5 hover:bg-primary/10 border border-primary/20"
                      : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                  )}
                >
                  <Icon className="h-4 w-4" />
                  {item.title}
                </Link>
              );
            })}
          </div>
        ))}
      </nav>
      {/* Onboarding progress widget */}
      <div className="p-4 border-t">
        <OnboardingWidget />
      </div>
    </div>
  );

  return (
    <>
      {/*
       * Desktop: always-visible fixed sidebar (md and above).
       * Mobile: hidden by default, rendered off-screen.
       */}
      <div className="hidden md:flex h-full w-64 flex-shrink-0">
        {sidebarContent}
      </div>

      {/* Mobile drawer overlay + panel */}
      {isOpen && (
        <div className="md:hidden fixed inset-0 z-50 flex">
          {/* Semi-transparent backdrop */}
          <div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm"
            onClick={onClose}
            aria-hidden="true"
          />
          {/* Sidebar panel slides in from the left */}
          <div className="relative z-50 flex h-full w-64 flex-shrink-0 shadow-xl">
            {sidebarContent}
          </div>
        </div>
      )}
    </>
  );
}
