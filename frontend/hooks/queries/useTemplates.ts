"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import toast from "react-hot-toast";

export interface TemplateInfo {
  id: string;
  name: string;
  description: string;
  category: string;
  source_type: string;
  destination_type: string;
  icon: string;
  tags: string[];
}

export interface TemplateCredentialField {
  field: string;
  label: string;
  type: string;
  placeholder: string;
  required: boolean;
  options?: string[];
}

export interface TemplateDetail extends TemplateInfo {
  source_config_template: Record<string, any>;
  destination_config_template: Record<string, any>;
  source_credential_schema: TemplateCredentialField[];
  destination_credential_schema: TemplateCredentialField[];
}

export interface DeployTemplateRequest {
  source_credentials: Record<string, any>;
  destination_credentials: Record<string, any>;
  pipeline_name: string;
  schedule?: string;
}

export interface DeployTemplateResponse {
  pipeline_id: string;
  source_id: string;
  destination_id: string;
  message: string;
}

export const useTemplates = () => {
  return useQuery({
    queryKey: ["templates"],
    queryFn: async () => {
      const { data } = await api.get<TemplateInfo[]>("/api/templates");
      return data;
    },
  });
};

export const useTemplate = (id: string) => {
  return useQuery({
    queryKey: ["templates", id],
    queryFn: async () => {
      const { data } = await api.get<TemplateDetail>(`/api/templates/${id}`);
      return data;
    },
    enabled: !!id,
  });
};

export const useDeployTemplate = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      templateId,
      request,
    }: {
      templateId: string;
      request: DeployTemplateRequest;
    }) => {
      const { data } = await api.post<DeployTemplateResponse>(
        `/api/templates/${templateId}/deploy`,
        request
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["pipelines"] });
      queryClient.invalidateQueries({ queryKey: ["sources"] });
      queryClient.invalidateQueries({ queryKey: ["destinations"] });
      toast.success("Template deployed successfully!");
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to deploy template"
      );
    },
  });
};
