"use client";

import { useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { usePipeline } from "@/hooks/queries/usePipelines";
import {
  useTransformations,
  useCreateTransformation,
  useUpdateTransformation,
  useDeleteTransformation,
  useDuplicateTransformation,
  useToggleTransformation,
  useReorderTransformations,
} from "@/hooks/queries/useTransformations";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  ArrowLeft,
  Plus,
  Loader2,
  Code2,
  Info,
  Sparkles,
  Database,
  Workflow,
} from "lucide-react";
import { TransformationList } from "@/components/transformations/TransformationList";
import { TransformationEditor } from "@/components/transformations/TransformationEditor";
import {
  SQLTransformation,
  CreateTransformationRequest,
  UpdateTransformationRequest,
} from "@/types/transformation";
import { Breadcrumb } from "@/components/ui/breadcrumb";

export default function TransformationsPage() {
  const params = useParams();
  const router = useRouter();
  const pipelineId = params.id as string;

  // Data fetching
  const { data: pipeline, isLoading: pipelineLoading } = usePipeline(pipelineId);
  const { data: transformations = [], isLoading: transformationsLoading } =
    useTransformations(pipelineId);

  // Mutations
  const createTransformation = useCreateTransformation(pipelineId);
  const updateTransformation = useUpdateTransformation(pipelineId);
  const deleteTransformation = useDeleteTransformation(pipelineId);
  const duplicateTransformation = useDuplicateTransformation(pipelineId);
  const toggleTransformation = useToggleTransformation(pipelineId);
  const reorderTransformations = useReorderTransformations(pipelineId);

  // Editor state
  const [isEditorOpen, setIsEditorOpen] = useState(false);
  const [editingTransformation, setEditingTransformation] = useState<
    SQLTransformation | undefined
  >(undefined);

  const handleCreate = useCallback(() => {
    setEditingTransformation(undefined);
    setIsEditorOpen(true);
  }, []);

  const handleEdit = useCallback((transformation: SQLTransformation) => {
    setEditingTransformation(transformation);
    setIsEditorOpen(true);
  }, []);

  const handleSave = useCallback(
    async (data: CreateTransformationRequest | UpdateTransformationRequest) => {
      if (editingTransformation) {
        await updateTransformation.mutateAsync({
          transformationId: editingTransformation.id,
          data,
        });
      } else {
        await createTransformation.mutateAsync(data as CreateTransformationRequest);
      }
      setIsEditorOpen(false);
      setEditingTransformation(undefined);
    },
    [editingTransformation, createTransformation, updateTransformation]
  );

  const handleDelete = useCallback(
    async (transformationId: string) => {
      await deleteTransformation.mutateAsync(transformationId);
    },
    [deleteTransformation]
  );

  const handleDuplicate = useCallback(
    async (transformationId: string) => {
      await duplicateTransformation.mutateAsync(transformationId);
    },
    [duplicateTransformation]
  );

  const handleToggle = useCallback(
    async (transformationId: string, isActive: boolean) => {
      await toggleTransformation.mutateAsync({ transformationId, isActive });
    },
    [toggleTransformation]
  );

  const handleReorder = useCallback(
    async (transformationIds: string[]) => {
      await reorderTransformations.mutateAsync({ transformation_ids: transformationIds });
    },
    [reorderTransformations]
  );

  const handleCloseEditor = useCallback(() => {
    setIsEditorOpen(false);
    setEditingTransformation(undefined);
  }, []);

  const isLoading = pipelineLoading || transformationsLoading;
  const isSaving =
    createTransformation.isPending || updateTransformation.isPending;

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!pipeline) {
    return (
      <div className="flex flex-col items-center justify-center h-64 space-y-4">
        <p className="text-destructive">Pipeline not found</p>
        <Link href="/pipelines">
          <Button variant="outline">Back to Pipelines</Button>
        </Link>
      </div>
    );
  }

  const activeCount = transformations.filter((t) => t.is_active).length;
  const totalCount = transformations.length;

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb
        items={[
          { label: "Pipelines", href: "/pipelines" },
          { label: pipeline.name, href: `/pipelines/${pipelineId}` },
          { label: "Transformations" },
        ]}
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href={`/pipelines/${pipelineId}`}>
            <Button variant="ghost" size="icon">
              <ArrowLeft className="h-4 w-4" />
            </Button>
          </Link>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold tracking-tight">
                SQL Transformations
              </h1>
              {totalCount > 0 && (
                <Badge variant="outline" className="font-mono">
                  {activeCount}/{totalCount} active
                </Badge>
              )}
            </div>
            <p className="text-muted-foreground mt-1">
              {pipeline.name} - Transform data after loading
            </p>
          </div>
        </div>
        <Button onClick={handleCreate}>
          <Plus className="mr-2 h-4 w-4" />
          Add Transformation
        </Button>
      </div>

      {/* Info Card */}
      {transformations.length === 0 && (
        <Card className="bg-gradient-to-r from-primary/5 to-primary/10 border-primary/20">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Sparkles className="h-5 w-5 text-primary" />
              Transform Your Data with SQL
            </CardTitle>
            <CardDescription>
              SQL transformations allow you to process, aggregate, and reshape your
              data after it lands in your destination.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid gap-4 md:grid-cols-3">
              <div className="flex items-start gap-3">
                <div className="rounded-lg bg-background p-2.5 shadow-sm">
                  <Database className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h4 className="font-medium text-sm">Data Aggregation</h4>
                  <p className="text-xs text-muted-foreground">
                    Create summary tables, calculate metrics, and group data
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="rounded-lg bg-background p-2.5 shadow-sm">
                  <Code2 className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h4 className="font-medium text-sm">Data Cleaning</h4>
                  <p className="text-xs text-muted-foreground">
                    Normalize values, handle nulls, and fix data quality issues
                  </p>
                </div>
              </div>
              <div className="flex items-start gap-3">
                <div className="rounded-lg bg-background p-2.5 shadow-sm">
                  <Workflow className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h4 className="font-medium text-sm">Data Modeling</h4>
                  <p className="text-xs text-muted-foreground">
                    Build dimensional models, fact tables, and derived datasets
                  </p>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Transformations List */}
      <TransformationList
        transformations={transformations}
        onEdit={handleEdit}
        onDelete={handleDelete}
        onDuplicate={handleDuplicate}
        onToggle={handleToggle}
        onReorder={handleReorder}
        isReordering={reorderTransformations.isPending}
      />

      {/* Execution Info */}
      {transformations.length > 0 && (
        <Card className="bg-muted/30">
          <CardContent className="py-4">
            <div className="flex items-start gap-3">
              <Info className="h-5 w-5 text-muted-foreground flex-shrink-0 mt-0.5" />
              <div className="space-y-1">
                <p className="text-sm font-medium">Execution Order</p>
                <p className="text-sm text-muted-foreground">
                  Transformations execute in order from 1 to {totalCount}. Drag and
                  drop cards to reorder them. Each transformation runs after the
                  previous one completes successfully.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Editor Modal */}
      <TransformationEditor
        pipelineId={pipelineId}
        transformation={editingTransformation}
        isOpen={isEditorOpen}
        onClose={handleCloseEditor}
        onSave={handleSave}
        isSaving={isSaving}
      />
    </div>
  );
}
