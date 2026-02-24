"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { useModel, useMaterializeModel, useDeleteModel } from "@/hooks/queries/useModels";
import { usePipeline } from "@/hooks/queries/usePipelines";
import { ModelSchema } from "@/components/models/ModelSchema";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { cn } from "@/lib/utils";
import {
  ArrowLeft,
  Boxes,
  Box,
  Grid3X3,
  Columns,
  CheckCircle,
  Sparkles,
  Database,
  Trash2,
  Loader2,
  Play,
  Copy,
  MessageSquareText,
  Brain,
  Code,
  ChevronDown,
  ChevronRight,
} from "lucide-react";
import Link from "next/link";
import { format, formatDistanceToNow } from "date-fns";
import { motion, AnimatePresence } from "framer-motion";
import { ModelLayer } from "@/types/models";

const layerConfig: Record<
  ModelLayer,
  { label: string; color: string; bgColor: string; icon: React.ReactNode; description: string }
> = {
  raw: {
    label: "Raw",
    color: "text-slate-600",
    bgColor: "bg-slate-100 dark:bg-slate-800",
    icon: <Columns className="h-4 w-4" />,
    description: "Unprocessed data directly from the source",
  },
  canonical: {
    label: "Canonical",
    color: "text-blue-600",
    bgColor: "bg-blue-100 dark:bg-blue-900/30",
    icon: <Grid3X3 className="h-4 w-4" />,
    description: "Cleaned and standardized data",
  },
  dimensional: {
    label: "Dimensional",
    color: "text-purple-600",
    bgColor: "bg-purple-100 dark:bg-purple-900/30",
    icon: <Boxes className="h-4 w-4" />,
    description: "Star schema optimized for analytics",
  },
};

function getModelIcon(name: string) {
  const nameLower = name.toLowerCase();
  if (nameLower.startsWith("fact_") || nameLower.includes("_fact")) {
    return <Box className="h-6 w-6 text-amber-500" />;
  }
  if (nameLower.startsWith("dim_") || nameLower.includes("_dim")) {
    return <Grid3X3 className="h-6 w-6 text-indigo-500" />;
  }
  return <Boxes className="h-6 w-6 text-primary" />;
}

export default function ModelDetailPage() {
  const params = useParams();
  const router = useRouter();
  const modelId = params.id as string;

  const { data: model, isLoading: modelLoading } = useModel(modelId);
  const { data: pipeline } = usePipeline(model?.pipeline_id || "");
  const materializeModel = useMaterializeModel();
  const deleteModel = useDeleteModel();

  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const [sqlExpanded, setSqlExpanded] = useState(true);
  const [questionsExpanded, setQuestionsExpanded] = useState(true);
  const [reasoningExpanded, setReasoningExpanded] = useState(false);

  const handleMaterialize = () => {
    materializeModel.mutate(modelId);
  };

  const handleDelete = () => {
    deleteModel.mutate(modelId, {
      onSuccess: () => {
        router.push("/models");
      },
    });
    setShowDeleteDialog(false);
  };

  const handleCopySQL = () => {
    if (model?.sql_definition) {
      navigator.clipboard.writeText(model.sql_definition);
    }
  };

  if (modelLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!model) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <p className="text-destructive">Model not found</p>
        <Link href="/models">
          <Button variant="outline">Back to Models</Button>
        </Link>
      </div>
    );
  }

  const layer = layerConfig[model.layer];

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb
        items={[
          { label: "Models", href: "/models" },
          { label: model.name },
        ]}
      />

      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-start gap-4">
          <Link href="/models">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div className="flex items-start gap-4">
            <div className="p-3 rounded-xl bg-muted">
              {getModelIcon(model.name)}
            </div>
            <div>
              <div className="flex items-center gap-3 flex-wrap">
                <h1 className="text-3xl font-bold tracking-tight">
                  {model.name}
                </h1>
                <Badge
                  variant="outline"
                  className={cn("flex items-center gap-1", layer.bgColor, layer.color)}
                >
                  {layer.icon}
                  {layer.label}
                </Badge>
                {model.is_materialized && (
                  <Badge variant="success" className="flex items-center gap-1">
                    <CheckCircle className="h-3 w-3" />
                    Materialized
                  </Badge>
                )}
                <Badge variant="secondary" className="flex items-center gap-1">
                  <Sparkles className="h-3 w-3" />
                  AI-Generated
                </Badge>
              </div>
              <p className="text-muted-foreground mt-1">{model.description}</p>
              {pipeline && (
                <p className="text-sm text-muted-foreground mt-2">
                  From pipeline:{" "}
                  <Link
                    href={`/pipelines/${pipeline.id}`}
                    className="text-primary hover:underline"
                  >
                    {pipeline.name}
                  </Link>
                </p>
              )}
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          {!model.is_materialized && (
            <Button
              onClick={handleMaterialize}
              disabled={materializeModel.isPending}
            >
              {materializeModel.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Materializing...
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Materialize
                </>
              )}
            </Button>
          )}
          <Button
            variant="destructive"
            onClick={() => setShowDeleteDialog(true)}
          >
            <Trash2 className="mr-2 h-4 w-4" />
            Delete
          </Button>
        </div>
      </div>

      {/* Content Grid */}
      <div className="grid gap-6 lg:grid-cols-2">
        {/* Left Column */}
        <div className="space-y-6">
          {/* SQL Definition */}
          <Card>
            <CardHeader className="pb-2">
              <Button
                variant="ghost"
                className="w-full justify-between p-0 h-auto hover:bg-transparent"
                onClick={() => setSqlExpanded(!sqlExpanded)}
              >
                <CardTitle className="text-base flex items-center gap-2">
                  <Code className="h-4 w-4" />
                  SQL Definition
                </CardTitle>
                {sqlExpanded ? (
                  <ChevronDown className="h-4 w-4 text-muted-foreground" />
                ) : (
                  <ChevronRight className="h-4 w-4 text-muted-foreground" />
                )}
              </Button>
            </CardHeader>
            <AnimatePresence>
              {sqlExpanded && (
                <motion.div
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2 }}
                >
                  <CardContent className="pt-2">
                    <div className="relative">
                      <pre className="bg-muted p-4 rounded-lg overflow-x-auto text-sm font-mono max-h-[400px] overflow-y-auto">
                        <code>{model.sql_definition}</code>
                      </pre>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="absolute top-2 right-2"
                        onClick={handleCopySQL}
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                    </div>
                  </CardContent>
                </motion.div>
              )}
            </AnimatePresence>
          </Card>

          {/* Business Questions */}
          {model.business_questions.length > 0 && (
            <Card>
              <CardHeader className="pb-2">
                <Button
                  variant="ghost"
                  className="w-full justify-between p-0 h-auto hover:bg-transparent"
                  onClick={() => setQuestionsExpanded(!questionsExpanded)}
                >
                  <CardTitle className="text-base flex items-center gap-2">
                    <MessageSquareText className="h-4 w-4" />
                    Business Questions
                    <Badge variant="secondary" className="ml-2">
                      {model.business_questions.length}
                    </Badge>
                  </CardTitle>
                  {questionsExpanded ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                </Button>
                <CardDescription>
                  Questions this model can help answer
                </CardDescription>
              </CardHeader>
              <AnimatePresence>
                {questionsExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <CardContent className="pt-0">
                      <ul className="space-y-2">
                        {model.business_questions.map((question, index) => (
                          <li
                            key={index}
                            className="flex items-start gap-2 p-2 rounded-md hover:bg-muted/50 transition-colors"
                          >
                            <span className="text-primary font-medium">
                              {index + 1}.
                            </span>
                            <span className="text-sm">{question}</span>
                          </li>
                        ))}
                      </ul>
                    </CardContent>
                  </motion.div>
                )}
              </AnimatePresence>
            </Card>
          )}

          {/* AI Reasoning */}
          {model.ai_reasoning && (
            <Card>
              <CardHeader className="pb-2">
                <Button
                  variant="ghost"
                  className="w-full justify-between p-0 h-auto hover:bg-transparent"
                  onClick={() => setReasoningExpanded(!reasoningExpanded)}
                >
                  <CardTitle className="text-base flex items-center gap-2">
                    <Brain className="h-4 w-4" />
                    AI Reasoning
                  </CardTitle>
                  {reasoningExpanded ? (
                    <ChevronDown className="h-4 w-4 text-muted-foreground" />
                  ) : (
                    <ChevronRight className="h-4 w-4 text-muted-foreground" />
                  )}
                </Button>
                <CardDescription>
                  How AI designed this model
                </CardDescription>
              </CardHeader>
              <AnimatePresence>
                {reasoningExpanded && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: "auto", opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.2 }}
                  >
                    <CardContent className="pt-0">
                      <div className="bg-muted/50 p-4 rounded-lg">
                        <p className="text-sm text-muted-foreground whitespace-pre-wrap">
                          {model.ai_reasoning}
                        </p>
                      </div>
                    </CardContent>
                  </motion.div>
                )}
              </AnimatePresence>
            </Card>
          )}
        </div>

        {/* Right Column */}
        <div className="space-y-6">
          {/* Model Schema */}
          <ModelSchema model={model} />

          {/* Source Tables */}
          {model.source_tables.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base flex items-center gap-2">
                  <Database className="h-4 w-4" />
                  Source Tables
                </CardTitle>
                <CardDescription>
                  Tables used to create this model
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {model.source_tables.map((table, index) => (
                    <Badge key={index} variant="outline" className="font-mono">
                      {table}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Metadata */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Metadata</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <p className="text-muted-foreground mb-1">Created</p>
                  <p className="font-medium">
                    {format(new Date(model.created_at), "PPP")}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatDistanceToNow(new Date(model.created_at), {
                      addSuffix: true,
                    })}
                  </p>
                </div>
                <div>
                  <p className="text-muted-foreground mb-1">Layer</p>
                  <p className="font-medium">{layer.label}</p>
                  <p className="text-xs text-muted-foreground">
                    {layer.description}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Delete Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Model</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete &quot;{model.name}&quot;? This
              action cannot be undone.
              {model.is_materialized && (
                <span className="block mt-2 text-warning">
                  Note: This will also remove the materialized view from your
                  destination.
                </span>
              )}
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowDeleteDialog(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteModel.isPending}
            >
              {deleteModel.isPending ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Deleting...
                </>
              ) : (
                "Delete"
              )}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
