"use client";

import React from "react";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { AlertCircle, CheckCircle, Clock, Database, Loader2 } from "lucide-react";
import { SQLPreviewResult } from "@/types/transformation";
import { cn } from "@/lib/utils";

interface SQLPreviewProps {
  result: SQLPreviewResult | null;
  isLoading: boolean;
  error?: string;
}

export function SQLPreview({ result, isLoading, error }: SQLPreviewProps) {
  if (isLoading) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground mb-4" />
          <p className="text-sm text-muted-foreground">Executing query...</p>
        </CardContent>
      </Card>
    );
  }

  if (error) {
    return (
      <Card className="border-destructive/50 bg-destructive/5">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2 text-destructive">
            <AlertCircle className="h-4 w-4" />
            Query Error
          </CardTitle>
        </CardHeader>
        <CardContent>
          <pre className="text-sm text-destructive whitespace-pre-wrap font-mono bg-destructive/10 p-4 rounded-lg overflow-x-auto">
            {error}
          </pre>
        </CardContent>
      </Card>
    );
  }

  if (result?.error) {
    return (
      <Card className="border-destructive/50 bg-destructive/5">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2 text-destructive">
            <AlertCircle className="h-4 w-4" />
            Query Error
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <pre className="text-sm text-destructive whitespace-pre-wrap font-mono bg-destructive/10 p-4 rounded-lg overflow-x-auto">
            {result.error}
          </pre>
          {result.error_traceback && (
            <details className="text-xs">
              <summary className="cursor-pointer text-muted-foreground hover:text-foreground transition-colors">
                Show traceback
              </summary>
              <pre className="mt-2 text-muted-foreground whitespace-pre-wrap font-mono bg-muted p-3 rounded-lg overflow-x-auto">
                {result.error_traceback}
              </pre>
            </details>
          )}
        </CardContent>
      </Card>
    );
  }

  if (!result) {
    return (
      <Card className="border-dashed">
        <CardContent className="flex flex-col items-center justify-center py-12 text-center">
          <Database className="h-12 w-12 text-muted-foreground/50 mb-4" />
          <p className="text-sm text-muted-foreground">
            Click &quot;Test SQL&quot; to preview query results
          </p>
          <p className="text-xs text-muted-foreground/70 mt-1">
            Results are limited to 100 rows for preview
          </p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base flex items-center gap-2">
            <CheckCircle className="h-4 w-4 text-success" />
            Query Results
          </CardTitle>
          <div className="flex items-center gap-3">
            <Badge variant="outline" className="font-mono text-xs">
              <Database className="h-3 w-3 mr-1" />
              {result.row_count.toLocaleString()} rows
            </Badge>
            <Badge variant="outline" className="font-mono text-xs">
              <Clock className="h-3 w-3 mr-1" />
              {result.execution_time_ms.toFixed(0)}ms
            </Badge>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        {result.rows.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-sm text-muted-foreground">
              Query executed successfully but returned no rows.
            </p>
          </div>
        ) : (
          <div className="rounded-lg border overflow-hidden">
            <div className="overflow-x-auto max-h-[400px] overflow-y-auto">
              <Table>
                <TableHeader className="sticky top-0 bg-muted/95 backdrop-blur supports-[backdrop-filter]:bg-muted/60">
                  <TableRow>
                    {result.columns.map((column, index) => (
                      <TableHead
                        key={index}
                        className="font-semibold whitespace-nowrap"
                      >
                        {column}
                      </TableHead>
                    ))}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {result.rows.map((row, rowIndex) => (
                    <TableRow key={rowIndex}>
                      {result.columns.map((column, colIndex) => (
                        <TableCell
                          key={colIndex}
                          className={cn(
                            "font-mono text-sm whitespace-nowrap",
                            row[column] === null && "text-muted-foreground italic"
                          )}
                        >
                          {formatCellValue(row[column])}
                        </TableCell>
                      ))}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </div>
        )}
        {result.row_count > result.rows.length && (
          <p className="text-xs text-muted-foreground mt-3 text-center">
            Showing {result.rows.length} of {result.row_count.toLocaleString()} total rows
          </p>
        )}
      </CardContent>
    </Card>
  );
}

function formatCellValue(value: any): string {
  if (value === null || value === undefined) {
    return "NULL";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  if (typeof value === "number") {
    return value.toLocaleString();
  }
  return String(value);
}

export default SQLPreview;
