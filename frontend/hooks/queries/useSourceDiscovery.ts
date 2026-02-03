"use client";

import { useMutation, useQuery } from "@tanstack/react-query";
import api from "@/lib/api-client";
import toast from "react-hot-toast";

export interface ConnectionTestRequest {
  source_type: string;
  config: Record<string, any>;
}

export interface ConnectionTestResponse {
  success: boolean;
  message: string;
  metadata?: Record<string, any>;
  error?: string;
}

export interface SchemaDiscoveryRequest {
  source_type: string;
  config: Record<string, any>;
}

export interface TableColumn {
  name: string;
  type: string;
  nullable: boolean;
}

export interface TableInfo {
  schema: string;
  table_name: string;
  row_count?: number;
  size_bytes?: number;
  columns: TableColumn[];
  primary_keys: string[];
  has_updated_at: boolean;
}

export interface SchemaDiscoveryResponse {
  databases: string[];
  schemas: string[];
  tables: TableInfo[];
}

export interface TablePreviewRequest {
  source_type: string;
  config: Record<string, any>;
  schema: string;
  table: string;
  limit?: number;
}

export interface TablePreviewResponse {
  columns: string[];
  rows: any[][];
  total_rows?: number;
}

export const useTestConnection = () => {
  return useMutation({
    mutationFn: async (request: ConnectionTestRequest) => {
      const { data } = await api.post<ConnectionTestResponse>(
        "/sources/discovery/test-connection",
        request
      );
      return data;
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message);
      } else {
        toast.error(data.error || data.message);
      }
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to test connection"
      );
    },
  });
};

export const useDiscoverSchema = () => {
  return useMutation({
    mutationFn: async (request: SchemaDiscoveryRequest) => {
      const { data} = await api.post<SchemaDiscoveryResponse>(
        "/sources/discovery/discover-schema",
        request
      );
      return data;
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to discover schema"
      );
    },
  });
};

export const usePreviewTable = () => {
  return useMutation({
    mutationFn: async (request: TablePreviewRequest) => {
      const { data } = await api.post<TablePreviewResponse>(
        "/sources/discovery/preview-table",
        request
      );
      return data;
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to preview table"
      );
    },
  });
};
