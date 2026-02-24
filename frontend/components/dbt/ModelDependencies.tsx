"use client";

import { useMemo } from "react";
import Link from "next/link";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ArrowUpRight,
  ArrowDownRight,
  Workflow,
  ExternalLink,
  GitBranch,
  Database,
} from "lucide-react";
import { DbtModel } from "@/types/dbt";

interface ModelDependenciesProps {
  model: DbtModel;
  allModels?: DbtModel[];
}

interface DependencyItemProps {
  uniqueId: string;
  modelId?: string;
}

function DependencyItem({ uniqueId, modelId }: DependencyItemProps) {
  // Parse unique_id to extract model name (format: model.project.model_name)
  const parts = uniqueId.split(".");
  const modelName = parts[parts.length - 1];
  const resourceType = parts[0];
  const projectName = parts.length > 2 ? parts[1] : undefined;

  const isModel = resourceType === "model";
  const isSource = resourceType === "source";
  const isSeed = resourceType === "seed";

  return (
    <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors">
      <div className="flex items-center gap-3 min-w-0">
        <div
          className={`p-1.5 rounded ${
            isSource
              ? "bg-blue-100"
              : isSeed
              ? "bg-teal-100"
              : "bg-purple-100"
          }`}
        >
          {isSource ? (
            <Database className="h-4 w-4 text-blue-600" />
          ) : isSeed ? (
            <Database className="h-4 w-4 text-teal-600" />
          ) : (
            <Workflow className="h-4 w-4 text-purple-600" />
          )}
        </div>
        <div className="min-w-0">
          <p className="font-medium truncate">{modelName}</p>
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Badge variant="outline" className="text-xs capitalize">
              {resourceType}
            </Badge>
            {projectName && (
              <span className="flex items-center gap-1">
                <GitBranch className="h-3 w-3" />
                {projectName}
              </span>
            )}
          </div>
        </div>
      </div>
      {isModel && modelId && (
        <Link href={`/settings/dbt/models/${modelId}`}>
          <Button variant="ghost" size="icon" className="h-8 w-8">
            <ExternalLink className="h-4 w-4" />
          </Button>
        </Link>
      )}
    </div>
  );
}

function MiniLineageGraph({ model }: { model: DbtModel }) {
  const upstreamCount = model.depends_on.length;
  const downstreamCount = model.referenced_by.length;

  return (
    <div className="flex items-center justify-center gap-4 py-6">
      {/* Upstream */}
      <div className="flex flex-col items-center">
        <div className="w-20 h-20 rounded-full bg-blue-50 border-2 border-blue-200 flex items-center justify-center">
          <div className="text-center">
            <ArrowUpRight className="h-5 w-5 text-blue-600 mx-auto" />
            <span className="text-xl font-bold text-blue-600">{upstreamCount}</span>
          </div>
        </div>
        <span className="text-xs text-muted-foreground mt-2">Upstream</span>
      </div>

      {/* Arrow */}
      <div className="flex items-center">
        <div className="w-8 h-0.5 bg-gray-300" />
        <div className="w-0 h-0 border-l-8 border-l-gray-300 border-y-4 border-y-transparent" />
      </div>

      {/* Current Model */}
      <div className="flex flex-col items-center">
        <div className="w-24 h-24 rounded-lg bg-purple-100 border-2 border-purple-400 flex items-center justify-center shadow-md">
          <div className="text-center px-2">
            <Workflow className="h-6 w-6 text-purple-600 mx-auto mb-1" />
            <span className="text-xs font-medium text-purple-700 truncate block max-w-full">
              {model.name}
            </span>
          </div>
        </div>
        <span className="text-xs font-medium text-purple-600 mt-2">Current</span>
      </div>

      {/* Arrow */}
      <div className="flex items-center">
        <div className="w-8 h-0.5 bg-gray-300" />
        <div className="w-0 h-0 border-l-8 border-l-gray-300 border-y-4 border-y-transparent" />
      </div>

      {/* Downstream */}
      <div className="flex flex-col items-center">
        <div className="w-20 h-20 rounded-full bg-emerald-50 border-2 border-emerald-200 flex items-center justify-center">
          <div className="text-center">
            <ArrowDownRight className="h-5 w-5 text-emerald-600 mx-auto" />
            <span className="text-xl font-bold text-emerald-600">{downstreamCount}</span>
          </div>
        </div>
        <span className="text-xs text-muted-foreground mt-2">Downstream</span>
      </div>
    </div>
  );
}

export default function ModelDependencies({ model, allModels }: ModelDependenciesProps) {
  // Map unique_ids to model IDs for linking
  const uniqueIdToModelId = useMemo(() => {
    if (!allModels) return {};
    return allModels.reduce((acc, m) => {
      acc[m.unique_id] = m.id;
      return acc;
    }, {} as Record<string, string>);
  }, [allModels]);

  const hasUpstream = model.depends_on.length > 0;
  const hasDownstream = model.referenced_by.length > 0;
  const hasDependencies = hasUpstream || hasDownstream;

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg flex items-center gap-2">
          <GitBranch className="h-5 w-5" />
          Dependencies
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Mini Lineage Visualization */}
        <MiniLineageGraph model={model} />

        {!hasDependencies && (
          <div className="text-center py-4 text-muted-foreground">
            <p>This model has no dependencies or dependents.</p>
          </div>
        )}

        {/* Upstream Dependencies */}
        {hasUpstream && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <ArrowUpRight className="h-4 w-4 text-blue-600" />
              <h4 className="font-medium">
                Upstream Dependencies ({model.depends_on.length})
              </h4>
            </div>
            <div className="space-y-2 pl-6">
              {model.depends_on.map((dep) => (
                <DependencyItem
                  key={dep}
                  uniqueId={dep}
                  modelId={uniqueIdToModelId[dep]}
                />
              ))}
            </div>
          </div>
        )}

        {/* Downstream Dependents */}
        {hasDownstream && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <ArrowDownRight className="h-4 w-4 text-emerald-600" />
              <h4 className="font-medium">
                Downstream Dependents ({model.referenced_by.length})
              </h4>
            </div>
            <div className="space-y-2 pl-6">
              {model.referenced_by.map((ref) => (
                <DependencyItem
                  key={ref}
                  uniqueId={ref}
                  modelId={uniqueIdToModelId[ref]}
                />
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
