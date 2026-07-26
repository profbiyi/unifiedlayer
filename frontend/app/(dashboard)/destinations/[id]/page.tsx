"use client";

import { useEffect, useState } from "react";
import { useRouter, useParams } from "next/navigation";
import {
  useDestination,
  useUpdateDestination,
  useDeleteDestination,
  useTestDestinationConnection,
} from "@/hooks/queries/useDestinations";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ArrowLeft,
  HardDrive,
  Edit2,
  Loader2,
  Trash2,
  Zap,
  Eye,
  EyeOff,
} from "lucide-react";

// Config keys whose values are secrets — masked unless revealed.
const SENSITIVE = ["password", "secret", "key", "token", "credentials"];

function isSensitive(key: string): boolean {
  const k = key.toLowerCase();
  return SENSITIVE.some((s) => k.includes(s));
}

export default function DestinationDetailPage() {
  const router = useRouter();
  const params = useParams();
  const id = params.id as string;

  const { data: destination, isLoading, error } = useDestination(id);
  const update = useUpdateDestination();
  const del = useDeleteDestination();
  const test = useTestDestinationConnection();

  const [isEditing, setIsEditing] = useState(false);
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [showSecrets, setShowSecrets] = useState(false);

  useEffect(() => {
    if (destination) {
      setName(destination.name || "");
      setDescription(destination.description || "");
    }
  }, [destination]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error || !destination) {
    return (
      <div className="flex flex-col items-center justify-center h-64 gap-4">
        <p className="text-destructive">Destination not found</p>
        <Button onClick={() => router.push("/destinations")}>
          <ArrowLeft className="mr-2 h-4 w-4" /> Back to Destinations
        </Button>
      </div>
    );
  }

  const dest: any = destination;
  const isManaged = !!(dest.config && dest.config.managed);
  const config: Record<string, any> = dest.config || {};

  const handleSave = () => {
    update.mutate(
      { id, updates: { name, description } },
      { onSuccess: () => setIsEditing(false) }
    );
  };

  const handleDelete = () => {
    if (!confirm(`Delete destination "${dest.name}"? This cannot be undone.`)) return;
    del.mutate(id, { onSuccess: () => router.push("/destinations") });
  };

  return (
    <div className="space-y-6 max-w-3xl">
      <Button variant="ghost" size="sm" onClick={() => router.push("/destinations")}>
        <ArrowLeft className="mr-2 h-4 w-4" /> Destinations
      </Button>

      <div className="flex items-start justify-between gap-4">
        <div className="flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-emerald-600">
            <HardDrive className="h-5 w-5 text-white" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">{dest.name}</h1>
            <div className="flex items-center gap-2 mt-1">
              <Badge variant="outline">{dest.destination_type}</Badge>
              {isManaged && (
                <Badge className="bg-emerald-600 hover:bg-emerald-600">Managed</Badge>
              )}
              <Badge variant={dest.is_active ? "default" : "secondary"}>
                {dest.is_active ? "Active" : "Inactive"}
              </Badge>
            </div>
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={() => test.mutate(id)}
            disabled={test.isPending}
          >
            {test.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Zap className="mr-2 h-4 w-4" />
            )}
            Test
          </Button>
          {!isEditing && (
            <Button size="sm" onClick={() => setIsEditing(true)}>
              <Edit2 className="mr-2 h-4 w-4" /> Edit
            </Button>
          )}
        </div>
      </div>

      {/* Details / edit */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Details</CardTitle>
          <CardDescription>Name and description of this destination.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="name">Name</Label>
            {isEditing ? (
              <Input id="name" value={name} onChange={(e) => setName(e.target.value)} />
            ) : (
              <p className="text-sm">{dest.name}</p>
            )}
          </div>
          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            {isEditing ? (
              <Textarea
                id="description"
                rows={2}
                value={description}
                onChange={(e) => setDescription(e.target.value)}
              />
            ) : (
              <p className="text-sm text-muted-foreground">
                {dest.description || "—"}
              </p>
            )}
          </div>
          {isEditing && (
            <div className="flex gap-2 pt-1">
              <Button onClick={handleSave} disabled={update.isPending}>
                {update.isPending ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : null}
                Save
              </Button>
              <Button
                variant="outline"
                onClick={() => {
                  setIsEditing(false);
                  setName(dest.name || "");
                  setDescription(dest.description || "");
                }}
              >
                Cancel
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Connection config (read-only, secrets masked) */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle className="text-base">Connection</CardTitle>
            <CardDescription>
              {isManaged
                ? "Platform-managed — analytics and AI run on this destination."
                : "Configuration for this destination."}
            </CardDescription>
          </div>
          {Object.keys(config).some((k) => isSensitive(k)) && (
            <Button variant="ghost" size="sm" onClick={() => setShowSecrets((s) => !s)}>
              {showSecrets ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </Button>
          )}
        </CardHeader>
        <CardContent>
          {Object.keys(config).length === 0 ? (
            <p className="text-sm text-muted-foreground">No connection details.</p>
          ) : (
            <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm">
              {Object.entries(config).map(([k, v]) => (
                <div key={k} className="flex justify-between gap-4 border-b py-1.5">
                  <dt className="text-muted-foreground">{k}</dt>
                  <dd className="font-mono text-right truncate max-w-[60%]">
                    {isSensitive(k) && !showSecrets ? "••••••••" : String(v)}
                  </dd>
                </div>
              ))}
            </dl>
          )}
        </CardContent>
      </Card>

      {/* Danger zone */}
      <Card className="border-destructive/30">
        <CardHeader>
          <CardTitle className="text-base text-destructive">Danger zone</CardTitle>
          <CardDescription>Deleting a destination cannot be undone.</CardDescription>
        </CardHeader>
        <CardContent>
          <Button variant="destructive" onClick={handleDelete} disabled={del.isPending}>
            {del.isPending ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Trash2 className="mr-2 h-4 w-4" />
            )}
            Delete destination
          </Button>
        </CardContent>
      </Card>
    </div>
  );
}
