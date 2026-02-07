"use client";

import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { DbtProjectCard } from "@/components/dbt/DbtProjectCard";
import { DbtProjectForm } from "@/components/dbt/DbtProjectForm";
import { Plus, GitBranch, Loader2 } from "lucide-react";
import toast from "react-hot-toast";

export default function DbtSettingsPage() {
  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<any>(null);
  const queryClient = useQueryClient();

  const { data: projects, isLoading } = useQuery({
    queryKey: ["dbt-projects"],
    queryFn: async () => {
      const { data } = await api.get("/dbt/projects");
      return data;
    },
  });

  const createMutation = useMutation({
    mutationFn: async (projectData: any) => {
      const { data } = await api.post("/dbt/projects", projectData);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dbt-projects"] });
      setIsCreateOpen(false);
      toast.success("dbt project created successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to create project");
    },
  });

  const updateMutation = useMutation({
    mutationFn: async ({ id, data }: { id: string; data: any }) => {
      const response = await api.put(`/dbt/projects/${id}`, data);
      return response.data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dbt-projects"] });
      setEditingProject(null);
      toast.success("dbt project updated successfully");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to update project");
    },
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: string) => {
      await api.delete(`/dbt/projects/${id}`);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["dbt-projects"] });
      toast.success("dbt project deleted");
    },
    onError: (error: any) => {
      toast.error(error.response?.data?.detail || "Failed to delete project");
    },
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">dbt Projects</h1>
          <p className="text-muted-foreground">
            Manage your dbt projects for data transformations
          </p>
        </div>
        <Dialog open={isCreateOpen} onOpenChange={setIsCreateOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-2 h-4 w-4" />
              Add dbt Project
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Add dbt Project</DialogTitle>
              <DialogDescription>
                Connect a dbt project from a Git repository
              </DialogDescription>
            </DialogHeader>
            <DbtProjectForm
              onSubmit={(data) => createMutation.mutate(data)}
              isSubmitting={createMutation.isPending}
              onCancel={() => setIsCreateOpen(false)}
            />
          </DialogContent>
        </Dialog>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : projects?.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <GitBranch className="h-12 w-12 text-muted-foreground mb-4" />
            <CardTitle className="mb-2">No dbt Projects</CardTitle>
            <CardDescription className="text-center mb-4">
              Connect your first dbt project to run transformations after data loads
            </CardDescription>
            <Button onClick={() => setIsCreateOpen(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Add dbt Project
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {projects?.map((project: any) => (
            <DbtProjectCard
              key={project.id}
              project={project}
              onEdit={() => setEditingProject(project)}
              onDelete={() => deleteMutation.mutate(project.public_id)}
            />
          ))}
        </div>
      )}

      {/* Edit Dialog */}
      <Dialog open={!!editingProject} onOpenChange={() => setEditingProject(null)}>
        <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Edit dbt Project</DialogTitle>
            <DialogDescription>
              Update your dbt project configuration
            </DialogDescription>
          </DialogHeader>
          {editingProject && (
            <DbtProjectForm
              initialData={editingProject}
              onSubmit={(data) =>
                updateMutation.mutate({ id: editingProject.public_id, data })
              }
              isSubmitting={updateMutation.isPending}
              onCancel={() => setEditingProject(null)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
