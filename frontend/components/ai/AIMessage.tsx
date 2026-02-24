"use client";

import { Sparkles, User, AlertCircle, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AIMessage as AIMessageType } from "@/types/ai";
import { SQLCodeBlock } from "./SQLCodeBlock";
import { ResultsChart } from "./ResultsChart";
import { ResultsTable } from "./ResultsTable";
import { Alert, AlertDescription } from "@/components/ui/alert";

interface AIMessageProps {
  message: AIMessageType;
}

export function AIMessage({ message }: AIMessageProps) {
  const isUser = message.role === "user";

  return (
    <div
      className={cn(
        "flex gap-3 p-4",
        isUser ? "justify-end" : "justify-start"
      )}
    >
      {!isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
          <Sparkles className="h-4 w-4 text-primary" />
        </div>
      )}

      <div
        className={cn(
          "max-w-[85%] space-y-3",
          isUser ? "items-end" : "items-start"
        )}
      >
        {/* Message content */}
        <div
          className={cn(
            "rounded-lg px-4 py-2",
            isUser
              ? "bg-primary text-primary-foreground"
              : "bg-muted"
          )}
        >
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        </div>

        {/* SQL code block (for assistant messages) */}
        {!isUser && message.sql && (
          <div className="w-full">
            <SQLCodeBlock sql={message.sql} />
          </div>
        )}

        {/* Error message */}
        {!isUser && message.error && (
          <Alert variant="destructive" className="w-full">
            <AlertCircle className="h-4 w-4" />
            <AlertDescription>{message.error}</AlertDescription>
          </Alert>
        )}

        {/* Results visualization */}
        {!isUser && message.results && message.results.length > 0 && message.chart_config && (
          <div className="w-full space-y-3">
            {/* Chart (if not table type) */}
            {message.chart_config.type !== "table" && (
              <ResultsChart
                data={message.results}
                config={message.chart_config}
              />
            )}

            {/* Table (always show for table type, or as expandable for others) */}
            {(message.chart_config.type === "table" || message.results.length > 1) && (
              <ResultsTable
                data={message.results}
                config={message.chart_config}
              />
            )}
          </div>
        )}

        {/* Execution metadata */}
        {!isUser && message.execution_time_ms && (
          <div className="flex items-center gap-1 text-xs text-muted-foreground">
            <Clock className="h-3 w-3" />
            <span>{message.execution_time_ms}ms</span>
            {message.row_count !== undefined && (
              <>
                <span className="mx-1">·</span>
                <span>{message.row_count} row{message.row_count !== 1 ? "s" : ""}</span>
              </>
            )}
          </div>
        )}
      </div>

      {isUser && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
          <User className="h-4 w-4" />
        </div>
      )}
    </div>
  );
}
