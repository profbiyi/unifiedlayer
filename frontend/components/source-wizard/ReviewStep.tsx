"use client";

import { Badge } from "@/components/ui/badge";
import { SourceWizardData } from "@/app/(dashboard)/sources/new/page";
import {
  CheckCircle2,
  Database,
  Table,
  Settings,
  RefreshCw,
  TrendingUp,
} from "lucide-react";

interface ReviewStepProps {
  data: SourceWizardData;
}

export default function ReviewStep({ data }: ReviewStepProps) {
  const selectedTables = Array.from(data.selectedTables);

  const getTableParts = (tableId: string) => {
    const [schema, table] = tableId.split(".");
    return { schema, table };
  };

  const fullRefreshCount = selectedTables.filter(
    (tableId) =>
      (data.tableConfigs[tableId]?.sync_mode || "full_refresh") ===
      "full_refresh"
  ).length;

  const incrementalCount = selectedTables.filter(
    (tableId) => data.tableConfigs[tableId]?.sync_mode === "incremental"
  ).length;

  return (
    <div className="space-y-6">
      {/* Success Header */}
      <div className="flex items-center gap-3 rounded-lg border border-green-500 bg-green-50 p-4 dark:bg-green-950">
        <CheckCircle2 className="h-6 w-6 text-green-600" />
        <div>
          <h3 className="font-semibold">Ready to Create Source</h3>
          <p className="text-sm text-muted-foreground">
            Review your configuration before creating the data source
          </p>
        </div>
      </div>

      {/* Basic Information */}
      <div className="rounded-lg border">
        <div className="border-b bg-muted/50 p-4">
          <h4 className="flex items-center gap-2 font-semibold">
            <Database className="h-5 w-5" />
            Basic Information
          </h4>
        </div>
        <div className="p-4">
          <dl className="space-y-3">
            <div className="flex justify-between">
              <dt className="text-sm font-medium text-muted-foreground">
                Source Name:
              </dt>
              <dd className="text-sm font-semibold">{data.name}</dd>
            </div>
            {data.description && (
              <div className="flex justify-between">
                <dt className="text-sm font-medium text-muted-foreground">
                  Description:
                </dt>
                <dd className="text-sm">{data.description}</dd>
              </div>
            )}
            <div className="flex justify-between">
              <dt className="text-sm font-medium text-muted-foreground">
                Source Type:
              </dt>
              <dd>
                <Badge variant="secondary" className="capitalize">
                  {data.source_type.replace("_", " ")}
                </Badge>
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Connection Details */}
      <div className="rounded-lg border">
        <div className="border-b bg-muted/50 p-4">
          <h4 className="flex items-center gap-2 font-semibold">
            <Settings className="h-5 w-5" />
            Connection Details
          </h4>
        </div>
        <div className="p-4">
          <dl className="space-y-3">
            {data.source_type === "postgresql" ||
            data.source_type === "mysql" ? (
              <>
                <div className="flex justify-between">
                  <dt className="text-sm font-medium text-muted-foreground">
                    Host:
                  </dt>
                  <dd className="font-mono text-sm">{data.config.host}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm font-medium text-muted-foreground">
                    Port:
                  </dt>
                  <dd className="font-mono text-sm">{data.config.port}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm font-medium text-muted-foreground">
                    Database:
                  </dt>
                  <dd className="font-mono text-sm">{data.config.database}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm font-medium text-muted-foreground">
                    Username:
                  </dt>
                  <dd className="font-mono text-sm">{data.config.username}</dd>
                </div>
              </>
            ) : data.source_type === "mongodb" ? (
              <div className="flex justify-between">
                <dt className="text-sm font-medium text-muted-foreground">
                  Database:
                </dt>
                <dd className="font-mono text-sm">{data.config.database}</dd>
              </div>
            ) : data.source_type === "rest_api" ? (
              <>
                <div className="flex justify-between">
                  <dt className="text-sm font-medium text-muted-foreground">
                    Base URL:
                  </dt>
                  <dd className="font-mono text-sm">{data.config.base_url}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm font-medium text-muted-foreground">
                    Auth Type:
                  </dt>
                  <dd>
                    <Badge variant="outline" className="capitalize">
                      {data.config.auth_type || "none"}
                    </Badge>
                  </dd>
                </div>
              </>
            ) : data.source_type === "csv" ? (
              <>
                <div className="flex justify-between">
                  <dt className="text-sm font-medium text-muted-foreground">
                    File Path:
                  </dt>
                  <dd className="font-mono text-sm">{data.config.file_path}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-sm font-medium text-muted-foreground">
                    Delimiter:
                  </dt>
                  <dd className="font-mono text-sm">
                    {data.config.delimiter || ","}
                  </dd>
                </div>
              </>
            ) : data.source_type === "local" ? (
              <div className="flex justify-between">
                <dt className="text-sm font-medium text-muted-foreground">
                  Directory:
                </dt>
                <dd className="font-mono text-sm">
                  {data.config.directory_path}
                </dd>
              </div>
            ) : null}

            <div className="flex justify-between border-t pt-3">
              <dt className="text-sm font-medium text-muted-foreground">
                Connection Status:
              </dt>
              <dd>
                <Badge
                  variant="default"
                  className="bg-green-600 hover:bg-green-700"
                >
                  <CheckCircle2 className="mr-1 h-3 w-3" />
                  Tested Successfully
                </Badge>
              </dd>
            </div>
          </dl>
        </div>
      </div>

      {/* Tables Selection */}
      <div className="rounded-lg border">
        <div className="border-b bg-muted/50 p-4">
          <div className="flex items-center justify-between">
            <h4 className="flex items-center gap-2 font-semibold">
              <Table className="h-5 w-5" />
              Selected Tables
            </h4>
            <Badge variant="secondary">{selectedTables.length} tables</Badge>
          </div>
        </div>
        <div className="p-4">
          <div className="mb-4 flex gap-4">
            <div className="flex items-center gap-2">
              <RefreshCw className="h-4 w-4 text-blue-600" />
              <span className="text-sm">
                <span className="font-semibold">{fullRefreshCount}</span> Full
                Refresh
              </span>
            </div>
            <div className="flex items-center gap-2">
              <TrendingUp className="h-4 w-4 text-green-600" />
              <span className="text-sm">
                <span className="font-semibold">{incrementalCount}</span>{" "}
                Incremental
              </span>
            </div>
          </div>

          <div className="max-h-[300px] space-y-2 overflow-y-auto">
            {selectedTables.map((tableId) => {
              const { schema, table } = getTableParts(tableId);
              const config =
                data.tableConfigs[tableId] || { sync_mode: "full_refresh" };

              return (
                <div
                  key={tableId}
                  className="flex items-center justify-between rounded-md border p-3"
                >
                  <div className="flex items-center gap-3">
                    <Table className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{table}</p>
                      <p className="text-xs text-muted-foreground">{schema}</p>
                    </div>
                  </div>
                  <Badge
                    variant={
                      config.sync_mode === "incremental" ? "default" : "secondary"
                    }
                    className={
                      config.sync_mode === "incremental"
                        ? "bg-green-600 hover:bg-green-700"
                        : ""
                    }
                  >
                    {config.sync_mode === "incremental" ? (
                      <>
                        <TrendingUp className="mr-1 h-3 w-3" />
                        Incremental
                      </>
                    ) : (
                      <>
                        <RefreshCw className="mr-1 h-3 w-3" />
                        Full Refresh
                      </>
                    )}
                  </Badge>
                </div>
              );
            })}
          </div>
        </div>
      </div>

      {/* Summary Stats */}
      <div className="rounded-lg border bg-muted/50 p-4">
        <h4 className="mb-3 font-semibold">Summary</h4>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <p className="text-2xl font-bold text-primary">
              {selectedTables.length}
            </p>
            <p className="text-xs text-muted-foreground">Tables Selected</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-blue-600">
              {fullRefreshCount}
            </p>
            <p className="text-xs text-muted-foreground">Full Refresh</p>
          </div>
          <div>
            <p className="text-2xl font-bold text-green-600">
              {incrementalCount}
            </p>
            <p className="text-xs text-muted-foreground">Incremental</p>
          </div>
        </div>
      </div>
    </div>
  );
}
