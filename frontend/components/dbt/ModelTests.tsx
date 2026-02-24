"use client";

import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
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
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
  Shield,
  Columns,
  Link as LinkIcon,
  Hash,
  List,
} from "lucide-react";
import { DbtModelTest } from "@/types/dbt";
import { formatDistanceToNow } from "date-fns";

interface ModelTestsProps {
  tests: DbtModelTest[];
}

const statusConfig: Record<
  string,
  {
    icon: React.ComponentType<{ className?: string }>;
    color: string;
    bgColor: string;
    label: string;
  }
> = {
  pass: {
    icon: CheckCircle,
    color: "text-green-600",
    bgColor: "bg-green-50",
    label: "Passed",
  },
  fail: {
    icon: XCircle,
    color: "text-red-600",
    bgColor: "bg-red-50",
    label: "Failed",
  },
  warn: {
    icon: AlertTriangle,
    color: "text-yellow-600",
    bgColor: "bg-yellow-50",
    label: "Warning",
  },
  skip: {
    icon: Clock,
    color: "text-gray-500",
    bgColor: "bg-gray-50",
    label: "Skipped",
  },
  pending: {
    icon: Clock,
    color: "text-gray-400",
    bgColor: "bg-gray-50",
    label: "Pending",
  },
};

const testTypeConfig: Record<
  string,
  {
    icon: React.ComponentType<{ className?: string }>;
    label: string;
    description: string;
  }
> = {
  unique: {
    icon: Hash,
    label: "Unique",
    description: "Ensures all values are unique",
  },
  not_null: {
    icon: Shield,
    label: "Not Null",
    description: "Ensures no null values",
  },
  accepted_values: {
    icon: List,
    label: "Accepted Values",
    description: "Ensures values are within allowed set",
  },
  relationships: {
    icon: LinkIcon,
    label: "Relationships",
    description: "Foreign key validation",
  },
  custom: {
    icon: Columns,
    label: "Custom",
    description: "Custom test logic",
  },
};

function TestStatusSummary({ tests }: { tests: DbtModelTest[] }) {
  const statusCounts = tests.reduce((acc, test) => {
    const status = test.status || "pending";
    acc[status] = (acc[status] || 0) + 1;
    return acc;
  }, {} as Record<string, number>);

  const statuses = ["pass", "fail", "warn", "skip", "pending"];

  return (
    <div className="flex items-center gap-3">
      {statuses.map((status) => {
        const count = statusCounts[status] || 0;
        if (count === 0) return null;

        const config = statusConfig[status];
        const Icon = config.icon;

        return (
          <div
            key={status}
            className={`flex items-center gap-1.5 px-2 py-1 rounded-md ${config.bgColor}`}
          >
            <Icon className={`h-4 w-4 ${config.color}`} />
            <span className={`text-sm font-medium ${config.color}`}>
              {count}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function ModelTests({ tests }: ModelTestsProps) {
  if (!tests || tests.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Tests
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <Shield className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No tests configured for this model</p>
            <p className="text-sm mt-1">
              Add tests in your schema.yml to ensure data quality.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="text-lg flex items-center gap-2">
              <Shield className="h-5 w-5" />
              Tests
            </CardTitle>
            <CardDescription>
              Data quality tests configured for this model
            </CardDescription>
          </div>
          <TestStatusSummary tests={tests} />
        </div>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[50px]">Status</TableHead>
              <TableHead>Test Name</TableHead>
              <TableHead>Type</TableHead>
              <TableHead>Column</TableHead>
              <TableHead>Last Run</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tests.map((test, idx) => {
              const status = test.status || "pending";
              const statusCfg = statusConfig[status];
              const StatusIcon = statusCfg.icon;
              const typeCfg = testTypeConfig[test.type] || testTypeConfig.custom;
              const TypeIcon = typeCfg.icon;

              return (
                <TableRow key={`${test.name}-${idx}`}>
                  <TableCell>
                    <div
                      className={`w-8 h-8 rounded-full flex items-center justify-center ${statusCfg.bgColor}`}
                    >
                      <StatusIcon className={`h-4 w-4 ${statusCfg.color}`} />
                    </div>
                  </TableCell>
                  <TableCell>
                    <div className="space-y-1">
                      <p className="font-medium">{test.name}</p>
                      {test.error_message && (
                        <p className="text-xs text-red-600 line-clamp-2">
                          {test.error_message}
                        </p>
                      )}
                    </div>
                  </TableCell>
                  <TableCell>
                    <Badge
                      variant="outline"
                      className="gap-1 text-xs capitalize"
                    >
                      <TypeIcon className="h-3 w-3" />
                      {typeCfg.label}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    {test.column_name ? (
                      <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                        {test.column_name}
                      </code>
                    ) : (
                      <span className="text-muted-foreground text-xs">
                        Model-level
                      </span>
                    )}
                  </TableCell>
                  <TableCell className="text-muted-foreground text-sm">
                    {test.last_run_at ? (
                      formatDistanceToNow(new Date(test.last_run_at), {
                        addSuffix: true,
                      })
                    ) : (
                      <span className="italic">Never</span>
                    )}
                  </TableCell>
                </TableRow>
              );
            })}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
