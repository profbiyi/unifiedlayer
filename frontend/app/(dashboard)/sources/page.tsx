"use client";

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
import { Plus, Trash2, Database, Eye } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { useRouter } from "next/navigation";

export default function SourcesPage() {
  const router = useRouter();
  const { data: sources, isLoading, error } = useSources();
  const deleteSource = useDeleteSource();

  const handleDelete = async (id: string) => {
    if (confirm("Are you sure you want to delete this source?")) {
      deleteSource.mutate(id);
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Loading sources...</p>
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
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Data Sources</h1>
          <p className="text-muted-foreground">
            Manage your data source connections
          </p>
        </div>
        <Button onClick={() => router.push("/sources/new")}>
          <Plus className="mr-2 h-4 w-4" />
          Add Source
        </Button>
      </div>

      {sources && sources.length === 0 ? (
        <Card>
          <CardHeader>
            <CardTitle>No sources yet</CardTitle>
            <CardDescription>
              Get started by adding your first data source
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button onClick={() => router.push("/sources/new")}>
              <Plus className="mr-2 h-4 w-4" />
              Add Your First Source
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {sources?.map((source) => (
            <Card
              key={source.id}
              className="cursor-pointer transition-all hover:shadow-lg"
              onClick={() => router.push(`/sources/${source.id}`)}
            >
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
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
                    >
                      <Eye className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="destructive"
                      size="sm"
                      onClick={() => handleDelete(source.id)}
                      disabled={deleteSource.isPending}
                      title="Delete source"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {source.description && (
                  <p className="text-sm text-muted-foreground mb-2 line-clamp-2">
                    {source.description}
                  </p>
                )}
                <p className="text-xs text-muted-foreground">
                  Created{" "}
                  {formatDistanceToNow(new Date(source.created_at), {
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
