"use client";

import { useState, useMemo, useRef, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  ChevronDown,
  ChevronRight,
  Clock,
  Download,
  RefreshCw,
  CheckCircle2,
  XCircle,
  AlertTriangle,
  Loader2,
  Copy,
  Check,
} from "lucide-react";
import { DbtRun, DbtModelExecution } from "@/types/dbt";
import { useDbtRun, useDbtRunLogs } from "@/hooks/queries/useDbt";
import { formatDistanceToNow, format } from "date-fns";

interface DbtRunLogsProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  runId: string;
}

interface LogSection {
  type: "info" | "warning" | "error" | "success" | "debug";
  timestamp?: string;
  content: string;
}

export default function DbtRunLogs({ open, onOpenChange, runId }: DbtRunLogsProps) {
  const { data: run, isLoading: isLoadingRun } = useDbtRun(runId);
  const { data: logs, isLoading: isLoadingLogs, refetch: refetchLogs } = useDbtRunLogs(runId);

  const [expandedSections, setExpandedSections] = useState<Set<string>>(
    new Set(["logs"])
  );
  const [copied, setCopied] = useState(false);
  const logsEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom when logs update
  useEffect(() => {
    if (run?.status === "running" && logsEndRef.current) {
      logsEndRef.current.scrollIntoView({ behavior: "smooth" });
    }
  }, [logs, run?.status]);

  const toggleSection = (section: string) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(section)) {
      newExpanded.delete(section);
    } else {
      newExpanded.add(section);
    }
    setExpandedSections(newExpanded);
  };

  const parsedLogs = useMemo((): LogSection[] => {
    if (!logs) return [];

    const lines = logs.split("\n");
    return lines.map((line) => {
      // Detect log type based on content
      let type: LogSection["type"] = "info";
      if (
        line.toLowerCase().includes("error") ||
        line.toLowerCase().includes("failed")
      ) {
        type = "error";
      } else if (
        line.toLowerCase().includes("warning") ||
        line.toLowerCase().includes("warn")
      ) {
        type = "warning";
      } else if (
        line.toLowerCase().includes("success") ||
        line.toLowerCase().includes("completed") ||
        line.toLowerCase().includes("done")
      ) {
        type = "success";
      } else if (
        line.toLowerCase().includes("debug") ||
        line.startsWith("  ")
      ) {
        type = "debug";
      }

      // Try to extract timestamp
      const timestampMatch = line.match(
        /^(\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}:\d{2})/
      );

      return {
        type,
        timestamp: timestampMatch?.[1],
        content: timestampMatch ? line.slice(timestampMatch[0].length + 1) : line,
      };
    });
  }, [logs]);

  const getLogLineClass = (type: LogSection["type"]) => {
    switch (type) {
      case "error":
        return "text-red-500 bg-red-500/5";
      case "warning":
        return "text-yellow-500 bg-yellow-500/5";
      case "success":
        return "text-green-500";
      case "debug":
        return "text-muted-foreground";
      default:
        return "";
    }
  };

  const getModelStatusIcon = (status: string) => {
    switch (status) {
      case "success":
        return <CheckCircle2 className="h-4 w-4 text-green-500" />;
      case "error":
        return <XCircle className="h-4 w-4 text-red-500" />;
      case "skipped":
        return <AlertTriangle className="h-4 w-4 text-yellow-500" />;
      default:
        return <Loader2 className="h-4 w-4 animate-spin" />;
    }
  };

  const handleCopyLogs = async () => {
    if (logs) {
      await navigator.clipboard.writeText(logs);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const handleDownloadLogs = () => {
    if (logs) {
      const blob = new Blob([logs], { type: "text/plain" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `dbt-run-${runId}-logs.txt`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    }
  };

  const formatDuration = (seconds?: number) => {
    if (!seconds) return "-";
    if (seconds < 60) return `${seconds.toFixed(1)}s`;
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
  };

  const isLoading = isLoadingRun || isLoadingLogs;
  const isRunning = run?.status === "running" || run?.status === "pending";

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[900px] max-h-[90vh] flex flex-col">
        <DialogHeader className="pb-4 border-b">
          <div className="flex items-center justify-between">
            <DialogTitle>dbt Run Logs</DialogTitle>
            {run && (
              <div className="flex items-center gap-2">
                <Badge
                  variant={
                    run.status === "completed"
                      ? "success"
                      : run.status === "failed"
                      ? "destructive"
                      : run.status === "running"
                      ? "running"
                      : "secondary"
                  }
                >
                  {run.status}
                </Badge>
              </div>
            )}
          </div>
          {run && (
            <div className="flex items-center gap-4 text-sm text-muted-foreground mt-2">
              <div className="flex items-center gap-1">
                <Clock className="h-4 w-4" />
                Started{" "}
                {run.started_at
                  ? formatDistanceToNow(new Date(run.started_at), {
                      addSuffix: true,
                    })
                  : "pending"}
              </div>
              {run.duration_seconds && (
                <div>Duration: {formatDuration(run.duration_seconds)}</div>
              )}
              {run.full_refresh && (
                <Badge variant="outline">Full Refresh</Badge>
              )}
            </div>
          )}
        </DialogHeader>

        <div className="flex-1 overflow-hidden flex flex-col min-h-0">
          {isLoading ? (
            <div className="flex items-center justify-center py-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : (
            <>
              {/* Model Execution List */}
              {run?.models_executed && run.models_executed.length > 0 && (
                <div className="border-b">
                  <button
                    onClick={() => toggleSection("models")}
                    className="flex items-center gap-2 w-full p-3 hover:bg-muted/50 transition-colors"
                  >
                    {expandedSections.has("models") ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    <span className="font-medium">
                      Model Execution ({run.models_executed.length} models)
                    </span>
                  </button>
                  {expandedSections.has("models") && (
                    <div className="px-3 pb-3">
                      <div className="rounded-lg border overflow-hidden">
                        <table className="w-full text-sm">
                          <thead className="bg-muted/50">
                            <tr>
                              <th className="text-left p-2">Model</th>
                              <th className="text-left p-2">Status</th>
                              <th className="text-right p-2">Rows</th>
                              <th className="text-right p-2">Duration</th>
                            </tr>
                          </thead>
                          <tbody>
                            {run.models_executed.map(
                              (model: DbtModelExecution, idx: number) => (
                                <tr
                                  key={idx}
                                  className="border-t hover:bg-muted/30"
                                >
                                  <td className="p-2 font-mono text-xs">
                                    {model.model_name}
                                  </td>
                                  <td className="p-2">
                                    <div className="flex items-center gap-2">
                                      {getModelStatusIcon(model.status)}
                                      <span className="capitalize">
                                        {model.status}
                                      </span>
                                    </div>
                                  </td>
                                  <td className="p-2 text-right text-muted-foreground">
                                    {model.rows_affected?.toLocaleString() || "-"}
                                  </td>
                                  <td className="p-2 text-right text-muted-foreground">
                                    {formatDuration(model.duration_seconds)}
                                  </td>
                                </tr>
                              )
                            )}
                          </tbody>
                        </table>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Logs Section */}
              <div className="flex-1 min-h-0 flex flex-col">
                <div className="flex items-center justify-between p-3 border-b">
                  <button
                    onClick={() => toggleSection("logs")}
                    className="flex items-center gap-2 hover:text-foreground"
                  >
                    {expandedSections.has("logs") ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    <span className="font-medium">Console Output</span>
                  </button>
                  <div className="flex items-center gap-2">
                    {isRunning && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => refetchLogs()}
                      >
                        <RefreshCw className="h-4 w-4 mr-1" />
                        Refresh
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleCopyLogs}
                      disabled={!logs}
                    >
                      {copied ? (
                        <>
                          <Check className="h-4 w-4 mr-1" />
                          Copied
                        </>
                      ) : (
                        <>
                          <Copy className="h-4 w-4 mr-1" />
                          Copy
                        </>
                      )}
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleDownloadLogs}
                      disabled={!logs}
                    >
                      <Download className="h-4 w-4 mr-1" />
                      Download
                    </Button>
                  </div>
                </div>
                {expandedSections.has("logs") && (
                  <div className="flex-1 overflow-auto bg-muted/30 p-3 font-mono text-xs">
                    {parsedLogs.length === 0 ? (
                      <div className="text-muted-foreground text-center py-4">
                        {isRunning
                          ? "Waiting for logs..."
                          : "No logs available"}
                      </div>
                    ) : (
                      <div className="space-y-0.5">
                        {parsedLogs.map((line, idx) => (
                          <div
                            key={idx}
                            className={`px-2 py-0.5 rounded ${getLogLineClass(
                              line.type
                            )}`}
                          >
                            {line.timestamp && (
                              <span className="text-muted-foreground mr-2">
                                [{format(new Date(line.timestamp), "HH:mm:ss")}]
                              </span>
                            )}
                            {line.content}
                          </div>
                        ))}
                        <div ref={logsEndRef} />
                      </div>
                    )}
                  </div>
                )}
              </div>

              {/* Error Message */}
              {run?.error_message && (
                <div className="p-3 border-t bg-red-500/5">
                  <div className="flex items-start gap-2 text-red-500">
                    <XCircle className="h-5 w-5 shrink-0 mt-0.5" />
                    <div>
                      <p className="font-medium">Error</p>
                      <p className="text-sm mt-1 whitespace-pre-wrap">
                        {run.error_message}
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}
