"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import {
  SQLTransformation,
  CreateTransformationRequest,
  UpdateTransformationRequest,
  ReorderTransformationsRequest,
  SQLPreviewRequest,
  SQLPreviewResult,
} from "@/types/transformation";
import toast from "react-hot-toast";

/**
 * Fetch all transformations for a pipeline
 */
export const useTransformations = (pipelineId: string) => {
  return useQuery({
    queryKey: ["transformations", pipelineId],
    queryFn: async () => {
      const { data } = await api.get<SQLTransformation[]>(
        `/pipelines/${pipelineId}/transformations`
      );
      return data;
    },
    enabled: !!pipelineId,
  });
};

/**
 * Fetch a single transformation by ID
 */
export const useTransformation = (pipelineId: string, transformationId: string) => {
  return useQuery({
    queryKey: ["transformations", pipelineId, transformationId],
    queryFn: async () => {
      const { data } = await api.get<SQLTransformation>(
        `/pipelines/${pipelineId}/transformations/${transformationId}`
      );
      return data;
    },
    enabled: !!pipelineId && !!transformationId,
  });
};

/**
 * Create a new transformation
 */
export const useCreateTransformation = (pipelineId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (transformation: CreateTransformationRequest) => {
      const { data } = await api.post<SQLTransformation>(
        `/pipelines/${pipelineId}/transformations`,
        transformation
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transformations", pipelineId] });
      toast.success("Transformation created successfully");
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to create transformation"
      );
    },
  });
};

/**
 * Update an existing transformation
 */
export const useUpdateTransformation = (pipelineId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      transformationId,
      data: transformationData,
    }: {
      transformationId: string;
      data: UpdateTransformationRequest;
    }) => {
      const { data } = await api.put<SQLTransformation>(
        `/pipelines/${pipelineId}/transformations/${transformationId}`,
        transformationData
      );
      return data;
    },
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["transformations", pipelineId] });
      queryClient.invalidateQueries({
        queryKey: ["transformations", pipelineId, variables.transformationId],
      });
      toast.success("Transformation updated successfully");
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to update transformation"
      );
    },
  });
};

/**
 * Delete a transformation
 */
export const useDeleteTransformation = (pipelineId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (transformationId: string) => {
      await api.delete(`/pipelines/${pipelineId}/transformations/${transformationId}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transformations", pipelineId] });
      toast.success("Transformation deleted successfully");
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to delete transformation"
      );
    },
  });
};

/**
 * Reorder transformations
 */
export const useReorderTransformations = (pipelineId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (request: ReorderTransformationsRequest) => {
      const { data } = await api.put<SQLTransformation[]>(
        `/pipelines/${pipelineId}/transformations/reorder`,
        request
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transformations", pipelineId] });
      toast.success("Transformations reordered successfully");
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to reorder transformations"
      );
    },
  });
};

/**
 * Toggle transformation active status
 */
export const useToggleTransformation = (pipelineId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      transformationId,
      isActive,
    }: {
      transformationId: string;
      isActive: boolean;
    }) => {
      const { data } = await api.patch<SQLTransformation>(
        `/pipelines/${pipelineId}/transformations/${transformationId}/toggle`,
        { is_active: isActive }
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transformations", pipelineId] });
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to toggle transformation"
      );
    },
  });
};

/**
 * Test/preview SQL query
 */
export const useTestSQL = (pipelineId: string) => {
  return useMutation({
    mutationFn: async (request: SQLPreviewRequest) => {
      const { data } = await api.post<SQLPreviewResult>(
        `/pipelines/${pipelineId}/transformations/test`,
        request
      );
      return data;
    },
    onError: () => {
      // SQL errors are displayed in the UI, no additional handling needed
    },
  });
};

/**
 * Duplicate a transformation
 */
export const useDuplicateTransformation = (pipelineId: string) => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (transformationId: string) => {
      const { data } = await api.post<SQLTransformation>(
        `/pipelines/${pipelineId}/transformations/${transformationId}/duplicate`
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["transformations", pipelineId] });
      toast.success("Transformation duplicated successfully");
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to duplicate transformation"
      );
    },
  });
};
