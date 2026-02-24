"use client";

import { useEffect, useState } from "react";
import { useSources, useDeleteSource } from "@/hooks/queries/useSources";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { SourceCardSkeleton } from "@/components/skeletons/SourceCardSkeleton";
import { EmptySources } from "@/components/feedback/EmptyStates";
import { ConnectionStatus } from "@/components/feedback/StatusIndicator";
import { SourceHelp } from "@/components/tooltips/QuickHelp";
import { AnimatedCard, SlideIn } from "@/components/feedback/MicroInteractions";
import {
  AutoDashboardNotification,
  useAutoDashboardNotification,
  type AutoDashboardNotificationData,
} from "@/components/dashboard/AutoDashboardNotification";
import { HealthBadge } from "@/components/health/HealthBadge";
import { Plus, Trash2, Database, Eye } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useRouter, useSearchParams } from "next/navigation";
import { motion } from "framer-motion";

export default function SourcesPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { data: sources, isLoading, error } = useSources();
  const deleteSource = useDeleteSource();

  // Auto-dashboard notification state
  const {
    notification: autoDashboardNotification,
    showNotification: showAutoDashboardNotification,
    dismissNotification: dismissAutoDashboardNotification,
  } = useAutoDashboardNotification();

  // Check for auto-dashboard notification from URL params or sessionStorage
  useEffect(() => {
    // Try to get notification data from sessionStorage (set by source creation)
    const storedNotification = sessionStorage.getItem("auto_dashboard_notification");
    if (storedNotification) {
      try {
        const notificationData = JSON.parse(storedNotification) as AutoDashboardNotificationData;
        showAutoDashboardNotification(notificationData);
        // Clear the stored notification
        sessionStorage.removeItem("auto_dashboard_notification");
      } catch (e) {
        console.error("Failed to parse auto-dashboard notification:", e);
      }
    }
  }, []);

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this source?")) {
      deleteSource.mutate(id);
    }
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-3xl font-bold tracking-tight">Data Sources</h1>
              <SourceHelp />
            </div>
            <p className="text-muted-foreground">
              Manage your data source connections
            </p>
          </div>
          <Button onClick={() => router.push("/sources/new")}>
            <Plus className="mr-2 h-4 w-4" />
            Add Source
          </Button>
        </div>
        <SourceCardSkeleton count={4} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-destructive">Error loading sources</p>
      </div>
    );
  }

  return (
    <>
      {/* Auto-Dashboard Notification */}
      <AutoDashboardNotification
        notification={autoDashboardNotification}
        onDismiss={dismissAutoDashboardNotification}
      />

      <div className="space-y-6">
        <SlideIn direction="down" duration={0.3}>
          <div className="flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2">
                <h1 className="text-3xl font-bold tracking-tight">Data Sources</h1>
                <SourceHelp />
              </div>
              <p className="text-muted-foreground">
                Manage your data source connections
              </p>
            </div>
            <Button onClick={() => router.push("/sources/new")}>
              <Plus className="mr-2 h-4 w-4" />
              Add Source
            </Button>
          </div>
        </SlideIn>

        {sources && sources.length === 0 ? (
          <Card>
            <EmptySources />
          </Card>
        ) : (
          <motion.div
            className="grid gap-4 md:grid-cols-2 lg:grid-cols-3"
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
            {sources?.map((source) => (
              <motion.div
                key={source.id}
                variants={{
                  hidden: { opacity: 0, y: 10 },
                  visible: { opacity: 1, y: 0 },
                }}
              >
                <AnimatedCard
                  className="cursor-pointer h-full"
                  onClick={() => router.push(`/sources/${source.id}`)}
                  hoverScale={1.02}
                  hoverY={-4}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 transition-colors">
                          <Database className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <CardTitle className="text-lg">{source.name}</CardTitle>
                          <Badge variant="outline" className="mt-1 capitalize">
                            {source.source_type?.replace('_', ' ') || source.type}
                          </Badge>
                        </div>
                      </div>
                      <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => router.push(`/sources/${source.id}`)}
                          title="View details"
                          className="transition-all hover:bg-primary/10"
                        >
                          <Eye className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="destructive"
                          size="sm"
                          onClick={() => handleDelete(source.id)}
                          disabled={deleteSource.isPending}
                          title="Delete source"
                          className="transition-all"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {source.description && (
                      <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                        {source.description}
                      </p>
                    )}
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <ConnectionStatus isConnected={true} />
                        <HealthBadge
                          resourceType="source"
                          resourceId={source.id}
                          size="sm"
                        />
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {formatDistanceToNow(new Date(source.created_at), {
                          addSuffix: true,
                        })}
                      </p>
                    </div>
                  </CardContent>
                </AnimatedCard>
              </motion.div>
            ))}
          </motion.div>
        )}
      </div>
    </>
  );
}
