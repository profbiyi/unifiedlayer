"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { useAlertRules, useUpdateAlertRule } from "@/hooks/queries/useAlerts";
import {
  AlertTriangle,
  AlertCircle,
  Info,
  Loader2,
  Clock,
  XCircle,
  Database,
  Gauge,
  Calendar,
  BarChart3,
} from "lucide-react";

const severityConfig = {
  critical: {
    label: "Critical",
    variant: "destructive" as const,
    icon: XCircle,
  },
  warning: {
    label: "Warning",
    variant: "warning" as const,
    icon: AlertTriangle,
  },
  info: {
    label: "Info",
    variant: "info" as const,
    icon: Info,
  },
};

const ruleIcons: Record<string, typeof AlertCircle> = {
  pipeline_failure: XCircle,
  slow_execution: Clock,
  data_quality_failure: Database,
  high_error_rate: Gauge,
  source_connection_failed: AlertCircle,
  destination_connection_failed: AlertCircle,
  schedule_missed: Calendar,
  low_row_count: BarChart3,
};

export function AlertRules() {
  const { data: rulesData, isLoading } = useAlertRules();
  const updateMutation = useUpdateAlertRule();
  const [editingThreshold, setEditingThreshold] = useState<string | null>(null);

  const handleToggleRule = (ruleId: string, enabled: boolean) => {
    updateMutation.mutate({ ruleId, update: { enabled } });
  };

  const handleUpdateThreshold = (ruleId: string, threshold: number) => {
    updateMutation.mutate({ ruleId, update: { threshold } });
    setEditingThreshold(null);
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  const rules = rulesData?.rules || [];

  return (
    <Card>
      <CardHeader>
        <CardTitle>Alert Rules</CardTitle>
        <CardDescription>
          Configure which events trigger alerts and their thresholds
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {rules.map((rule, index) => {
          const severity = severityConfig[rule.severity];
          const SeverityIcon = severity.icon;
          const RuleIcon = ruleIcons[rule.id] || AlertCircle;

          return (
            <div key={rule.id}>
              {index > 0 && <Separator className="mb-4" />}
              <div className="flex items-start justify-between gap-4">
                <div className="flex items-start gap-3 flex-1">
                  <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-muted">
                    <RuleIcon className="h-5 w-5 text-muted-foreground" />
                  </div>
                  <div className="flex-1 space-y-1">
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium">{rule.name}</h3>
                      <Badge variant={severity.variant} className="text-xs">
                        <SeverityIcon className="mr-1 h-3 w-3" />
                        {severity.label}
                      </Badge>
                    </div>
                    <p className="text-sm text-muted-foreground">
                      {rule.description}
                    </p>

                    {/* Threshold input */}
                    {rule.threshold !== null && rule.enabled && (
                      <div className="flex items-center gap-2 mt-2">
                        <Label className="text-sm text-muted-foreground">
                          Threshold:
                        </Label>
                        {editingThreshold === rule.id ? (
                          <Input
                            type="number"
                            defaultValue={rule.threshold}
                            className="w-24 h-8"
                            autoFocus
                            onBlur={(e) => {
                              const value = parseFloat(e.target.value);
                              if (!isNaN(value) && value > 0) {
                                handleUpdateThreshold(rule.id, value);
                              } else {
                                setEditingThreshold(null);
                              }
                            }}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") {
                                const value = parseFloat(
                                  (e.target as HTMLInputElement).value
                                );
                                if (!isNaN(value) && value > 0) {
                                  handleUpdateThreshold(rule.id, value);
                                } else {
                                  setEditingThreshold(null);
                                }
                              }
                              if (e.key === "Escape") {
                                setEditingThreshold(null);
                              }
                            }}
                          />
                        ) : (
                          <button
                            onClick={() => setEditingThreshold(rule.id)}
                            className="text-sm font-medium text-primary hover:underline"
                          >
                            {rule.threshold} {rule.threshold_unit}
                          </button>
                        )}
                      </div>
                    )}
                  </div>
                </div>

                <Switch
                  checked={rule.enabled}
                  onCheckedChange={(enabled) =>
                    handleToggleRule(rule.id, enabled)
                  }
                  disabled={updateMutation.isPending}
                />
              </div>
            </div>
          );
        })}

        {rules.length === 0 && (
          <div className="text-center py-6 text-muted-foreground">
            No alert rules configured
          </div>
        )}
      </CardContent>
    </Card>
  );
}
