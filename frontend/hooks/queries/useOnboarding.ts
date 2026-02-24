/**
 * Onboarding API Hooks
 *
 * TanStack Query hooks for onboarding flow.
 */
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";
import {
  OnboardingStatusResponse,
  RoleOption,
  SourceRecommendation,
  UserRole,
} from "@/types/onboarding";

// Query keys
export const onboardingKeys = {
  all: ["onboarding"] as const,
  status: () => [...onboardingKeys.all, "status"] as const,
  roles: () => [...onboardingKeys.all, "roles"] as const,
  sourceRecommendations: () => [...onboardingKeys.all, "source-recommendations"] as const,
  dashboardRecommendations: () => [...onboardingKeys.all, "dashboard-recommendations"] as const,
};

/**
 * Get available role options
 */
export function useRoleOptions() {
  return useQuery({
    queryKey: onboardingKeys.roles(),
    queryFn: async () => {
      const response = await apiClient.get<RoleOption[]>("/onboarding/roles");
      return response.data;
    },
  });
}

/**
 * Get current onboarding status and checklist
 */
export function useOnboardingStatus() {
  return useQuery({
    queryKey: onboardingKeys.status(),
    queryFn: async () => {
      const response = await apiClient.get<OnboardingStatusResponse>("/onboarding/status");
      return response.data;
    },
  });
}

/**
 * Get source recommendations based on role
 */
export function useSourceRecommendations() {
  return useQuery({
    queryKey: onboardingKeys.sourceRecommendations(),
    queryFn: async () => {
      const response = await apiClient.get<SourceRecommendation[]>(
        "/onboarding/recommendations/sources"
      );
      return response.data;
    },
  });
}

/**
 * Get dashboard recommendations based on role
 */
export function useDashboardRecommendations() {
  return useQuery({
    queryKey: onboardingKeys.dashboardRecommendations(),
    queryFn: async () => {
      const response = await apiClient.get<{ dashboard_ids: string[] }>(
        "/onboarding/recommendations/dashboards"
      );
      return response.data.dashboard_ids;
    },
  });
}

/**
 * Set user's business role
 */
export function useSetRole() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (role: UserRole) => {
      const response = await apiClient.post<{
        message: string;
        role: string;
        status: string;
      }>("/onboarding/role", { role });
      return response.data;
    },
    onSuccess: () => {
      // Invalidate status to refetch with new role
      queryClient.invalidateQueries({ queryKey: onboardingKeys.status() });
      queryClient.invalidateQueries({ queryKey: onboardingKeys.sourceRecommendations() });
      queryClient.invalidateQueries({ queryKey: onboardingKeys.dashboardRecommendations() });
    },
  });
}

/**
 * Mark an onboarding step as complete
 */
export function useMarkStepComplete() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (step: string) => {
      const response = await apiClient.post<{
        message: string;
        step: string;
        completion_percentage: number;
        status: string;
      }>("/onboarding/step", { step });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: onboardingKeys.status() });
    },
  });
}

/**
 * Skip onboarding
 */
export function useSkipOnboarding() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (reason?: string) => {
      const response = await apiClient.post<{
        message: string;
        status: string;
      }>("/onboarding/skip", { reason });
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: onboardingKeys.status() });
    },
  });
}

/**
 * Sync onboarding progress from existing data
 */
export function useSyncProgress() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      const response = await apiClient.post<{
        message: string;
        completion_percentage: number;
        status: string;
      }>("/onboarding/sync");
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: onboardingKeys.status() });
    },
  });
}
