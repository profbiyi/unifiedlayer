"use client";

import { useDestinations, useDeleteDestination, useTestDestinationConnection } from "@/hooks/queries/useDestinations";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Plus, Trash2, HardDrive, Zap, Loader2 } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useRouter } from "next/navigation";
import { useState } from "react";

export default function DestinationsPage() {
  const router = useRouter();
  const { data: destinations, isLoading, error } = useDestinations();
  const deleteDestination = useDeleteDestination();
  const testConnection = useTestDestinationConnection();
  const [testingId, setTestingId] = useState<string | null>(null);

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this destination?")) {
      deleteDestination.mutate(id);
    }
  };

  const handleTestConnection = async (id: string) => {
    setTestingId(id);
    testConnection.mutate(id, {
      onSettled: () => setTestingId(null),
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Loading destinations...</p>
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

      {destinations && destinations.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No destinations yet</CardTitle>
            <CardDescription>
              Get started by adding your first data destination
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.push("/destinations/new")}>
              <Plus className="mr-2 h-4 w-4" />
              Add Your First Destination
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {destinations?.map((destination) => (
            <Card key={destination.id}>
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                      <HardDrive className="h-5 w-5 text-primary" />
                    </div>
                    <div>
                      <CardTitle className="text-lg">
                        {destination.name}
                      </CardTitle>
                      <Badge variant="outline" className="mt-1">
                        {destination.type}
                      </Badge>
                    </div>
                  </div>
                  <div className="flex gap-1">
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleTestConnection(destination.id)}
                      disabled={testingId === destination.id}
                      title="Test Connection"
                    >
                      {testingId === destination.id ? (
                        <Loader2 className="h-4 w-4 animate-spin" />
                      ) : (
                        <Zap className="h-4 w-4" />
                      )}
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(destination.id)}
                      disabled={deleteDestination.isPending}
                      title="Delete"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <p className="text-xs text-muted-foreground">
                  Created{" "}
                  {formatDistanceToNow(new Date(destination.created_at), {
                    addSuffix: true,
                  })}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
