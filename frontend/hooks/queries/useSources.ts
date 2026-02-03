"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { Source } from "@/types/pipeline";
import toast from "react-hot-toast";

export const useSources = () => {
  return useQuery({
    queryKey: ["sources"],
    queryFn: async () => {
      const { data } = await api.get<Source[]>("/sources");
      return data;
    },
  });
};

export const useSource = (id: string) => {
  return useQuery({
    queryKey: ["sources", id],
    queryFn: async () => {
      const { data } = await api.get<Source>(`/sources/${id}`);
      return data;
    },
    enabled: !!id,
  });
};

export const useCreateSource = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (source: Omit<Source, "id" | "created_at">) => {
      const { data } = await api.post<Source>("/sources", source);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      toast.success("Source created successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to create source");
    },
  });
};

export const useDeleteSource = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/sources/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      toast.success("Source deleted successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to delete source");
    },
  });
};

export const useTestConnection = () => {
  return useMutation({
    mutationFn: async (sourceId: string) => {
      const { data } = await api.post(`/sources/${sourceId}/test`);
      return data;
    },
    onSuccess: () => {
      toast.success("Connection test successful");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Connection test failed");
    },
  });
};
