"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Check, Copy, ChevronDown, ChevronUp, Code } from "lucide-react";
import { cn } from "@/lib/utils";

interface SQLCodeBlockProps {
  sql: string;
  defaultExpanded?: boolean;
}

export function SQLCodeBlock({ sql, defaultExpanded = false }: SQLCodeBlockProps) {
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(defaultExpanded);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(sql);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // Format SQL with basic syntax highlighting
  const formatSQL = (sql: string) => {
    const keywords = [
      "SELECT", "FROM", "WHERE", "AND", "OR", "JOIN", "LEFT", "RIGHT", "INNER",
      "OUTER", "ON", "GROUP", "BY", "ORDER", "HAVING", "LIMIT", "OFFSET",
      "AS", "DISTINCT", "COUNT", "SUM", "AVG", "MIN", "MAX", "CASE", "WHEN",
      "THEN", "ELSE", "END", "IN", "NOT", "NULL", "IS", "LIKE", "BETWEEN",
      "EXISTS", "UNION", "ALL", "INSERT", "UPDATE", "DELETE", "CREATE", "DROP",
      "TABLE", "INDEX", "VIEW", "WITH", "OVER", "PARTITION", "COALESCE",
      "CAST", "EXTRACT", "DATE_TRUNC", "NOW", "INTERVAL",
    ];

    const keywordPattern = new RegExp(`\\b(${keywords.join("|")})\\b`, "gi");

    return sql.split("\n").map((line, i) => {
      // Highlight keywords
      const highlighted = line.replace(keywordPattern, '<span class="text-blue-500 font-medium">$1</span>');
      // Highlight strings
      const withStrings = highlighted.replace(/'[^']*'/g, '<span class="text-green-500">$&</span>');
      // Highlight numbers
      const withNumbers = withStrings.replace(/\b(\d+\.?\d*)\b/g, '<span class="text-orange-500">$1</span>');

      return (
        <div key={i} className="flex">
          <span className="w-8 text-right pr-3 text-muted-foreground select-none">
            {i + 1}
          </span>
          <span dangerouslySetInnerHTML={{ __html: withNumbers }} />
        </div>
      );
    });
  };

  return (
    <div className="rounded-lg border bg-muted/50 overflow-hidden">
      <div
        className="flex items-center justify-between px-3 py-2 bg-muted/80 cursor-pointer hover:bg-muted"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Code className="h-4 w-4" />
          <span>SQL Query</span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2"
            onClick={(e) => {
              e.stopPropagation();
              handleCopy();
            }}
          >
            {copied ? (
              <Check className="h-3.5 w-3.5 text-green-500" />
            ) : (
              <Copy className="h-3.5 w-3.5" />
            )}
          </Button>
          <Button variant="ghost" size="sm" className="h-7 px-1">
            {expanded ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      <div
        className={cn(
          "overflow-hidden transition-all duration-200",
          expanded ? "max-h-[500px]" : "max-h-0"
        )}
      >
        <div className="p-3 overflow-x-auto">
          <pre className="text-sm font-mono leading-relaxed">
            <code>{formatSQL(sql)}</code>
          </pre>
        </div>
      </div>
    </div>
  );
}
