"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import apiClient from "@/lib/api-client";
import toast from "react-hot-toast";

// Types
export interface SuggestedJoin {
  id: string;
  left_source: string;
  left_table: string;
  left_column: string;
  right_source: string;
  right_table: string;
  right_column: string;
  confidence: number;
  reasoning: string;
  join_type: string;
  sample_matches: string[][];
}

export interface CrossSourceAnalysis {
  sources_analyzed: number;
  tables_found: number;
  suggested_joins: SuggestedJoin[];
}

export interface AutoModelSettings {
  auto_model_enabled: boolean;
  cross_source_enabled: boolean;
  last_model_generation: string | null;
  models_generated: number;
}

export interface AvailableSource {
  id: number;
  name: string;
  type: string;
  has_synced_data: boolean;
}

export interface AvailableSourcesResponse {
  sources: AvailableSource[];
  total: number;
}

export interface UnifiedModelResponse {
  models_created: number;
  model_ids: string[];
  message: string;
}

// Query keys
export const crossSourceKeys = {
  all: ["cross-source"] as const,
  settings: () => [...crossSourceKeys.all, "settings"] as const,
  sources: () => [...crossSourceKeys.all, "sources"] as const,
  analysis: (sourceIds?: number[]) =>
    [...crossSourceKeys.all, "analysis", sourceIds] as const,
};

// Get auto-model settings
export function useAutoModelSettings() {
  return useQuery({
    queryKey: crossSourceKeys.settings(),
    queryFn: async () => {
      const { data } = await apiClient.get<AutoModelSettings>(
        "/cross-source/settings"
      );
      return data;
    },
  });
}

// Update auto-model settings
export function useUpdateAutoModelSettings() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (settings: {
      enabled: boolean;
      cross_source_enabled: boolean;
    }) => {
      const { data } = await apiClient.put<AutoModelSettings>(
        "/cross-source/settings",
        settings
      );
      return data;
    },
    onSuccess: (data) => {
      queryClient.setQueryData(crossSourceKeys.settings(), data);
      toast.success("AI modeling settings updated");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to update settings");
    },
  });
}

// Get available sources for cross-source modeling
export function useAvailableSources() {
  return useQuery({
    queryKey: crossSourceKeys.sources(),
    queryFn: async () => {
      const { data } = await apiClient.get<AvailableSourcesResponse>(
        "/cross-source/sources"
      );
      return data;
    },
  });
}

// Analyze sources for cross-source relationships
export function useAnalyzeSources() {
  return useMutation({
    mutationFn: async (sourceIds?: number[]) => {
      const { data } = await apiClient.post<CrossSourceAnalysis>(
        "/cross-source/analyze",
        { source_ids: sourceIds || null }
      );
      return data;
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Analysis failed");
    },
  });
}

// Generate unified models from confirmed joins
export function useGenerateUnifiedModels() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: {
      confirmed_join_ids: string[];
      custom_joins?: Record<string, unknown>[];
      primary_source: string;
    }) => {
      const { data } = await apiClient.post<UnifiedModelResponse>(
        "/cross-source/generate",
        request
      );
      return data;
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["models"] });
      toast.success(data.message);

      // Trigger celebration for first unified models
      const hasCreatedUnified = localStorage.getItem("unifiedlayer_unified_models_created");
      if (!hasCreatedUnified && data.models_created > 0) {
        localStorage.setItem("unifiedlayer_unified_models_created", "true");
        window.dispatchEvent(new CustomEvent("unifiedlayer:celebration"));
      }
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Model generation failed");
    },
  });
}
