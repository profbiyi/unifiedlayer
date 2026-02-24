"use client";

import { usePipelines, useDeletePipeline, useTriggerPipeline, useClonePipeline } from "@/hooks/queries/usePipelines";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import PipelineStatusBadge from "@/components/pipeline/pipeline-status-badge";
import { PipelineCardSkeleton } from "@/components/skeletons/PipelineCardSkeleton";
import { EmptyPipelines } from "@/components/feedback/EmptyStates";
import { PipelineStatusIndicator } from "@/components/feedback/StatusIndicator";
import { PipelineHelp } from "@/components/tooltips/QuickHelp";
import { AnimatedCard, SlideIn, StaggerList } from "@/components/feedback/MicroInteractions";
import { HealthBadge } from "@/components/health/HealthBadge";
import { Plus, Play, Trash2, Eye, Copy } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { format, formatDistanceToNow } from "date-fns";
import { motion } from "framer-motion";

export default function PipelinesPage() {
  const router = useRouter();
  const { data: pipelines, isLoading, error } = usePipelines();
  const deletePipeline = useDeletePipeline();
  const triggerPipeline = useTriggerPipeline();
  const clonePipeline = useClonePipeline();

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation(); // Prevent card click
    if (confirm("Are you sure you want to delete this pipeline?")) {
      deletePipeline.mutate(id);
    }
  };

  const handleTrigger = (e: React.MouseEvent, id: string) => {
    e.stopPropagation(); // Prevent card click
    triggerPipeline.mutate(id);
  };

  const handleClone = (e: React.MouseEvent, id: string) => {
    e.stopPropagation(); // Prevent card click
    clonePipeline.mutate(id);
  };

  const handleCardClick = (id: string) => {
    router.push(`/pipelines/${id}`);
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold tracking-tight">Pipelines</h1>
              <PipelineHelp />
            </div>
            <p className="text-muted-foreground">
              Manage your data integration pipelines
            </p>
          </div>
          <Link href="/pipelines/new">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Create Pipeline
            </Button>
          </Link>
        </div>
        <PipelineCardSkeleton count={4} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-destructive">Error loading pipelines</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SlideIn direction="down" duration={0.3}>
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold tracking-tight">Pipelines</h1>
              <PipelineHelp />
            </div>
            <p className="text-muted-foreground">
              Manage your data integration pipelines
            </p>
          </div>
          <Link href="/pipelines/new">
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Create Pipeline
            </Button>
          </Link>
        </div>
      </SlideIn>

      {pipelines && pipelines.length === 0 ? (
        <Card>
          <EmptyPipelines />
        </Card>
      ) : (
        <motion.div
          className="grid gap-4"
          initial="hidden"
          animate="visible"
          variants={{
            hidden: { opacity: 0 },
            visible: {
              opacity: 1,
              transition: {
                staggerChildren: 0.05,
                delayChildren: 0.1,
              },
            },
          }}
        >
          {pipelines?.map((pipeline, index) => (
            <motion.div
              key={pipeline.id}
              variants={{
                hidden: { opacity: 0, y: 10 },
                visible: { opacity: 1, y: 0 },
              }}
            >
              <AnimatedCard
                className="cursor-pointer hover:border-primary/50"
                onClick={() => handleCardClick(pipeline.id)}
                hoverScale={1.01}
                hoverY={-2}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="space-y-1">
                      <div className="flex items-center gap-3">
                        <CardTitle>{pipeline.name}</CardTitle>
                        <PipelineStatusIndicator
                          status={pipeline.is_active ? "active" : "paused"}
                          size="sm"
                        />
                        <HealthBadge
                          resourceType="pipeline"
                          resourceId={pipeline.id}
                          size="sm"
                        />
                      </div>
                      {pipeline.description && (
                        <CardDescription>{pipeline.description}</CardDescription>
                      )}
                      <div className="flex gap-4 text-sm text-muted-foreground">
                        <span>Source: {pipeline.source?.name || pipeline.source_id}</span>
                        <span>→</span>
                        <span>Destination: {pipeline.destination?.name || pipeline.destination_id}</span>
                      </div>
                      <p className="text-xs text-muted-foreground">
                        Created on {format(new Date(pipeline.created_at), "PPP")} ({formatDistanceToNow(new Date(pipeline.created_at), { addSuffix: true })})
                      </p>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => handleTrigger(e, pipeline.id)}
                        disabled={!pipeline.is_active || triggerPipeline.isPending}
                        title="Run pipeline"
                        className="transition-all hover:bg-primary hover:text-primary-foreground"
                      >
                        <Play className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => handleClone(e, pipeline.id)}
                        disabled={clonePipeline.isPending}
                        title="Duplicate pipeline"
                        className="transition-all hover:bg-secondary"
                      >
                        <Copy className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={(e) => handleDelete(e, pipeline.id)}
                        disabled={deletePipeline.isPending}
                        title="Delete pipeline"
                        className="transition-all"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
              </AnimatedCard>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
