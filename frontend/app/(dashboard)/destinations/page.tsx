"use client";

import { useDestinations, useDeleteDestination, useTestDestinationConnection } from "@/hooks/queries/useDestinations";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { DestinationCardSkeleton } from "@/components/skeletons/DestinationCardSkeleton";
import { EmptyDestinations } from "@/components/feedback/EmptyStates";
import { AnimatedCard, SlideIn } from "@/components/feedback/MicroInteractions";
import { Plus, Trash2, HardDrive, Zap, Loader2, Eye } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { motion } from "framer-motion";

export default function DestinationsPage() {
  const router = useRouter();
  const { data: destinations, isLoading, error } = useDestinations();
  const deleteDestination = useDeleteDestination();
  const testConnection = useTestDestinationConnection();
  const [testingId, setTestingId] = useState<string | null>(null);

  const handleDelete = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    if (confirm("Are you sure you want to delete this destination?")) {
      deleteDestination.mutate(id);
    }
  };

  const handleTestConnection = async (e: React.MouseEvent, id: string) => {
    e.stopPropagation();
    setTestingId(id);
    testConnection.mutate(id, {
      onSettled: () => setTestingId(null),
    });
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Destinations</h1>
            <p className="text-muted-foreground">
              Manage your data destination connections
            </p>
          </div>
          <Button onClick={() => router.push("/destinations/new")}>
            <Plus className="mr-2 h-4 w-4" />
            Add Destination
          </Button>
        </div>
        <DestinationCardSkeleton count={4} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-destructive">Error loading destinations</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <SlideIn direction="down" duration={0.3}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold tracking-tight">Destinations</h1>
            <p className="text-muted-foreground">
              Manage your data destination connections
            </p>
          </div>
          <Button onClick={() => router.push("/destinations/new")}>
            <Plus className="mr-2 h-4 w-4" />
            Add Destination
          </Button>
        </div>
      </SlideIn>

      {destinations && destinations.length === 0 ? (
        <Card>
          <EmptyDestinations />
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
          {destinations?.map((destination) => (
            <motion.div
              key={destination.id}
              variants={{
                hidden: { opacity: 0, y: 10 },
                visible: { opacity: 1, y: 0 },
              }}
            >
              <AnimatedCard
                className="cursor-pointer h-full"
                onClick={() => router.push(`/destinations/${destination.id}`)}
                hoverScale={1.02}
                hoverY={-4}
              >
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 transition-colors">
                        <HardDrive className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <CardTitle className="text-lg">
                          {destination.name}
                        </CardTitle>
                        <Badge variant="outline" className="mt-1 capitalize">
                          {destination.type?.replace('_', ' ')}
                        </Badge>
                      </div>
                    </div>
                    <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => handleTestConnection(e, destination.id)}
                        disabled={testingId === destination.id}
                        title="Test Connection"
                        className="transition-all hover:bg-primary/10"
                      >
                        {testingId === destination.id ? (
                          <Loader2 className="h-4 w-4 animate-spin" />
                        ) : (
                          <Zap className="h-4 w-4" />
                        )}
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => router.push(`/destinations/${destination.id}`)}
                        title="View details"
                        className="transition-all hover:bg-primary/10"
                      >
                        <Eye className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="destructive"
                        size="sm"
                        onClick={(e) => handleDelete(e, destination.id)}
                        disabled={deleteDestination.isPending}
                        title="Delete"
                        className="transition-all"
                      >
                        <Trash2 className="h-4 w-4" />
                      </Button>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  {destination.description && (
                    <p className="text-sm text-muted-foreground mb-3 line-clamp-2">
                      {destination.description}
                    </p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Created{" "}
                    {formatDistanceToNow(new Date(destination.created_at), {
                      addSuffix: true,
                    })}
                  </p>
                </CardContent>
              </AnimatedCard>
            </motion.div>
          ))}
        </motion.div>
      )}
    </div>
  );
}
