"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import {
  Pipeline,
  CreatePipelineRequest,
  UpdatePipelineRequest,
  PipelineRun,
} from "@/types/pipeline";
import toast from "react-hot-toast";

export const usePipelines = () => {
  return useQuery({
    queryKey: ["pipelines"],
    queryFn: async () => {
      const { data } = await api.get<Pipeline[]>("/pipelines");
      return data;
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  });
};

export const usePipeline = (id: string) => {
  return useQuery({
    queryKey: ["pipelines", id],
    queryFn: async () => {
      const { data } = await api.get<Pipeline>(`/pipelines/${id}`);
      return data;
    },
    enabled: !!id,
  });
};

export const useCreatePipeline = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (pipeline: CreatePipelineRequest) => {
      const { data } = await api.post<Pipeline>("/pipelines", pipeline);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
      toast.success("Pipeline created successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to create pipeline");
    },
  });
};

export const useUpdatePipeline = (id: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (pipeline: UpdatePipelineRequest) => {
      const { data } = await api.put<Pipeline>(`/pipelines/${id}`, pipeline);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
      queryClient.invalidateQueries({ queryKey: ["pipelines", id] });
      toast.success("Pipeline updated successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to update pipeline");
    },
  });
};

export const useDeletePipeline = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/pipelines/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
      toast.success("Pipeline deleted successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to delete pipeline");
    },
  });
};

export const useClonePipeline = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post<Pipeline>(`/pipelines/${id}/clone`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
      toast.success("Pipeline duplicated successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to duplicate pipeline");
    },
  });
};

export const useTriggerPipeline = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post<PipelineRun>(`/pipelines/${id}/run`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["runs"] });
      toast.success("Pipeline run triggered successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to trigger pipeline");
    },
  });
};

export const usePipelineRuns = (pipelineId?: string) => {
  return useQuery({
    queryKey: pipelineId ? ["runs", pipelineId] : ["runs"],
    queryFn: async () => {
      // Use correct endpoint format
      const url = pipelineId ? `/pipelines/${pipelineId}/runs` : "/runs";
      const { data } = await api.get<PipelineRun[]>(url);
      return data;
    },
    refetchInterval: 5000, // Refetch every 5 seconds for active runs
  });
};
