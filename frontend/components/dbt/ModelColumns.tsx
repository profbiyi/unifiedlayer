"use client";

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Key,
  Hash,
  Type,
  CheckCircle,
  XCircle,
  Clock,
  AlertTriangle,
} from "lucide-react";
import { DbtModelColumn, DbtColumnTest } from "@/types/dbt";

interface ModelColumnsProps {
  columns: DbtModelColumn[];
  isLoading?: boolean;
}

const testStatusConfig: Record<
  string,
  { icon: React.ComponentType<{ className?: string }>; color: string }
> = {
  pass: { icon: CheckCircle, color: "text-green-600" },
  fail: { icon: XCircle, color: "text-red-600" },
  warn: { icon: AlertTriangle, color: "text-yellow-600" },
  skip: { icon: Clock, color: "text-gray-500" },
  pending: { icon: Clock, color: "text-gray-400" },
};

function TestBadge({ test }: { test: DbtColumnTest }) {
  const status = test.status || "pending";
  const config = testStatusConfig[status] || testStatusConfig.pending;
  const StatusIcon = config.icon;

  const testTypeLabel: Record<string, string> = {
    unique: "Unique",
    not_null: "Not Null",
    accepted_values: "Accepted Values",
    relationships: "FK",
    custom: "Custom",
  };

  return (
    <Badge
      variant="outline"
      className={`text-xs gap-1 ${config.color} border-current`}
    >
      <StatusIcon className="h-3 w-3" />
      {testTypeLabel[test.type] || test.name}
    </Badge>
  );
}

function ColumnTypeBadge({ dataType }: { dataType?: string }) {
  if (!dataType) return null;

  const type = dataType.toLowerCase();
  let icon = Type;
  let color = "text-gray-600 border-gray-300";

  if (type.includes("int") || type.includes("numeric") || type.includes("decimal") || type.includes("float")) {
    icon = Hash;
    color = "text-blue-600 border-blue-300";
  } else if (type.includes("key") || type.includes("id")) {
    icon = Key;
    color = "text-purple-600 border-purple-300";
  }

  const Icon = icon;

  return (
    <Badge variant="outline" className={`text-xs font-mono gap-1 ${color}`}>
      <Icon className="h-3 w-3" />
      {dataType}
    </Badge>
  );
}

function ColumnsTableSkeleton() {
  return (
    <div className="space-y-2">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex items-center gap-4 p-3 border rounded-md">
          <Skeleton className="h-4 w-32" />
          <Skeleton className="h-5 w-20 rounded-full" />
          <Skeleton className="h-4 w-48 flex-1" />
          <div className="flex gap-1">
            <Skeleton className="h-5 w-16 rounded-full" />
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
        </div>
      ))}
    </div>
  );
}

export default function ModelColumns({ columns, isLoading }: ModelColumnsProps) {
  if (isLoading) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Columns</CardTitle>
        </CardHeader>
        <CardContent>
          <ColumnsTableSkeleton />
        </CardContent>
      </Card>
    );
  }

  if (!columns || columns.length === 0) {
    return (
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Columns</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-center py-8 text-muted-foreground">
            <Type className="h-12 w-12 mx-auto mb-3 opacity-50" />
            <p>No column information available</p>
            <p className="text-sm mt-1">
              Column metadata will appear here once the manifest is parsed.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center justify-between">
          <span>Columns</span>
          <Badge variant="secondary">{columns.length} columns</Badge>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-[200px]">Name</TableHead>
              <TableHead className="w-[150px]">Type</TableHead>
              <TableHead>Description</TableHead>
              <TableHead className="w-[200px]">Tests</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {columns.map((column) => (
              <TableRow key={column.name}>
                <TableCell className="font-mono text-sm font-medium">
                  {column.name}
                </TableCell>
                <TableCell>
                  <ColumnTypeBadge dataType={column.data_type} />
                </TableCell>
                <TableCell className="text-muted-foreground text-sm">
                  {column.description || (
                    <span className="italic opacity-60">No description</span>
                  )}
                </TableCell>
                <TableCell>
                  {column.tests && column.tests.length > 0 ? (
                    <div className="flex flex-wrap gap-1">
                      {column.tests.map((test, idx) => (
                        <TestBadge key={`${test.name}-${idx}`} test={test} />
                      ))}
                    </div>
                  ) : (
                    <span className="text-xs text-muted-foreground italic">
                      No tests
                    </span>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </CardContent>
    </Card>
  );
}
