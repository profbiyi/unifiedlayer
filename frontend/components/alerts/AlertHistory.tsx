"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useAlertHistory,
  useAcknowledgeAlert,
  useResolveAlert,
  AlertHistoryItem,
} from "@/hooks/queries/useAlerts";
import {
  AlertTriangle,
  AlertCircle,
  Info,
  Loader2,
  Check,
  CheckCircle,
  XCircle,
  ChevronLeft,
  ChevronRight,
  Bell,
  Eye,
  Filter,
} from "lucide-react";

const severityConfig = {
  critical: {
    label: "Critical",
    variant: "destructive" as const,
    icon: XCircle,
    className: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  },
  warning: {
    label: "Warning",
    variant: "warning" as const,
    icon: AlertTriangle,
    className: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  },
  info: {
    label: "Info",
    variant: "info" as const,
    icon: Info,
    className: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  },
};

const statusConfig = {
  triggered: {
    label: "Triggered",
    icon: Bell,
    className: "bg-red-100 text-red-800 dark:bg-red-900 dark:text-red-200",
  },
  acknowledged: {
    label: "Acknowledged",
    icon: Eye,
    className: "bg-yellow-100 text-yellow-800 dark:bg-yellow-900 dark:text-yellow-200",
  },
  resolved: {
    label: "Resolved",
    icon: CheckCircle,
    className: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  },
};

function formatDate(dateString: string): string {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();

  // Less than 1 minute
  if (diff < 60000) {
    return "Just now";
  }

  // Less than 1 hour
  if (diff < 3600000) {
    const minutes = Math.floor(diff / 60000);
    return `${minutes}m ago`;
  }

  // Less than 24 hours
  if (diff < 86400000) {
    const hours = Math.floor(diff / 3600000);
    return `${hours}h ago`;
  }

  // Less than 7 days
  if (diff < 604800000) {
    const days = Math.floor(diff / 86400000);
    return `${days}d ago`;
  }

  // Default to formatted date
  return date.toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function AlertHistory() {
  const [severityFilter, setSeverityFilter] = useState<string>("all");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [page, setPage] = useState(0);
  const limit = 10;

  const { data, isLoading, isFetching } = useAlertHistory({
    severity: severityFilter !== "all" ? severityFilter : undefined,
    status: statusFilter !== "all" ? statusFilter : undefined,
    skip: page * limit,
    limit,
  });

  const acknowledgeMutation = useAcknowledgeAlert();
  const resolveMutation = useResolveAlert();

  const handleAcknowledge = (alertId: string) => {
    acknowledgeMutation.mutate(alertId);
  };

  const handleResolve = (alertId: string) => {
    resolveMutation.mutate(alertId);
  };

  const totalPages = data ? Math.ceil(data.total / limit) : 0;

  return (
    <Card>
      <CardHeader>
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <CardTitle>Alert History</CardTitle>
            <CardDescription>
              View and manage past alert notifications
            </CardDescription>
          </div>
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <Select value={severityFilter} onValueChange={setSeverityFilter}>
              <SelectTrigger className="w-[130px]">
                <SelectValue placeholder="Severity" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Severity</SelectItem>
                <SelectItem value="critical">Critical</SelectItem>
                <SelectItem value="warning">Warning</SelectItem>
                <SelectItem value="info">Info</SelectItem>
              </SelectContent>
            </Select>
            <Select value={statusFilter} onValueChange={setStatusFilter}>
              <SelectTrigger className="w-[140px]">
                <SelectValue placeholder="Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="triggered">Triggered</SelectItem>
                <SelectItem value="acknowledged">Acknowledged</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : data?.items && data.items.length > 0 ? (
          <>
            <div className="rounded-md border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Time</TableHead>
                    <TableHead>Rule</TableHead>
                    <TableHead>Severity</TableHead>
                    <TableHead>Status</TableHead>
                    <TableHead className="hidden md:table-cell">Message</TableHead>
                    <TableHead className="text-right">Actions</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {data.items.map((alert: AlertHistoryItem) => {
                    const severity = severityConfig[alert.severity];
                    const status = statusConfig[alert.status];
                    const SeverityIcon = severity.icon;
                    const StatusIcon = status.icon;

                    return (
                      <TableRow key={alert.id}>
                        <TableCell className="font-medium whitespace-nowrap">
                          {formatDate(alert.triggered_at)}
                        </TableCell>
                        <TableCell>
                          <div>
                            <div className="font-medium">{alert.rule_name}</div>
                            {alert.pipeline_name && (
                              <div className="text-xs text-muted-foreground">
                                {alert.pipeline_name}
                              </div>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant={severity.variant} className="text-xs">
                            <SeverityIcon className="mr-1 h-3 w-3" />
                            {severity.label}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline" className={`text-xs ${status.className}`}>
                            <StatusIcon className="mr-1 h-3 w-3" />
                            {status.label}
                          </Badge>
                        </TableCell>
                        <TableCell className="hidden md:table-cell max-w-xs truncate">
                          <span className="text-sm text-muted-foreground">
                            {alert.message}
                          </span>
                        </TableCell>
                        <TableCell className="text-right">
                          <div className="flex items-center justify-end gap-1">
                            {alert.status === "triggered" && (
                              <>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleAcknowledge(alert.id)}
                                  disabled={acknowledgeMutation.isPending}
                                >
                                  <Eye className="h-3 w-3 mr-1" />
                                  Ack
                                </Button>
                                <Button
                                  variant="outline"
                                  size="sm"
                                  onClick={() => handleResolve(alert.id)}
                                  disabled={resolveMutation.isPending}
                                >
                                  <Check className="h-3 w-3 mr-1" />
                                  Resolve
                                </Button>
                              </>
                            )}
                            {alert.status === "acknowledged" && (
                              <Button
                                variant="outline"
                                size="sm"
                                onClick={() => handleResolve(alert.id)}
                                disabled={resolveMutation.isPending}
                              >
                                <Check className="h-3 w-3 mr-1" />
                                Resolve
                              </Button>
                            )}
                            {alert.status === "resolved" && (
                              <span className="text-xs text-muted-foreground">
                                Resolved
                              </span>
                            )}
                          </div>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            </div>

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-between mt-4">
                <p className="text-sm text-muted-foreground">
                  Showing {page * limit + 1} to{" "}
                  {Math.min((page + 1) * limit, data.total)} of {data.total}{" "}
                  alerts
                </p>
                <div className="flex items-center gap-2">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0 || isFetching}
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      setPage((p) => Math.min(totalPages - 1, p + 1))
                    }
                    disabled={page >= totalPages - 1 || isFetching}
                  >
                    Next
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="flex flex-col items-center justify-center py-12 text-center">
            <div className="flex h-12 w-12 items-center justify-center rounded-full bg-muted mb-4">
              <CheckCircle className="h-6 w-6 text-muted-foreground" />
            </div>
            <h3 className="font-medium mb-1">No alerts found</h3>
            <p className="text-sm text-muted-foreground max-w-sm">
              {severityFilter !== "all" || statusFilter !== "all"
                ? "No alerts match your current filters. Try adjusting them."
                : "You're all caught up! No alerts have been triggered yet."}
            </p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
