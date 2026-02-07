"use client";

import { useState } from "react";
import { usePipelineRuns } from "@/hooks/queries/usePipelines";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Progress } from "@/components/ui/progress";
import { TableRowSkeleton } from "@/components/skeletons/TableRowSkeleton";
import { format, formatDistanceToNow } from "date-fns";
import { Activity, Clock, CheckCircle, XCircle, Loader2, Database, AlertCircle, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { PipelineRun } from "@/types/pipeline";

const getStatusIcon = (status: string) => {
  switch (status.toLowerCase()) {
    case "completed":
      return <CheckCircle className="h-5 w-5 text-success" />;
    case "failed":
      return <XCircle className="h-5 w-5 text-error" />;
    case "running":
      return <Loader2 className="h-5 w-5 text-running animate-spin" />;
    case "pending":
      return <Clock className="h-5 w-5 text-warning" />;
    default:
      return <Activity className="h-5 w-5 text-muted-foreground" />;
  }
};

const getStatusLabel = (status: string) => {
  switch (status.toLowerCase()) {
    case "completed":
      return "Completed Successfully";
    case "failed":
      return "Failed";
    case "running":
      return "Running";
    case "pending":
      return "Pending";
    default:
      return status;
  }
};

const getStatusVariant = (status: string) => {
  switch (status) {
    case "completed":
      return "success";
    case "failed":
      return "error";
    case "running":
      return "running";
    case "pending":
      return "warning";
    default:
      return "default";
  }
};

export default function RunsPage() {
  const { data: runs, isLoading, error } = usePipelineRuns();
  const [selectedRun, setSelectedRun] = useState<PipelineRun | null>(null);

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Pipeline Runs</h1>
          <p className="text-muted-foreground">
            Monitor all pipeline execution history
          </p>
        </div>
        <TableRowSkeleton count={6} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-destructive">Error loading runs</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Pipeline Runs</h1>
        <p className="text-muted-foreground">
          Monitor all pipeline execution history
        </p>
      </div>

      {runs && runs.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No runs yet</CardTitle>
            <CardDescription>
              Pipeline runs will appear here once you trigger a pipeline
            </CardDescription>
          </CardHeader>
        </Card>
      ) : (
        <div className="space-y-4">
          {runs?.map((run) => (
            <Card
              key={run.id}
              className="cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => setSelectedRun(run)}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    {getStatusIcon(run.status)}
                    <div>
                      <CardTitle className="text-lg">
                        {run.pipeline_name || `Pipeline Run #${run.id}`}
                      </CardTitle>
                      <CardDescription>
                        {run.started_at
                          ? format(new Date(run.started_at), "PPpp")
                          : "Not started"}
                      </CardDescription>
                    </div>
                  </div>
                  <Badge variant={getStatusVariant(run.status) as any}>
                    {getStatusLabel(run.status)}
                  </Badge>
                </div>
              </CardHeader>
              <CardContent>
                {/* Progress bar for running pipelines */}
                {run.status === "running" && (
                  <div className="mb-4 space-y-2">
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-muted-foreground flex items-center gap-2">
                        <Zap className="h-4 w-4 text-running animate-pulse" />
                        {run.run_metadata?.current_step || "Processing..."}
                      </span>
                      <span className="font-medium">
                        {run.run_metadata?.progress_percent || 0}%
                      </span>
                    </div>
                    <Progress
                      value={run.run_metadata?.progress_percent || 0}
                      className="h-2"
                      animated={true}
                      indeterminate={!run.run_metadata?.progress_percent || run.run_metadata?.progress_percent === 0}
                    />
                  </div>
                )}

                <div className="grid gap-4 md:grid-cols-3">
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">
                      Started
                    </p>
                    <p className="text-sm">
                      {run.started_at
                        ? formatDistanceToNow(new Date(run.started_at), {
                            addSuffix: true,
                          })
                        : "Not started"}
                    </p>
                  </div>
                  {run.duration_seconds !== undefined && run.duration_seconds !== null && (
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">
                        Duration
                      </p>
                      <p className="text-sm">
                        {run.duration_seconds < 60
                          ? `${Math.round(run.duration_seconds)}s`
                          : `${Math.floor(run.duration_seconds / 60)}m ${Math.round(run.duration_seconds % 60)}s`
                        }
                      </p>
                    </div>
                  )}
                  {run.rows_written !== undefined && run.rows_written !== null && (
                    <div>
                      <p className="text-sm font-medium text-muted-foreground">
                        Rows Written
                      </p>
                      <p className="text-sm">
                        {run.rows_written.toLocaleString()}
                      </p>
                    </div>
                  )}
                </div>
                {run.error_message && (
                  <div className="mt-4 rounded-md bg-destructive/10 p-3">
                    <p className="text-sm text-destructive">
                      {run.error_message}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Run Details Dialog */}
      <Dialog open={!!selectedRun} onOpenChange={(open) => !open && setSelectedRun(null)}>
        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
          {selectedRun && (
            <>
              <DialogHeader>
                <div className="flex items-center gap-3">
                  {getStatusIcon(selectedRun.status)}
                  <div>
                    <DialogTitle>
                      {selectedRun.pipeline_name || `Pipeline Run #${selectedRun.id}`}
                    </DialogTitle>
                    <DialogDescription>
                      Run ID: {selectedRun.id} • {selectedRun.started_at && format(new Date(selectedRun.started_at), "PPpp")}
                    </DialogDescription>
                  </div>
                </div>
              </DialogHeader>

              <div className="space-y-6 mt-4">
                {/* Status */}
                <div>
                  <h3 className="text-sm font-medium mb-2 flex items-center gap-2">
                    <Activity className="h-4 w-4" />
                    Status
                  </h3>
                  <Badge variant={getStatusVariant(selectedRun.status) as any} className="text-sm">
                    {getStatusLabel(selectedRun.status)}
                  </Badge>
                </div>

                {/* Progress for running pipelines */}
                {selectedRun.status === "running" && (
                  <div>
                    <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                      <Zap className="h-4 w-4 text-running animate-pulse" />
                      Progress
                    </h3>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between">
                        <span className="text-sm text-muted-foreground flex items-center gap-2">
                          <Loader2 className="h-3 w-3 animate-spin" />
                          {selectedRun.run_metadata?.current_step || "Processing..."}
                        </span>
                        <span className="text-sm font-medium">
                          {selectedRun.run_metadata?.progress_percent || 0}%
                        </span>
                      </div>
                      <Progress
                        value={selectedRun.run_metadata?.progress_percent || 0}
                        className="h-3"
                        animated={true}
                        indeterminate={!selectedRun.run_metadata?.progress_percent || selectedRun.run_metadata?.progress_percent === 0}
                      />
                      {selectedRun.run_metadata?.source_name && (
                        <div className="text-xs text-muted-foreground">
                          Source: {selectedRun.run_metadata.source_name}
                          {selectedRun.run_metadata?.destination_name && (
                            <> → Destination: {selectedRun.run_metadata.destination_name}</>
                          )}
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Timing */}
                <div>
                  <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                    <Clock className="h-4 w-4" />
                    Execution Timeline
                  </h3>
                  <div className="grid gap-3">
                    {selectedRun.started_at && (
                      <div className="flex justify-between items-center p-3 bg-muted/50 rounded-lg">
                        <span className="text-sm text-muted-foreground">Started</span>
                        <span className="text-sm font-medium">
                          {format(new Date(selectedRun.started_at), "PPpp")}
                        </span>
                      </div>
                    )}
                    {selectedRun.completed_at && (
                      <div className="flex justify-between items-center p-3 bg-muted/50 rounded-lg">
                        <span className="text-sm text-muted-foreground">Completed</span>
                        <span className="text-sm font-medium">
                          {format(new Date(selectedRun.completed_at), "PPpp")}
                        </span>
                      </div>
                    )}
                    {selectedRun.duration_seconds !== undefined && selectedRun.duration_seconds !== null && (
                      <div className="flex justify-between items-center p-3 bg-muted/50 rounded-lg">
                        <span className="text-sm text-muted-foreground">Duration</span>
                        <span className="text-sm font-medium">
                          {selectedRun.duration_seconds < 60
                            ? `${Math.round(selectedRun.duration_seconds)} seconds`
                            : selectedRun.duration_seconds < 3600
                            ? `${Math.floor(selectedRun.duration_seconds / 60)} minutes ${Math.round(selectedRun.duration_seconds % 60)} seconds`
                            : `${Math.floor(selectedRun.duration_seconds / 3600)} hours ${Math.floor((selectedRun.duration_seconds % 3600) / 60)} minutes`
                          }
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Data Metrics */}
                {(selectedRun.rows_written !== undefined || selectedRun.bytes_written !== undefined) && (
                  <div>
                    <h3 className="text-sm font-medium mb-3 flex items-center gap-2">
                      <Database className="h-4 w-4" />
                      Data Processed
                    </h3>
                    <div className="grid gap-3">
                      {selectedRun.rows_written !== undefined && selectedRun.rows_written !== null && (
                        <div className="flex justify-between items-center p-3 bg-muted/50 rounded-lg">
                          <span className="text-sm text-muted-foreground">Rows Written</span>
                          <span className="text-sm font-medium">{selectedRun.rows_written.toLocaleString()}</span>
                        </div>
                      )}
                      {selectedRun.bytes_written !== undefined && selectedRun.bytes_written !== null && (
                        <div className="flex justify-between items-center p-3 bg-muted/50 rounded-lg">
                          <span className="text-sm text-muted-foreground">Bytes Written</span>
                          <span className="text-sm font-medium">
                            {(selectedRun.bytes_written / 1024 / 1024).toFixed(2)} MB
                          </span>
                        </div>
                      )}
                    </div>
                  </div>
                )}

                {/* Error Details */}
                {selectedRun.error_message && (
                  <div>
                    <h3 className="text-sm font-medium mb-3 flex items-center gap-2 text-destructive">
                      <AlertCircle className="h-4 w-4" />
                      Error Details
                    </h3>
                    <div className="space-y-3">
                      <div className="p-3 bg-destructive/10 rounded-lg">
                        <p className="text-sm text-destructive font-medium mb-1">Error Message</p>
                        <p className="text-sm text-destructive/90">{selectedRun.error_message}</p>
                      </div>
                      {selectedRun.error_traceback && (
                        <div className="p-3 bg-muted rounded-lg">
                          <p className="text-sm font-medium mb-2">Stack Trace</p>
                          <pre className="text-xs overflow-x-auto whitespace-pre-wrap">
                            {selectedRun.error_traceback}
                          </pre>
                        </div>
                      )}
                    </div>
                  </div>
                )}

              </div>
            </>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
