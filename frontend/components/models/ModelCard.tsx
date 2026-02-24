"use client";

import { GeneratedModel, ModelLayer } from "@/types/models";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { Box, Boxes, Grid3X3, Columns, CheckCircle, Sparkles } from "lucide-react";

interface ModelCardProps {
  model: GeneratedModel;
  onClick?: () => void;
  className?: string;
}

const layerConfig: Record<
  ModelLayer,
  { label: string; color: string; bgColor: string; icon: React.ReactNode }
> = {
  raw: {
    label: "Raw",
    color: "text-slate-600",
    bgColor: "bg-slate-100 dark:bg-slate-800",
    icon: <Columns className="h-4 w-4" />,
  },
  canonical: {
    label: "Canonical",
    color: "text-blue-600",
    bgColor: "bg-blue-100 dark:bg-blue-900/30",
    icon: <Grid3X3 className="h-4 w-4" />,
  },
  dimensional: {
    label: "Dimensional",
    color: "text-purple-600",
    bgColor: "bg-purple-100 dark:bg-purple-900/30",
    icon: <Boxes className="h-4 w-4" />,
  },
};

function getModelIcon(model: GeneratedModel) {
  // Determine if this is a fact or dimension table based on naming convention
  const nameLower = model.name.toLowerCase();
  if (nameLower.startsWith("fact_") || nameLower.includes("_fact")) {
    return <Box className="h-5 w-5 text-amber-500" />;
  }
  if (nameLower.startsWith("dim_") || nameLower.includes("_dim")) {
    return <Grid3X3 className="h-5 w-5 text-indigo-500" />;
  }
  return <Boxes className="h-5 w-5 text-primary" />;
}

export function ModelCard({ model, onClick, className }: ModelCardProps) {
  const layer = layerConfig[model.layer];

  return (
    <Card
      className={cn(
        "cursor-pointer hover:border-primary/50 transition-all",
        className
      )}
      onClick={onClick}
    >
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-2">
          <div className="flex items-center gap-3 min-w-0">
            <div className="flex-shrink-0 p-2 rounded-lg bg-muted">
              {getModelIcon(model)}
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 flex-wrap">
                <CardTitle className="text-base truncate">
                  {model.name}
                </CardTitle>
                {model.is_materialized && (
                  <Badge variant="success" className="flex items-center gap-1 text-xs">
                    <CheckCircle className="h-3 w-3" />
                    Materialized
                  </Badge>
                )}
              </div>
              <CardDescription className="line-clamp-2 mt-1">
                {model.description}
              </CardDescription>
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Layer Badge */}
        <div className="flex items-center gap-2">
          <Badge
            variant="outline"
            className={cn("flex items-center gap-1", layer.bgColor, layer.color)}
          >
            {layer.icon}
            {layer.label}
          </Badge>
        </div>

        {/* Source Tables */}
        {model.source_tables.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {model.source_tables.slice(0, 3).map((table, index) => (
              <Badge key={index} variant="secondary" className="text-xs">
                {table}
              </Badge>
            ))}
            {model.source_tables.length > 3 && (
              <Badge variant="secondary" className="text-xs">
                +{model.source_tables.length - 3} more
              </Badge>
            )}
          </div>
        )}

        {/* Stats */}
        <div className="flex items-center gap-4 pt-2 border-t text-xs text-muted-foreground">
          <span>{model.columns.length} columns</span>
          <span>{model.relationships.length} relationships</span>
          {model.business_questions.length > 0 && (
            <span className="flex items-center gap-1">
              <Sparkles className="h-3 w-3" />
              {model.business_questions.length} questions
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

export default ModelCard;
