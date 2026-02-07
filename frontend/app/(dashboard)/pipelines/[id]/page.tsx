"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { usePipeline, useTriggerPipeline, usePipelineRuns } from "@/hooks/queries/usePipelines";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import PipelineStatusBadge from "@/components/pipeline/pipeline-status-badge";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { ArrowLeft, Play, Settings, Loader2, Activity, Clock, CheckCircle, XCircle, Database, AlertCircle } from "lucide-react";
import { format, formatDistanceToNow } from "date-fns";
import { PipelineRun } from "@/types/pipeline";
import Link from "next/link";

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
  switch (status.toLowerCase()) {
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

export default function PipelineDetailPage() {
  const params = useParams();
  const router = useRouter();
  const pipelineId = params.id as string;

  const { data: pipeline, isLoading: pipelineLoading } = usePipeline(pipelineId);
  const { data: runs, isLoading: runsLoading } = usePipelineRuns(pipelineId);
  const triggerPipeline = useTriggerPipeline();
  const [selectedRun, setSelectedRun] = useState<PipelineRun | null>(null);

  const handleTrigger = () => {
    triggerPipeline.mutate(pipelineId);
  };

  if (pipelineLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!pipeline) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <p className="text-destructive">Pipeline not found</p>
        <Link href="/pipelines">
          <Button variant="outline">Back to Pipelines</Button>
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb
        items={[
          { label: "Pipelines", href: "/pipelines" },
          { label: pipeline.name },
        ]}
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/pipelines">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">{pipeline.name}</h1>
              <PipelineStatusBadge isActive={pipeline.is_active} />
            </div>
            {pipeline.description && (
              <p className="text-muted-foreground mt-1">{pipeline.description}</p>
            )}
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            onClick={handleTrigger}
            disabled={!pipeline.is_active || triggerPipeline.isPending}
          >
            <Play className="mr-2 h-4 w-4" />
            {triggerPipeline.isPending ? "Triggering..." : "Run Pipeline"}
          </Button>
          <Link href={`/pipelines/${pipelineId}/settings`}>
            <Button variant="outline">
              <Settings className="mr-2 h-4 w-4" />
              Settings
            </Button>
          </Link>
        </div>
      </div>

      {/* Pipeline Info */}
      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Source</CardTitle>
            <CardDescription>Data source configuration</CardDescription>
          </CardHeader>
          <CardContent>
            {pipeline.source ? (
              <div className="space-y-2">
                <p className="font-medium">{pipeline.source.name}</p>
                <Badge variant="outline">{pipeline.source.type}</Badge>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Source ID: {pipeline.source_id}
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Destination</CardTitle>
            <CardDescription>Data destination configuration</CardDescription>
          </CardHeader>
          <CardContent>
            {pipeline.destination ? (
              <div className="space-y-2">
                <p className="font-medium">{pipeline.destination.name}</p>
                <Badge variant="outline">{pipeline.destination.type}</Badge>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Destination ID: {pipeline.destination_id}
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Schedule */}
      <Card>
        <CardHeader>
          <CardTitle>Schedule</CardTitle>
          <CardDescription>Pipeline execution schedule</CardDescription>
        </CardHeader>
        <CardContent>
          {pipeline.schedule ? (
            <div className="space-y-1">
              <p className="font-mono text-sm">{pipeline.schedule}</p>
              <p className="text-xs text-muted-foreground">Cron expression</p>
            </div>
          ) : (
            <p className="text-sm text-muted-foreground">
              Manual execution only (no schedule configured)
            </p>
          )}
        </CardContent>
      </Card>

      {/* Recent Runs */}
      <Card>
        <CardHeader>
          <CardTitle>Recent Runs</CardTitle>
          <CardDescription>Pipeline execution history</CardDescription>
        </CardHeader>
        <CardContent>
          {runsLoading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          ) : runs && runs.length > 0 ? (
            <div className="space-y-3">
              {runs.map((run) => (
                <div
                  key={run.id}
                  className="flex items-center justify-between p-3 rounded-lg border hover:bg-muted/50 transition-colors cursor-pointer"
                  onClick={() => setSelectedRun(run)}
                >
                  <div className="flex items-center gap-3">
                    {getStatusIcon(run.status)}
                    <div>
                      <p className="font-medium">Run #{run.id}</p>
                      <p className="text-xs text-muted-foreground">
                        {run.started_at
                          ? `${format(new Date(run.started_at), "PPp")} (${formatDistanceToNow(new Date(run.started_at), {
                              addSuffix: true,
                            })})`
                          : "Not started"}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    {run.duration_seconds !== undefined && run.duration_seconds !== null && (
                      <p className="text-sm text-muted-foreground">
                        {run.duration_seconds < 60
                          ? `${Math.round(run.duration_seconds)}s`
                          : `${Math.floor(run.duration_seconds / 60)}m ${Math.round(run.duration_seconds % 60)}s`
                        }
                      </p>
                    )}
                    {(run.rows_written !== null && run.rows_written !== undefined) && (
                      <p className="text-sm text-muted-foreground">
                        {run.rows_written.toLocaleString()} rows
                      </p>
                    )}
                    <Badge variant={getStatusVariant(run.status) as any}>
                      {getStatusLabel(run.status)}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-sm text-muted-foreground">
                No runs yet. Click "Run Pipeline" to execute this pipeline.
              </p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Metadata */}
      <Card>
        <CardHeader>
          <CardTitle>Metadata</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground mb-1">Created</p>
              <p className="font-medium">{format(new Date(pipeline.created_at), "PPP")}</p>
              <p className="text-xs text-muted-foreground">
                {formatDistanceToNow(new Date(pipeline.created_at), {
                  addSuffix: true,
                })}
              </p>
            </div>
            <div>
              <p className="text-muted-foreground mb-1">Last Updated</p>
              <p className="font-medium">{format(new Date(pipeline.updated_at), "PPP")}</p>
              <p className="text-xs text-muted-foreground">
                {formatDistanceToNow(new Date(pipeline.updated_at), {
                  addSuffix: true,
                })}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

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
                      Run #{selectedRun.id}
                    </DialogTitle>
                    <DialogDescription>
                      {pipeline?.name} • {selectedRun.started_at && format(new Date(selectedRun.started_at), "PPpp")}
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
