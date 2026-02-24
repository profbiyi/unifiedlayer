/**
 * Onboarding Types
 */

export type UserRole = "founder" | "finance" | "operations" | "sales" | "developer" | "other";

export type OnboardingStatus = "not_started" | "in_progress" | "completed" | "skipped";

export interface RoleOption {
  value: UserRole;
  label: string;
  description: string;
  icon: string;
}

export interface SourceRecommendation {
  type: string;
  name: string;
  reason: string;
  priority: number;
}

export interface ChecklistItem {
  id: string;
  title: string;
  description: string;
  completed: boolean;
  href: string;
}

export interface OnboardingStatusResponse {
  status: OnboardingStatus;
  completion_percentage: number;
  next_step: string;
  business_role: UserRole | null;
  checklist: ChecklistItem[];
}
