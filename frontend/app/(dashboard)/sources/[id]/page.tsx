"use client";

import { useState } from "react";
import { useRouter, useParams } from "next/navigation";
import { useSource } from "@/hooks/queries/useSources";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  ArrowLeft,
  Database,
  Edit2,
  X,
  Eye,
  EyeOff,
} from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import Link from "next/link";

export default function SourceDetailPage() {
  const router = useRouter();
  const params = useParams();
  const sourceId = params.id as string;

  const { data: source, isLoading, error } = useSource(sourceId);
  const [isEditing, setIsEditing] = useState(false);
  const [showSensitive, setShowSensitive] = useState(false);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Loading source...</p>
      </div>
    );
  }

  if (error || !source) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-destructive">Error loading source</p>
        <Button onClick={() => router.push("/sources")}>
          <ArrowLeft className="mr-2 h-4 w-4" />
          Back to Sources
        </Button>
      </div>
    );
  }

  const maskSensitiveValue = (value: string) => {
    if (!value) return "";
    if (showSensitive) return value;
    return "•".repeat(Math.min(value.length, 12));
  };

  const sensitiveKeys = ["password", "api_key", "secret", "token", "bearer_token", "aws_secret_access_key"];

  const isSensitiveKey = (key: string) => {
    return sensitiveKeys.some((sk) => key.toLowerCase().includes(sk));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link href="/sources">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Sources
            </Button>
          </Link>
          <div className="flex items-center gap-3">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
              <Database className="h-6 w-6 text-primary" />
            </div>
            <div>
              <h1 className="text-3xl font-bold tracking-tight">
                {source.name}
              </h1>
              <Badge variant="outline" className="mt-1 capitalize">
                {source.source_type?.replace("_", " ")}
              </Badge>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={() => setShowSensitive(!showSensitive)}
          >
            {showSensitive ? (
              <>
                <EyeOff className="mr-2 h-4 w-4" />
                Hide Sensitive
              </>
            ) : (
              <>
                <Eye className="mr-2 h-4 w-4" />
                Show Sensitive
              </>
            )}
          </Button>
          {!isEditing && (
            <Button onClick={() => setIsEditing(true)}>
              <Edit2 className="mr-2 h-4 w-4" />
              Edit Source
            </Button>
          )}
        </div>
      </div>

      {/* Basic Information */}
      <Card>
        <CardHeader>
          <CardTitle>Basic Information</CardTitle>
          <CardDescription>
            General details about this data source
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label>Name</Label>
              {isEditing ? (
                <Input value={source.name} disabled />
              ) : (
                <p className="text-sm font-medium">{source.name}</p>
              )}
            </div>
            <div className="space-y-2">
              <Label>Source Type</Label>
              <p className="text-sm font-medium capitalize">
                {source.source_type?.replace("_", " ")}
              </p>
            </div>
          </div>

          <div className="space-y-2">
            <Label>Description</Label>
            {isEditing ? (
              <Textarea value={source.description || ""} disabled rows={2} />
            ) : (
              <p className="text-sm text-muted-foreground">
                {source.description || "No description provided"}
              </p>
            )}
          </div>

          <div className="grid grid-cols-3 gap-4 pt-4 border-t">
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Status</Label>
              <Badge variant={source.is_active ? "default" : "secondary"}>
                {source.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Created</Label>
              <p className="text-sm">
                {formatDistanceToNow(new Date(source.created_at), {
                  addSuffix: true,
                })}
              </p>
            </div>
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">
                Last Updated
              </Label>
              <p className="text-sm">
                {formatDistanceToNow(new Date(source.updated_at), {
                  addSuffix: true,
                })}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Connection Configuration */}
      <Card>
        <CardHeader>
          <CardTitle>Connection Configuration</CardTitle>
          <CardDescription>
            Connection details and credentials
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-4">
            {source.config && typeof source.config === "object" ? (
              Object.entries(source.config).map(([key, value]) => {
                const isSensitive = isSensitiveKey(key);
                const displayValue =
                  typeof value === "string"
                    ? isSensitive
                      ? maskSensitiveValue(value)
                      : value
                    : JSON.stringify(value, null, 2);

                return (
                  <div key={key} className="space-y-2">
                    <Label className="capitalize">
                      {key.replace(/_/g, " ")}
                      {isSensitive && (
                        <Badge variant="secondary" className="ml-2 text-xs">
                          Sensitive
                        </Badge>
                      )}
                    </Label>
                    {isEditing ? (
                      <Input
                        value={displayValue}
                        type={isSensitive && !showSensitive ? "password" : "text"}
                        disabled
                        className="font-mono text-sm"
                      />
                    ) : (
                      <div className="rounded-md border bg-muted/50 p-3">
                        <p className="font-mono text-sm break-all">
                          {displayValue}
                        </p>
                      </div>
                    )}
                  </div>
                );
              })
            ) : (
              <p className="text-sm text-muted-foreground">
                No configuration available
              </p>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Edit Mode Actions */}
      {isEditing && (
        <Card className="border-primary">
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <p className="text-sm text-muted-foreground">
                Editing is currently view-only. To update this source, please create a new one.
              </p>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setIsEditing(false)}>
                  <X className="mr-2 h-4 w-4" />
                  Cancel
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
