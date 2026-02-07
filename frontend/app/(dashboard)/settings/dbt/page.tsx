"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import DbtProjectCard from "@/components/dbt/DbtProjectCard";
import DbtProjectForm from "@/components/dbt/DbtProjectForm";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Plus, GitBranch, Loader2 } from "lucide-react";

export default function DbtSettingsPage() {
  const [isFormOpen, setIsFormOpen] = useState(false);
  const [editingProject, setEditingProject] = useState<any>(null);

  const { data: projects, isLoading } = useQuery({
    queryKey: ["dbt-projects"],
    queryFn: async () => {
      const { data } = await api.get("/dbt/projects");
      return data;
    },
  });

  const handleEdit = (project: any) => {
    setEditingProject(project);
    setIsFormOpen(true);
  };

  const handleFormClose = () => {
    setIsFormOpen(false);
    setEditingProject(null);
  };

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb
        items={[
          { label: "Settings", href: "/settings" },
          { label: "dbt Projects" },
        ]}
      />

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">dbt Projects</h1>
          <p className="text-muted-foreground">
            Manage your dbt projects for data transformations
          </p>
        </div>
        <Button onClick={() => setIsFormOpen(true)}>
          <Plus className="mr-2 h-4 w-4" />
          Add dbt Project
        </Button>
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
            <Button onClick={() => setIsFormOpen(true)}>
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
              onEdit={() => handleEdit(project)}
            />
          ))}
        </div>
      )}

      {/* Create/Edit Form Dialog */}
      <DbtProjectForm
        open={isFormOpen}
        onOpenChange={handleFormClose}
        project={editingProject}
      />
    </div>
  );
}
