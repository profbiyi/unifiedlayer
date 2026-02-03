import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api-client";

export interface OverviewMetrics {
  timerange: string;
  total_runs: number;
  completed_runs: number;
  failed_runs: number;
  running_runs: number;
  success_rate: number;
  avg_duration_seconds: number;
  total_rows_processed: number;
  active_pipelines: number;
  most_active_pipeline: {
    name: string | null;
    run_count: number;
  };
  slowest_pipeline: {
    name: string | null;
    avg_duration: number;
  };
}

export function useOverviewMetrics(timerange: string = "24h") {
  return useQuery<OverviewMetrics>({
    queryKey: ["overview-metrics", timerange],
    queryFn: async () => {
      const response = await api.get(`/metrics/overview?timerange=${timerange}`);
      return response.data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
}

export interface PipelinePerformance {
  pipeline_name: string;
  timerange: string;
  total_runs: number;
  success_rate: number;
  avg_duration_seconds: number;
  total_rows_processed: number;
  duration_trend: Array<{
    timestamp: string;
    duration: number;
    rows: number;
  }>;
  recent_runs: Array<{
    id: number;
    status: string;
    duration: number | null;
    rows: number | null;
    created_at: string;
  }>;
}

export function usePipelinePerformance(pipelineId: number, timerange: string = "7d") {
  return useQuery<PipelinePerformance>({
    queryKey: ["pipeline-performance", pipelineId, timerange],
    queryFn: async () => {
      const response = await api.get(`/metrics/pipeline/${pipelineId}/performance?timerange=${timerange}`);
      return response.data;
    },
    enabled: !!pipelineId,
    refetchInterval: 30000,
  });
}

export interface SystemHealth {
  database: string;
  sources: number;
  destinations: number;
  active_pipelines: number;
  running_pipelines: number;
  status: string;
}

export function useSystemHealth() {
  return useQuery<SystemHealth>({
    queryKey: ["system-health"],
    queryFn: async () => {
      const response = await api.get("/metrics/system-health");
      return response.data;
    },
    refetchInterval: 10000, // Refresh every 10 seconds
  });
}
