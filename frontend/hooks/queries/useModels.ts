"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import {
  GeneratedModel,
  ModelGenerationResult,
  MaterializeModelResult,
} from "@/types/models";
import toast from "react-hot-toast";

/**
 * Fetch all generated models
 */
export const useModels = () => {
  return useQuery({
    queryKey: ["models"],
    queryFn: async () => {
      const { data } = await api.get<GeneratedModel[]>("/models");
      return data;
    },
    refetchInterval: 30000, // Refetch every 30 seconds
  });
};

/**
 * Fetch a single model by ID
 */
export const useModel = (id: string) => {
  return useQuery({
    queryKey: ["models", id],
    queryFn: async () => {
      const { data } = await api.get<GeneratedModel>(`/models/${id}`);
      return data;
    },
    enabled: !!id,
  });
};

/**
 * Fetch models for a specific pipeline
 */
export const useModelsByPipeline = (pipelineId: string) => {
  return useQuery({
    queryKey: ["models", "pipeline", pipelineId],
    queryFn: async () => {
      const { data } = await api.get<GeneratedModel[]>(
        `/pipelines/${pipelineId}/models`
      );
      return data;
    },
    enabled: !!pipelineId,
  });
};

/**
 * Generate models for a pipeline using AI
 */
export const useGenerateModels = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (pipelineId: string) => {
      const { data } = await api.post<ModelGenerationResult>(
        `/pipelines/${pipelineId}/models/generate`
      );
      return data;
    },
    onSuccess: (data, pipelineId) => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      queryClient.invalidateQueries({
        queryKey: ["models", "pipeline", pipelineId],
      });
      toast.success(
        `Generated ${data.fact_tables} fact tables and ${data.dimension_tables} dimension tables`
      );
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to generate models"
      );
    },
  });
};

/**
 * Materialize a model as a view in the destination
 */
export const useMaterializeModel = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (modelId: string) => {
      const { data } = await api.post<MaterializeModelResult>(
        `/models/${modelId}/materialize`
      );
      return data;
    },
    onSuccess: (data, modelId) => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      queryClient.invalidateQueries({ queryKey: ["models", modelId] });
      toast.success(data.message || "Model materialized successfully");
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to materialize model"
      );
    },
  });
};

/**
 * Delete a generated model
 */
export const useDeleteModel = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (modelId: string) => {
      await api.delete(`/models/${modelId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      toast.success("Model deleted successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to delete model");
    },
  });
};

/**
 * Refresh/regenerate a single model
 */
export const useRefreshModel = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (modelId: string) => {
      const { data } = await api.post<GeneratedModel>(
        `/models/${modelId}/refresh`
      );
      return data;
    },
    onSuccess: (_, modelId) => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      queryClient.invalidateQueries({ queryKey: ["models", modelId] });
      toast.success("Model refreshed successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to refresh model");
    },
  });
};
