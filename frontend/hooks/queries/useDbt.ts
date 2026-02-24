"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import {
  DbtProject,
  DbtRun,
  CreateDbtProjectRequest,
  UpdateDbtProjectRequest,
  TriggerDbtRunRequest,
  TestConnectionResponse,
  DbtModel,
  DbtModelSummary,
  DbtModelColumn,
} from "@/types/dbt";
import toast from "react-hot-toast";

// Query keys
export const dbtKeys = {
  all: ["dbt"] as const,
  projects: () => [...dbtKeys.all, "projects"] as const,
  project: (id: string) => [...dbtKeys.projects(), id] as const,
  runs: (projectId?: string) => [...dbtKeys.all, "runs", projectId] as const,
  run: (runId: string) => [...dbtKeys.all, "run", runId] as const,
  models: () => [...dbtKeys.all, "models"] as const,
  model: (id: string) => [...dbtKeys.models(), id] as const,
  modelColumns: (id: string) => [...dbtKeys.model(id), "columns"] as const,
};

// Fetch all dbt projects
export const useDbtProjects = () => {
  return useQuery({
    queryKey: dbtKeys.projects(),
    queryFn: async () => {
      const { data } = await api.get<DbtProject[]>("/dbt/projects");
      return data;
    },
    refetchInterval: 30000,
  });
};

// Fetch single dbt project
export const useDbtProject = (id: string) => {
  return useQuery({
    queryKey: dbtKeys.project(id),
    queryFn: async () => {
      const { data } = await api.get<DbtProject>(`/dbt/projects/${id}`);
      return data;
    },
    enabled: !!id,
  });
};

// Create dbt project
export const useCreateDbtProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (project: CreateDbtProjectRequest) => {
      const { data } = await api.post<DbtProject>("/dbt/projects", project);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dbtKeys.projects() });
      toast.success("dbt project created successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to create dbt project");
    },
  });
};

// Update dbt project
export const useUpdateDbtProject = (id: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (project: UpdateDbtProjectRequest) => {
      const { data } = await api.put<DbtProject>(`/dbt/projects/${id}`, project);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dbtKeys.projects() });
      queryClient.invalidateQueries({ queryKey: dbtKeys.project(id) });
      toast.success("dbt project updated successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to update dbt project");
    },
  });
};

// Delete dbt project
export const useDeleteDbtProject = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/dbt/projects/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dbtKeys.projects() });
      toast.success("dbt project deleted successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to delete dbt project");
    },
  });
};

// Test git connection
export const useTestDbtConnection = () => {
  return useMutation({
    mutationFn: async (params: {
      git_repo_url: string;
      git_username?: string;
      git_token?: string;
    }) => {
      const { data } = await api.post<TestConnectionResponse>(
        "/dbt/test-connection",
        params
      );
      return data;
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message || "Connection successful");
      } else {
        toast.error(data.message || "Connection failed");
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Connection test failed");
    },
  });
};

// Trigger dbt run
export const useTriggerDbtRun = (projectId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (params?: TriggerDbtRunRequest) => {
      const { data } = await api.post<DbtRun>(
        `/dbt/projects/${projectId}/run`,
        params || {}
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dbtKeys.projects() });
      queryClient.invalidateQueries({ queryKey: dbtKeys.runs(projectId) });
      toast.success("dbt run started successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to start dbt run");
    },
  });
};

// Cancel dbt run
export const useCancelDbtRun = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (runId: string) => {
      await api.post(`/dbt/runs/${runId}/cancel`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dbtKeys.all });
      toast.success("dbt run cancelled");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to cancel dbt run");
    },
  });
};

// Fetch runs for a project
export const useDbtRuns = (projectId?: string) => {
  return useQuery({
    queryKey: dbtKeys.runs(projectId),
    queryFn: async () => {
      const url = projectId ? `/dbt/projects/${projectId}/runs` : "/dbt/runs";
      const { data } = await api.get<DbtRun[]>(url);
      return data;
    },
    refetchInterval: 5000,
    enabled: projectId ? !!projectId : true,
  });
};

// Fetch single run details
export const useDbtRun = (runId: string) => {
  return useQuery({
    queryKey: dbtKeys.run(runId),
    queryFn: async () => {
      const { data } = await api.get<DbtRun>(`/dbt/runs/${runId}`);
      return data;
    },
    enabled: !!runId,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      // Keep polling while run is in progress
      return status === "running" || status === "pending" ? 3000 : false;
    },
  });
};

// Fetch run logs
export const useDbtRunLogs = (runId: string) => {
  return useQuery({
    queryKey: [...dbtKeys.run(runId), "logs"],
    queryFn: async () => {
      const { data } = await api.get<{ logs: string }>(`/dbt/runs/${runId}/logs`);
      return data.logs;
    },
    enabled: !!runId,
    refetchInterval: (query) => {
      // We'll need to fetch the run status separately or pass it in
      return 5000;
    },
  });
};

// ==================== dbt Models Hooks ====================

// Fetch all dbt models (parsed from manifest)
export const useDbtModels = (params?: {
  search?: string;
  tag?: string;
  schema?: string;
  materialization?: string;
  projectId?: string;
}) => {
  return useQuery({
    queryKey: [...dbtKeys.models(), params],
    queryFn: async () => {
      const searchParams = new URLSearchParams();
      if (params?.search) searchParams.append("search", params.search);
      if (params?.tag) searchParams.append("tag", params.tag);
      if (params?.schema) searchParams.append("schema", params.schema);
      if (params?.materialization) searchParams.append("materialization", params.materialization);
      if (params?.projectId) searchParams.append("project_id", params.projectId);

      const url = `/dbt/models${searchParams.toString() ? `?${searchParams.toString()}` : ""}`;
      const { data } = await api.get<DbtModelSummary[]>(url);
      return data;
    },
    staleTime: 30000,
  });
};

// Fetch single dbt model with full details
export const useDbtModel = (id: string) => {
  return useQuery({
    queryKey: dbtKeys.model(id),
    queryFn: async () => {
      const { data } = await api.get<DbtModel>(`/dbt/models/${id}`);
      return data;
    },
    enabled: !!id,
  });
};

// Fetch model columns
export const useDbtModelColumns = (id: string) => {
  return useQuery({
    queryKey: dbtKeys.modelColumns(id),
    queryFn: async () => {
      const { data } = await api.get<DbtModelColumn[]>(`/dbt/models/${id}/columns`);
      return data;
    },
    enabled: !!id,
  });
};

// Fetch model runs (runs that included this model)
export const useDbtModelRuns = (modelId: string) => {
  return useQuery({
    queryKey: [...dbtKeys.model(modelId), "runs"],
    queryFn: async () => {
      const { data } = await api.get<DbtRun[]>(`/dbt/models/${modelId}/runs`);
      return data;
    },
    enabled: !!modelId,
  });
};

// Refresh/re-parse manifest
export const useRefreshDbtManifest = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (projectId: string) => {
      const { data } = await api.post(`/dbt/projects/${projectId}/refresh-manifest`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: dbtKeys.models() });
      toast.success("Manifest refreshed successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to refresh manifest");
    },
  });
};
