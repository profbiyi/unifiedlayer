"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import toast from "react-hot-toast";

// Types
export interface HealthIssue {
  code: string;
  message: string;
  severity: "critical" | "warning" | "info";
}

export interface HealthMetrics {
  connection_test?: {
    success: boolean;
    message: string;
    latency_ms: number | null;
    error: string | null;
    checked_at: string;
  };
  token_expiry?: {
    has_oauth: boolean;
    expires_at: string | null;
    days_until_expiry: number | null;
    warning: boolean;
    expired: boolean;
  };
  success_rate?: {
    total_runs: number;
    successful_runs: number;
    failed_runs: number;
    success_rate: number | null;
    has_data: boolean;
  };
  sync_freshness?: {
    last_successful_sync: string | null;
    hours_since_sync: number | null;
    is_stale: boolean;
    has_ever_synced: boolean;
    threshold_hours: number;
  };
  consecutive_failures?: {
    consecutive_failures: number;
    threshold: number;
    is_concerning: boolean;
  };
}

export interface SourceHealth {
  source_id: string;
  source_name: string;
  source_type: string;
  status: "healthy" | "warning" | "critical" | "unknown";
  score: number;
  issues: HealthIssue[];
  metrics: HealthMetrics;
  last_checked_at: string | null;
}

export interface PipelineHealth {
  pipeline_id: string;
  pipeline_name: string;
  status: "healthy" | "warning" | "critical" | "unknown";
  score: number;
  issues: HealthIssue[];
  metrics: HealthMetrics;
  last_checked_at: string | null;
}

export interface DestinationHealth {
  destination_id: string;
  destination_name: string;
  destination_type: string;
  status: "healthy" | "warning" | "critical" | "unknown";
  score: number;
  issues: HealthIssue[];
  metrics: HealthMetrics;
  last_checked_at: string | null;
}

export interface HealthOverview {
  total_resources: number;
  healthy: number;
  warning: number;
  critical: number;
  unknown: number;
  by_type: {
    source: { healthy: number; warning: number; critical: number; unknown: number; total: number };
    pipeline: { healthy: number; warning: number; critical: number; unknown: number; total: number };
    destination: { healthy: number; warning: number; critical: number; unknown: number; total: number };
  };
  average_score: number;
  overall_status: "healthy" | "warning" | "critical" | "unknown";
  critical_issues: Array<{
    resource_type: string;
    resource_id: number;
    issue: HealthIssue;
  }>;
}

export interface HealthCheckResult {
  message: string;
  status: string;
  score: number;
  issues_count: number;
}

export interface HealthHistoryItem {
  id: number;
  status: string;
  score: number;
  issues: HealthIssue[];
  metrics: HealthMetrics;
  check_type: string;
  checked_at: string;
}

export interface HealthHistoryResponse {
  items: HealthHistoryItem[];
  total: number;
}

// Query keys
const healthKeys = {
  all: ["health"] as const,
  overview: () => [...healthKeys.all, "overview"] as const,
  sources: (status?: string) => [...healthKeys.all, "sources", { status }] as const,
  pipelines: (status?: string) => [...healthKeys.all, "pipelines", { status }] as const,
  destinations: (status?: string) => [...healthKeys.all, "destinations", { status }] as const,
  source: (id: string) => [...healthKeys.all, "source", id] as const,
  pipeline: (id: string) => [...healthKeys.all, "pipeline", id] as const,
  history: (resourceType: string, resourceId: string) =>
    [...healthKeys.all, "history", resourceType, resourceId] as const,
};

/**
 * Get overall health overview for the organization.
 */
export const useHealthOverview = () => {
  return useQuery({
    queryKey: healthKeys.overview(),
    queryFn: async () => {
      const { data } = await api.get<HealthOverview>("/health/overview");
      return data;
    },
    refetchInterval: 60000, // Refetch every minute
    staleTime: 30000, // Consider fresh for 30 seconds
  });
};

/**
 * Get health status for all sources.
 */
export const useSourcesHealth = (statusFilter?: string) => {
  return useQuery({
    queryKey: healthKeys.sources(statusFilter),
    queryFn: async () => {
      const params = statusFilter ? { status_filter: statusFilter } : {};
      const { data } = await api.get<SourceHealth[]>("/health/sources", { params });
      return data;
    },
    refetchInterval: 60000,
    staleTime: 30000,
  });
};

/**
 * Get health status for all pipelines.
 */
export const usePipelinesHealth = (statusFilter?: string) => {
  return useQuery({
    queryKey: healthKeys.pipelines(statusFilter),
    queryFn: async () => {
      const params = statusFilter ? { status_filter: statusFilter } : {};
      const { data } = await api.get<PipelineHealth[]>("/health/pipelines", { params });
      return data;
    },
    refetchInterval: 60000,
    staleTime: 30000,
  });
};

/**
 * Get health status for all destinations.
 */
export const useDestinationsHealth = (statusFilter?: string) => {
  return useQuery({
    queryKey: healthKeys.destinations(statusFilter),
    queryFn: async () => {
      const params = statusFilter ? { status_filter: statusFilter } : {};
      const { data } = await api.get<DestinationHealth[]>("/health/destinations", { params });
      return data;
    },
    refetchInterval: 60000,
    staleTime: 30000,
  });
};

/**
 * Get detailed health for a specific source.
 */
export const useSourceHealth = (sourceId: string) => {
  return useQuery({
    queryKey: healthKeys.source(sourceId),
    queryFn: async () => {
      const { data } = await api.get<SourceHealth>(`/health/source/${sourceId}`);
      return data;
    },
    enabled: !!sourceId,
    staleTime: 30000,
  });
};

/**
 * Get detailed health for a specific pipeline.
 */
export const usePipelineHealth = (pipelineId: string) => {
  return useQuery({
    queryKey: healthKeys.pipeline(pipelineId),
    queryFn: async () => {
      const { data } = await api.get<PipelineHealth>(`/health/pipeline/${pipelineId}`);
      return data;
    },
    enabled: !!pipelineId,
    staleTime: 30000,
  });
};

/**
 * Get health check history for a resource.
 */
export const useHealthHistory = (
  resourceType: string,
  resourceId: string,
  options?: { skip?: number; limit?: number }
) => {
  return useQuery({
    queryKey: healthKeys.history(resourceType, resourceId),
    queryFn: async () => {
      const params = {
        skip: options?.skip || 0,
        limit: options?.limit || 20,
      };
      const { data } = await api.get<HealthHistoryResponse>(
        `/health/history/${resourceType}/${resourceId}`,
        { params }
      );
      return data;
    },
    enabled: !!resourceType && !!resourceId,
  });
};

/**
 * Trigger a health check for a source.
 */
export const useTriggerSourceHealthCheck = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      sourceId,
      runConnectionTest = true,
    }: {
      sourceId: string;
      runConnectionTest?: boolean;
    }) => {
      const params = { run_connection_test: runConnectionTest };
      const { data } = await api.post<HealthCheckResult>(
        `/health/source/${sourceId}/check`,
        null,
        { params }
      );
      return data;
    },
    onSuccess: (data, variables) => {
      // Invalidate health queries to refresh data
      queryClient.invalidateQueries({ queryKey: healthKeys.all });
      toast.success(data.message);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Health check failed");
    },
  });
};

/**
 * Trigger a health check for a pipeline.
 */
export const useTriggerPipelineHealthCheck = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (pipelineId: string) => {
      const { data } = await api.post<HealthCheckResult>(
        `/health/pipeline/${pipelineId}/check`
      );
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: healthKeys.all });
      toast.success(data.message);
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Health check failed");
    },
  });
};

/**
 * Hook to get health status for a specific source by ID.
 * Returns just the status for quick inline usage.
 */
export const useSourceHealthStatus = (sourceId: string) => {
  const { data } = useSourcesHealth();

  if (!data || !sourceId) return null;

  const sourceHealth = data.find((h) => h.source_id === sourceId);
  return sourceHealth
    ? {
        status: sourceHealth.status,
        score: sourceHealth.score,
        issues: sourceHealth.issues,
      }
    : null;
};

/**
 * Hook to get health status for a specific pipeline by ID.
 * Returns just the status for quick inline usage.
 */
export const usePipelineHealthStatus = (pipelineId: string) => {
  const { data } = usePipelinesHealth();

  if (!data || !pipelineId) return null;

  const pipelineHealth = data.find((h) => h.pipeline_id === pipelineId);
  return pipelineHealth
    ? {
        status: pipelineHealth.status,
        score: pipelineHealth.score,
        issues: pipelineHealth.issues,
      }
    : null;
};
