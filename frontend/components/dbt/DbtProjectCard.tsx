"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  MoreVertical,
  Play,
  Pencil,
  Trash2,
  GitBranch,
  Clock,
  ExternalLink,
  Loader2,
} from "lucide-react";
import { DbtProject } from "@/types/dbt";
import { useDeleteDbtProject, useTriggerDbtRun } from "@/hooks/queries/useDbt";
import { formatDistanceToNow } from "date-fns";

interface DbtProjectCardProps {
  project: DbtProject;
  onEdit: (project: DbtProject) => void;
  onViewLogs?: (project: DbtProject) => void;
}

export default function DbtProjectCard({
  project,
  onEdit,
  onViewLogs,
}: DbtProjectCardProps) {
  const [showDeleteDialog, setShowDeleteDialog] = useState(false);
  const deleteProject = useDeleteDbtProject();
  const triggerRun = useTriggerDbtRun(project.id);

  const handleDelete = async () => {
    await deleteProject.mutateAsync(project.id);
    setShowDeleteDialog(false);
  };

  const handleRun = async () => {
    await triggerRun.mutateAsync({});
  };

  const getStatusBadge = () => {
    if (!project.last_run) {
      return <Badge variant="secondary">Never run</Badge>;
    }

    switch (project.last_run.status) {
      case "completed":
        return <Badge variant="success">Completed</Badge>;
      case "running":
        return <Badge variant="running">Running</Badge>;
      case "pending":
        return <Badge variant="info">Pending</Badge>;
      case "failed":
        return <Badge variant="destructive">Failed</Badge>;
      case "cancelled":
        return <Badge variant="warning">Cancelled</Badge>;
      default:
        return <Badge variant="secondary">{project.last_run.status}</Badge>;
    }
  };

  const maskGitUrl = (url: string) => {
    try {
      const parsed = new URL(url);
      // Show domain and repo name, mask the rest
      const pathParts = parsed.pathname.split("/").filter(Boolean);
      if (pathParts.length >= 2) {
        return `${parsed.hostname}/${pathParts[0]}/...`;
      }
      return parsed.hostname;
    } catch {
      // For non-URL formats (like SSH)
      const match = url.match(/[:/]([^/]+\/[^/]+?)(?:\.git)?$/);
      return match ? `.../${match[1]}` : "***";
    }
  };

  const isRunning =
    project.last_run?.status === "running" ||
    project.last_run?.status === "pending";

  return (
    <>
      <Card className="hover:shadow-md transition-shadow">
        <CardHeader className="pb-3">
          <div className="flex items-start justify-between">
            <div className="space-y-1 flex-1">
              <div className="flex items-center gap-2">
                <CardTitle className="text-lg">{project.name}</CardTitle>
                {!project.is_active && (
                  <Badge variant="outline" className="text-muted-foreground">
                    Disabled
                  </Badge>
                )}
              </div>
              {project.description && (
                <CardDescription className="line-clamp-2">
                  {project.description}
                </CardDescription>
              )}
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8">
                  <MoreVertical className="h-4 w-4" />
                  <span className="sr-only">Open menu</span>
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => onEdit(project)}>
                  <Pencil className="mr-2 h-4 w-4" />
                  Edit
                </DropdownMenuItem>
                {onViewLogs && project.last_run && (
                  <DropdownMenuItem onClick={() => onViewLogs(project)}>
                    <ExternalLink className="mr-2 h-4 w-4" />
                    View Logs
                  </DropdownMenuItem>
                )}
                <DropdownMenuSeparator />
                <DropdownMenuItem
                  onClick={() => setShowDeleteDialog(true)}
                  className="text-destructive focus:text-destructive"
                >
                  <Trash2 className="mr-2 h-4 w-4" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          {/* Repository Info */}
          <div className="space-y-2 text-sm">
            <div className="flex items-center gap-2 text-muted-foreground">
              <GitBranch className="h-4 w-4 shrink-0" />
              <span className="truncate" title={project.git_repo_url}>
                {maskGitUrl(project.git_repo_url)}
              </span>
              <span className="text-foreground font-medium">
                ({project.git_branch})
              </span>
            </div>

            {project.last_run && (
              <div className="flex items-center gap-2 text-muted-foreground">
                <Clock className="h-4 w-4 shrink-0" />
                <span>
                  Last run{" "}
                  {formatDistanceToNow(new Date(project.last_run.created_at), {
                    addSuffix: true,
                  })}
                </span>
              </div>
            )}
          </div>

          {/* Status and Actions */}
          <div className="flex items-center justify-between pt-2 border-t">
            <div>{getStatusBadge()}</div>
            <Button
              size="sm"
              onClick={handleRun}
              disabled={isRunning || triggerRun.isPending || !project.is_active}
            >
              {triggerRun.isPending || isRunning ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  {isRunning ? "Running..." : "Starting..."}
                </>
              ) : (
                <>
                  <Play className="mr-2 h-4 w-4" />
                  Run
                </>
              )}
            </Button>
          </div>

          {/* Models Preview */}
          {project.default_models && project.default_models.length > 0 && (
            <div className="pt-2 border-t">
              <p className="text-xs text-muted-foreground mb-1">Default models:</p>
              <div className="flex flex-wrap gap-1">
                {project.default_models.slice(0, 3).map((model) => (
                  <Badge key={model} variant="outline" className="text-xs">
                    {model}
                  </Badge>
                ))}
                {project.default_models.length > 3 && (
                  <Badge variant="outline" className="text-xs">
                    +{project.default_models.length - 3} more
                  </Badge>
                )}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Delete Confirmation Dialog */}
      <Dialog open={showDeleteDialog} onOpenChange={setShowDeleteDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete dbt Project</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete <strong>{project.name}</strong>?
              This action cannot be undone and will remove all run history.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowDeleteDialog(false)}
              disabled={deleteProject.isPending}
            >
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDelete}
              disabled={deleteProject.isPending}
            >
              {deleteProject.isPending ? (
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
    </>
  );
}
