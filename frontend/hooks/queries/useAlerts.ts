"use client";

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import toast from "react-hot-toast";

// Types
export interface SlackChannelConfig {
  enabled: boolean;
  webhook_url: string | null;
}

export interface EmailChannelConfig {
  enabled: boolean;
  recipients: string[];
}

export interface NotificationChannelsConfig {
  slack: SlackChannelConfig;
  email: EmailChannelConfig;
}

export interface NotificationChannelsResponse {
  id: string;
  organization_id: string | null;
  slack: SlackChannelConfig;
  email: EmailChannelConfig;
  updated_at: string;
}

export interface AlertRule {
  id: string;
  name: string;
  description: string;
  severity: "critical" | "warning" | "info";
  enabled: boolean;
  threshold: number | null;
  threshold_unit: string | null;
}

export interface AlertRulesResponse {
  rules: AlertRule[];
  updated_at: string;
}

export interface UpdateAlertRuleRequest {
  enabled?: boolean;
  threshold?: number;
}

export interface AlertHistoryItem {
  id: string;
  rule_id: string;
  rule_name: string;
  severity: "critical" | "warning" | "info";
  status: "triggered" | "acknowledged" | "resolved";
  message: string;
  pipeline_id: string | null;
  pipeline_name: string | null;
  triggered_at: string;
  acknowledged_at: string | null;
  resolved_at: string | null;
}

export interface PaginatedAlertHistory {
  items: AlertHistoryItem[];
  total: number;
  skip: number;
  limit: number;
}

export interface AlertHistoryFilters {
  severity?: string;
  status?: string;
  skip?: number;
  limit?: number;
}

// Notification Channels Hooks
export const useNotificationChannels = () => {
  return useQuery({
    queryKey: ["notification-channels"],
    queryFn: async () => {
      const { data } = await api.get<NotificationChannelsResponse>(
        "/alerts/settings/notifications"
      );
      return data;
    },
  });
};

export const useUpdateNotificationChannels = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (config: NotificationChannelsConfig) => {
      const { data } = await api.put<NotificationChannelsResponse>(
        "/alerts/settings/notifications",
        config
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notification-channels"] });
      toast.success("Notification settings saved");
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to save notification settings"
      );
    },
  });
};

export const useTestSlackWebhook = () => {
  return useMutation({
    mutationFn: async (webhookUrl: string) => {
      const { data } = await api.post<{ success: boolean; message: string }>(
        "/alerts/settings/notifications/test-slack",
        { webhook_url: webhookUrl }
      );
      return data;
    },
    onSuccess: (data) => {
      if (data.success) {
        toast.success(data.message);
      } else {
        toast.error(data.message);
      }
    },
    onError: (error: any) => {
      toast.error(
        error.response?.data?.detail || "Failed to test Slack webhook"
      );
    },
  });
};

// Alert Rules Hooks
export const useAlertRules = () => {
  return useQuery({
    queryKey: ["alert-rules"],
    queryFn: async () => {
      const { data } = await api.get<AlertRulesResponse>("/alerts/rules");
      return data;
    },
  });
};

export const useUpdateAlertRule = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      ruleId,
      update,
    }: {
      ruleId: string;
      update: UpdateAlertRuleRequest;
    }) => {
      const { data } = await api.patch<AlertRule>(
        `/alerts/rules/${ruleId}`,
        update
      );
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert-rules"] });
      toast.success("Alert rule updated");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to update alert rule");
    },
  });
};

// Alert History Hooks
export const useAlertHistory = (filters: AlertHistoryFilters = {}) => {
  return useQuery({
    queryKey: ["alert-history", filters],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (filters.severity) params.append("severity", filters.severity);
      if (filters.status) params.append("alert_status", filters.status);
      if (filters.skip !== undefined)
        params.append("skip", filters.skip.toString());
      if (filters.limit !== undefined)
        params.append("limit", filters.limit.toString());

      const { data } = await api.get<PaginatedAlertHistory>(
        `/alerts/history?${params.toString()}`
      );
      return data;
    },
    refetchInterval: 30000, // Refresh every 30 seconds
  });
};

export const useAcknowledgeAlert = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (alertId: string) => {
      const { data } = await api.patch(`/alerts/history/${alertId}/acknowledge`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert-history"] });
      toast.success("Alert acknowledged");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to acknowledge alert");
    },
  });
};

export const useResolveAlert = () => {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (alertId: string) => {
      const { data } = await api.patch(`/alerts/history/${alertId}/resolve`);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["alert-history"] });
      toast.success("Alert resolved");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to resolve alert");
    },
  });
};
