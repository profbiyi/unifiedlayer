"use client";

import { use } from "react";
import Link from "next/link";
import {
  useDbtModel,
  useDbtModelRuns,
  useDbtModels,
} from "@/hooks/queries/useDbt";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import ModelColumns from "@/components/dbt/ModelColumns";
import ModelDependencies from "@/components/dbt/ModelDependencies";
import ModelTests from "@/components/dbt/ModelTests";
import {
  ArrowLeft,
  Database,
  GitBranch,
  Tag,
  Layers,
  Table,
  Clock,
  FileCode,
  CheckCircle,
  XCircle,
  History,
  Loader2,
  Copy,
  ExternalLink,
} from "lucide-react";
import { DbtMaterialization } from "@/types/dbt";
import { formatDistanceToNow, format } from "date-fns";
import toast from "react-hot-toast";

interface PageProps {
  params: Promise<{ modelId: string }>;
}

const materializationConfig: Record<
  DbtMaterialization,
  { color: string; bg: string; label: string }
> = {
  table: { color: "text-blue-600", bg: "bg-blue-100", label: "Table" },
  view: { color: "text-green-600", bg: "bg-green-100", label: "View" },
  incremental: { color: "text-purple-600", bg: "bg-purple-100", label: "Incremental" },
  ephemeral: { color: "text-orange-600", bg: "bg-orange-100", label: "Ephemeral" },
  snapshot: { color: "text-amber-600", bg: "bg-amber-100", label: "Snapshot" },
  seed: { color: "text-teal-600", bg: "bg-teal-100", label: "Seed" },
};

function ModelDetailSkeleton() {
  return (
    <div className="space-y-6">
      {/* Header Skeleton */}
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-4 w-96" />
          <div className="flex gap-2 mt-2">
            <Skeleton className="h-6 w-20 rounded-full" />
            <Skeleton className="h-6 w-24 rounded-full" />
            <Skeleton className="h-6 w-16 rounded-full" />
          </div>
        </div>
        <Skeleton className="h-10 w-32" />
      </div>

      {/* Info Cards Skeleton */}
      <div className="grid gap-4 md:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Card key={i} className="p-4">
            <div className="flex items-center gap-3">
              <Skeleton className="h-10 w-10 rounded-lg" />
              <div className="space-y-1">
                <Skeleton className="h-6 w-12" />
                <Skeleton className="h-4 w-20" />
              </div>
            </div>
          </Card>
        ))}
      </div>

      {/* Tabs Skeleton */}
      <Skeleton className="h-10 w-80" />
      <Card>
        <CardContent className="p-6">
          <Skeleton className="h-64 w-full" />
        </CardContent>
      </Card>
    </div>
  );
}

function RunHistorySection({ modelId }: { modelId: string }) {
  const { data: runs, isLoading } = useDbtModelRuns(modelId);

  if (isLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <div key={i} className="flex items-center justify-between p-3 border rounded-lg">
            <div className="flex items-center gap-3">
              <Skeleton className="h-8 w-8 rounded-full" />
              <div className="space-y-1">
                <Skeleton className="h-4 w-32" />
                <Skeleton className="h-3 w-24" />
              </div>
            </div>
            <Skeleton className="h-5 w-16 rounded-full" />
          </div>
        ))}
      </div>
    );
  }

  if (!runs || runs.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <History className="h-12 w-12 mx-auto mb-3 opacity-50" />
        <p>No run history for this model</p>
        <p className="text-sm mt-1">
          Run history will appear here after dbt runs are executed.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {runs.slice(0, 10).map((run) => {
        const modelExecution = run.models_executed?.find(
          (m) => m.model_name === modelId
        );
        const status = modelExecution?.status || run.status;

        return (
          <Link
            key={run.id}
            href={`/settings/dbt?run=${run.id}`}
            className="flex items-center justify-between p-3 border rounded-lg hover:bg-muted/50 transition-colors"
          >
            <div className="flex items-center gap-3">
              <div
                className={`w-8 h-8 rounded-full flex items-center justify-center ${
                  status === "completed" || status === "success"
                    ? "bg-green-100"
                    : status === "failed" || status === "error"
                    ? "bg-red-100"
                    : "bg-gray-100"
                }`}
              >
                {status === "completed" || status === "success" ? (
                  <CheckCircle className="h-4 w-4 text-green-600" />
                ) : status === "failed" || status === "error" ? (
                  <XCircle className="h-4 w-4 text-red-600" />
                ) : (
                  <Clock className="h-4 w-4 text-gray-500" />
                )}
              </div>
              <div>
                <p className="font-medium text-sm">
                  Run {run.id.slice(0, 8)}
                </p>
                <p className="text-xs text-muted-foreground">
                  {formatDistanceToNow(new Date(run.created_at), {
                    addSuffix: true,
                  })}
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {modelExecution?.duration_seconds && (
                <span className="text-xs text-muted-foreground">
                  {modelExecution.duration_seconds.toFixed(1)}s
                </span>
              )}
              <Badge
                variant={
                  status === "completed" || status === "success"
                    ? "success"
                    : status === "failed" || status === "error"
                    ? "destructive"
                    : "secondary"
                }
                className="capitalize text-xs"
              >
                {status}
              </Badge>
            </div>
          </Link>
        );
      })}
    </div>
  );
}

export default function ModelDetailPage({ params }: PageProps) {
  const { modelId } = use(params);
  const { data: model, isLoading } = useDbtModel(modelId);
  const { data: allModels } = useDbtModels();

  const handleCopySQL = () => {
    if (model?.raw_sql) {
      navigator.clipboard.writeText(model.raw_sql);
      toast.success("SQL copied to clipboard");
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <Breadcrumb
          items={[
            { label: "Settings", href: "/settings" },
            { label: "dbt Projects", href: "/settings/dbt" },
            { label: "Models Catalog", href: "/settings/dbt/models" },
            { label: "Loading..." },
          ]}
        />
        <ModelDetailSkeleton />
      </div>
    );
  }

  if (!model) {
    return (
      <div className="space-y-6">
        <Breadcrumb
          items={[
            { label: "Settings", href: "/settings" },
            { label: "dbt Projects", href: "/settings/dbt" },
            { label: "Models Catalog", href: "/settings/dbt/models" },
            { label: "Not Found" },
          ]}
        />
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Database className="h-12 w-12 text-muted-foreground mb-4" />
            <CardTitle className="mb-2">Model Not Found</CardTitle>
            <CardDescription className="text-center mb-4">
              The requested dbt model could not be found.
            </CardDescription>
            <Link href="/settings/dbt/models">
              <Button>
                <ArrowLeft className="mr-2 h-4 w-4" />
                Back to Models Catalog
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  const matConfig = materializationConfig[model.materialization] || materializationConfig.table;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb
        items={[
          { label: "Settings", href: "/settings" },
          { label: "dbt Projects", href: "/settings/dbt" },
          { label: "Models Catalog", href: "/settings/dbt/models" },
          { label: model.name },
        ]}
      />

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="space-y-2">
          <div className="flex items-center gap-3">
            <div className={`p-2 rounded-lg ${matConfig.bg}`}>
              <Layers className={`h-6 w-6 ${matConfig.color}`} />
            </div>
            <h1 className="text-2xl font-bold tracking-tight">{model.name}</h1>
          </div>
          {model.description ? (
            <p className="text-muted-foreground max-w-2xl">{model.description}</p>
          ) : (
            <p className="text-muted-foreground/60 italic">No description available</p>
          )}
          <div className="flex items-center gap-2 flex-wrap">
            <Badge className={`${matConfig.color} ${matConfig.bg} border-0`}>
              {matConfig.label}
            </Badge>
            <Badge variant="outline" className="font-mono text-xs">
              <Database className="h-3 w-3 mr-1" />
              {model.schema}
            </Badge>
            {model.project_name && (
              <Badge variant="outline">
                <GitBranch className="h-3 w-3 mr-1" />
                {model.project_name}
              </Badge>
            )}
            {model.tags.map((tag) => (
              <Badge key={tag} variant="secondary">
                <Tag className="h-3 w-3 mr-1" />
                {tag}
              </Badge>
            ))}
          </div>
        </div>
        <Link href="/settings/dbt/models">
          <Button variant="outline">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Catalog
          </Button>
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Table className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{model.columns.length}</p>
              <p className="text-sm text-muted-foreground">Columns</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <CheckCircle className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{model.tests.length}</p>
              <p className="text-sm text-muted-foreground">Tests</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <GitBranch className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{model.depends_on.length}</p>
              <p className="text-sm text-muted-foreground">Upstream</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-orange-100 rounded-lg">
              <ExternalLink className="h-5 w-5 text-orange-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{model.referenced_by.length}</p>
              <p className="text-sm text-muted-foreground">Downstream</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Tabs */}
      <Tabs defaultValue="columns" className="space-y-4">
        <TabsList>
          <TabsTrigger value="columns" className="gap-2">
            <Table className="h-4 w-4" />
            Columns
          </TabsTrigger>
          <TabsTrigger value="tests" className="gap-2">
            <CheckCircle className="h-4 w-4" />
            Tests
          </TabsTrigger>
          <TabsTrigger value="dependencies" className="gap-2">
            <GitBranch className="h-4 w-4" />
            Dependencies
          </TabsTrigger>
          <TabsTrigger value="sql" className="gap-2">
            <FileCode className="h-4 w-4" />
            SQL
          </TabsTrigger>
          <TabsTrigger value="runs" className="gap-2">
            <History className="h-4 w-4" />
            Run History
          </TabsTrigger>
        </TabsList>

        <TabsContent value="columns">
          <ModelColumns columns={model.columns} />
        </TabsContent>

        <TabsContent value="tests">
          <ModelTests tests={model.tests} />
        </TabsContent>

        <TabsContent value="dependencies">
          <ModelDependencies model={model} allModels={allModels} />
        </TabsContent>

        <TabsContent value="sql">
          <Card>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2">
                  <FileCode className="h-5 w-5" />
                  Model SQL
                </CardTitle>
                {model.raw_sql && (
                  <Button variant="outline" size="sm" onClick={handleCopySQL}>
                    <Copy className="h-4 w-4 mr-2" />
                    Copy SQL
                  </Button>
                )}
              </div>
            </CardHeader>
            <CardContent>
              {model.raw_sql ? (
                <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm font-mono">
                  <code>{model.raw_sql}</code>
                </pre>
              ) : (
                <div className="text-center py-8 text-muted-foreground">
                  <FileCode className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>SQL not available</p>
                  <p className="text-sm mt-1">
                    The raw SQL for this model has not been stored.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="runs">
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <History className="h-5 w-5" />
                Run History
              </CardTitle>
              <CardDescription>
                Recent dbt runs that included this model
              </CardDescription>
            </CardHeader>
            <CardContent>
              <RunHistorySection modelId={model.id} />
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Metadata Footer */}
      <Card className="p-4">
        <div className="flex items-center justify-between text-sm text-muted-foreground">
          <div className="flex items-center gap-4">
            {model.path && (
              <span className="font-mono text-xs">
                <FileCode className="h-3 w-3 inline mr-1" />
                {model.path}
              </span>
            )}
            {model.unique_id && (
              <span className="font-mono text-xs">
                ID: {model.unique_id}
              </span>
            )}
          </div>
          <div className="flex items-center gap-4">
            <span>
              <Clock className="h-3 w-3 inline mr-1" />
              Updated {formatDistanceToNow(new Date(model.updated_at), { addSuffix: true })}
            </span>
          </div>
        </div>
      </Card>
    </div>
  );
}
