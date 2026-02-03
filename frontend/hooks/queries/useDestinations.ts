"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { Destination } from "@/types/pipeline";
import toast from "react-hot-toast";

export const useDestinations = () => {
  return useQuery({
    queryKey: ["destinations"],
    queryFn: async () => {
      const { data } = await api.get<Destination[]>("/destinations");
      return data;
    },
  });
};

export const useDestination = (id: string) => {
  return useQuery({
    queryKey: ["destinations", id],
    queryFn: async () => {
      const { data } = await api.get<Destination>(`/destinations/${id}`);
      return data;
    },
    enabled: !!id,
  });
};

export const useCreateDestination = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (destination: Omit<Destination, "id" | "created_at">) => {
      const { data } = await api.post<Destination>("/destinations", destination);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["destinations"] });
      toast.success("Destination created successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to create destination");
    },
  });
};

export const useDeleteDestination = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/destinations/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["destinations"] });
      toast.success("Destination deleted successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to delete destination");
    },
  });
};

export const useTestDestinationConnection = () => {
  return useMutation({
    mutationFn: async (id: string) => {
      const { data } = await api.post(`/destinations/${id}/test`);
      return data;
    },
    onSuccess: (data) => {
      toast.success(data.message || "Connection test successful");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Connection test failed");
    },
  });
};
