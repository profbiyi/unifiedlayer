"use client";

import { useState } from "react";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SourceWizardData } from "@/app/(dashboard)/sources/new/page";
import { Table, Info, RefreshCw, TrendingUp } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface SyncConfigStepProps {
  data: SourceWizardData;
  onUpdate: (updates: Partial<SourceWizardData>) => void;
}

type SyncMode = "full_refresh" | "incremental";

export default function SyncConfigStep({
  data,
  onUpdate,
}: SyncConfigStepProps) {
  const selectedTables = Array.from(data.selectedTables);
  const [bulkSyncMode, setBulkSyncMode] = useState<SyncMode>("full_refresh");

  const updateTableConfig = (
    tableId: string,
    config: {
      sync_mode: SyncMode;
      cursor_field?: string;
      primary_key?: string[];
    }
  ) => {
    onUpdate({
      tableConfigs: {
        ...data.tableConfigs,
        [tableId]: config,
      },
    });
  };

  const getTableConfig = (tableId: string) => {
    return (
      data.tableConfigs[tableId] || {
        sync_mode: "full_refresh",
      }
    );
  };

  const applyBulkSyncMode = () => {
    const newConfigs = { ...data.tableConfigs };
    selectedTables.forEach((tableId) => {
      newConfigs[tableId] = {
        ...newConfigs[tableId],
        sync_mode: bulkSyncMode,
      };
    });
    onUpdate({ tableConfigs: newConfigs });
  };

  const getTableParts = (tableId: string) => {
    const [schema, table] = tableId.split(".");
    return { schema, table };
  };

  const fullRefreshCount = selectedTables.filter(
    (tableId) => getTableConfig(tableId).sync_mode === "full_refresh"
  ).length;

  const incrementalCount = selectedTables.filter(
    (tableId) => getTableConfig(tableId).sync_mode === "incremental"
  ).length;

  return (
    <div className="space-y-6">
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Configure how each table should be synchronized. You can change these
          settings later.
        </AlertDescription>
      </Alert>

      {/* Bulk Actions */}
      <div className="rounded-lg border bg-muted/50 p-4">
        <div className="flex items-center justify-between">
          <div className="space-y-1">
            <Label className="text-base font-semibold">
              Apply to All Tables
            </Label>
            <p className="text-sm text-muted-foreground">
              Set the same sync mode for all selected tables
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Select
              value={bulkSyncMode}
              onValueChange={(value) => setBulkSyncMode(value as SyncMode)}
            >
              <SelectTrigger className="w-[200px]">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="full_refresh">
                  <div className="flex items-center gap-2">
                    <RefreshCw className="h-4 w-4" />
                    Full Refresh
                  </div>
                </SelectItem>
                <SelectItem value="incremental">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" />
                    Incremental
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            <button
              onClick={applyBulkSyncMode}
              className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90"
            >
              Apply
            </button>
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="flex gap-4">
        <div className="flex-1 rounded-lg border p-4">
          <div className="flex items-center gap-2">
            <RefreshCw className="h-5 w-5 text-blue-600" />
            <div>
              <p className="text-2xl font-bold">{fullRefreshCount}</p>
              <p className="text-sm text-muted-foreground">Full Refresh</p>
            </div>
          </div>
        </div>
        <div className="flex-1 rounded-lg border p-4">
          <div className="flex items-center gap-2">
            <TrendingUp className="h-5 w-5 text-green-600" />
            <div>
              <p className="text-2xl font-bold">{incrementalCount}</p>
              <p className="text-sm text-muted-foreground">Incremental</p>
            </div>
          </div>
        </div>
      </div>

      {/* Per-Table Configuration */}
      <div className="space-y-2">
        <Label className="text-base font-semibold">
          Per-Table Configuration
        </Label>
        <div className="max-h-[400px] space-y-2 overflow-y-auto rounded-lg border p-4">
          {selectedTables.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No tables selected
            </div>
          ) : (
            selectedTables.map((tableId) => {
              const { schema, table } = getTableParts(tableId);
              const config = getTableConfig(tableId);

              return (
                <div
                  key={tableId}
                  className="flex items-center justify-between rounded-md border p-3 hover:bg-muted/50"
                >
                  <div className="flex items-center gap-3">
                    <Table className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{table}</p>
                      <p className="text-xs text-muted-foreground">{schema}</p>
                    </div>
                  </div>

                  <div className="flex items-center gap-3">
                    <Select
                      value={config.sync_mode}
                      onValueChange={(value) =>
                        updateTableConfig(tableId, {
                          ...config,
                          sync_mode: value as SyncMode,
                        })
                      }
                    >
                      <SelectTrigger className="w-[180px]">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="full_refresh">
                          <div className="flex items-center gap-2">
                            <RefreshCw className="h-4 w-4" />
                            <div>
                              <p className="font-medium">Full Refresh</p>
                              <p className="text-xs text-muted-foreground">
                                Replace all data
                              </p>
                            </div>
                          </div>
                        </SelectItem>
                        <SelectItem value="incremental">
                          <div className="flex items-center gap-2">
                            <TrendingUp className="h-4 w-4" />
                            <div>
                              <p className="font-medium">Incremental</p>
                              <p className="text-xs text-muted-foreground">
                                Sync new/updated rows
                              </p>
                            </div>
                          </div>
                        </SelectItem>
                      </SelectContent>
                    </Select>

                    <Badge
                      variant={
                        config.sync_mode === "incremental"
                          ? "default"
                          : "secondary"
                      }
                      className={
                        config.sync_mode === "incremental"
                          ? "bg-green-600 hover:bg-green-700"
                          : ""
                      }
                    >
                      {config.sync_mode === "full_refresh"
                        ? "Full"
                        : "Incremental"}
                    </Badge>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Sync Mode Explanations */}
      <div className="space-y-3 rounded-lg border bg-card p-4">
        <h4 className="font-semibold">Sync Mode Explanations</h4>
        <div className="space-y-3 text-sm">
          <div className="flex gap-3">
            <RefreshCw className="h-5 w-5 shrink-0 text-blue-600" />
            <div>
              <p className="font-medium">Full Refresh</p>
              <p className="text-muted-foreground">
                Replaces all data in the destination table on each sync. Best for
                smaller tables or when you need a complete snapshot.
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <TrendingUp className="h-5 w-5 shrink-0 text-green-600" />
            <div>
              <p className="font-medium">Incremental</p>
              <p className="text-muted-foreground">
                Only syncs new or updated rows since the last sync. More efficient
                for large tables with a timestamp or ID cursor field.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
