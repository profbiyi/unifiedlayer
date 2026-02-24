"use client";

import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Database,
  Table,
  Layers,
  GitBranch,
  ArrowUpRight,
  ArrowDownRight,
  CheckCircle,
  XCircle,
  Clock,
  Tag,
} from "lucide-react";
import { DbtModelSummary, DbtMaterialization } from "@/types/dbt";

interface ModelCardProps {
  model: DbtModelSummary;
}

const materializationConfig: Record<
  DbtMaterialization,
  { icon: React.ComponentType<{ className?: string }>; color: string; bg: string }
> = {
  table: { icon: Table, color: "text-blue-600", bg: "bg-blue-100" },
  view: { icon: Database, color: "text-green-600", bg: "bg-green-100" },
  incremental: { icon: Layers, color: "text-purple-600", bg: "bg-purple-100" },
  ephemeral: { icon: GitBranch, color: "text-orange-600", bg: "bg-orange-100" },
  snapshot: { icon: Clock, color: "text-amber-600", bg: "bg-amber-100" },
  seed: { icon: Database, color: "text-teal-600", bg: "bg-teal-100" },
};

const statusConfig: Record<
  string,
  { icon: React.ComponentType<{ className?: string }>; color: string }
> = {
  pass: { icon: CheckCircle, color: "text-green-600" },
  fail: { icon: XCircle, color: "text-red-600" },
  skip: { icon: Clock, color: "text-gray-500" },
  pending: { icon: Clock, color: "text-yellow-600" },
};

export default function ModelCard({ model }: ModelCardProps) {
  const matConfig = materializationConfig[model.materialization] || materializationConfig.table;
  const MatIcon = matConfig.icon;
  const status = model.last_run_status || "pending";
  const StatusIcon = statusConfig[status]?.icon || Clock;
  const statusColor = statusConfig[status]?.color || "text-gray-500";

  return (
    <Link href={`/settings/dbt/models/${model.id}`}>
      <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="space-y-1 flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <div className={`p-1.5 rounded ${matConfig.bg}`}>
                  <MatIcon className={`h-4 w-4 ${matConfig.color}`} />
                </div>
                <CardTitle className="text-lg truncate">{model.name}</CardTitle>
                <StatusIcon className={`h-4 w-4 shrink-0 ${statusColor}`} />
              </div>
              {model.description ? (
                <CardDescription className="line-clamp-2">
                  {model.description}
                </CardDescription>
              ) : (
                <CardDescription className="text-muted-foreground/60 italic">
                  No description
                </CardDescription>
              )}
            </div>
          </div>
        </CardHeader>
        <CardContent className="space-y-3">
          {/* Schema and Project */}
          <div className="flex items-center gap-4 text-sm text-muted-foreground">
            <div className="flex items-center gap-1.5">
              <Database className="h-3.5 w-3.5" />
              <span className="font-mono text-xs">{model.schema}</span>
            </div>
            {model.project_name && (
              <div className="flex items-center gap-1.5">
                <GitBranch className="h-3.5 w-3.5" />
                <span className="text-xs truncate">{model.project_name}</span>
              </div>
            )}
          </div>

          {/* Materialization Badge */}
          <div className="flex items-center gap-2">
            <Badge
              variant="outline"
              className={`text-xs capitalize ${matConfig.color} border-current`}
            >
              {model.materialization}
            </Badge>
          </div>

          {/* Tags */}
          {model.tags.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {model.tags.slice(0, 3).map((tag) => (
                <Badge
                  key={tag}
                  variant="secondary"
                  className="text-xs font-normal"
                >
                  <Tag className="h-3 w-3 mr-1" />
                  {tag}
                </Badge>
              ))}
              {model.tags.length > 3 && (
                <Badge variant="secondary" className="text-xs font-normal">
                  +{model.tags.length - 3}
                </Badge>
              )}
            </div>
          )}

          {/* Stats */}
          <div className="flex items-center gap-4 pt-2 border-t text-xs text-muted-foreground">
            <div className="flex items-center gap-1">
              <Table className="h-3 w-3" />
              <span>{model.columns_count} columns</span>
            </div>
            <div className="flex items-center gap-1">
              <CheckCircle className="h-3 w-3" />
              <span>{model.tests_count} tests</span>
            </div>
            <div className="flex items-center gap-1">
              <ArrowUpRight className="h-3 w-3" />
              <span>{model.upstream_count}</span>
            </div>
            <div className="flex items-center gap-1">
              <ArrowDownRight className="h-3 w-3" />
              <span>{model.downstream_count}</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </Link>
  );
}
