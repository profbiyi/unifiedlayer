"use client";

import { useState, useMemo } from "react";
import { useDbtModels, useDbtProjects } from "@/hooks/queries/useDbt";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardDescription, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import ModelCard from "@/components/dbt/ModelCard";
import { ModelCardSkeleton } from "@/components/skeletons/ModelCardSkeleton";
import {
  Search,
  Filter,
  Workflow,
  Database,
  Tag,
  Layers,
  X,
  RefreshCw,
  Loader2,
} from "lucide-react";
import { DbtMaterialization } from "@/types/dbt";

const materializationOptions: { value: DbtMaterialization | "all"; label: string }[] = [
  { value: "all", label: "All Materializations" },
  { value: "table", label: "Table" },
  { value: "view", label: "View" },
  { value: "incremental", label: "Incremental" },
  { value: "ephemeral", label: "Ephemeral" },
  { value: "snapshot", label: "Snapshot" },
  { value: "seed", label: "Seed" },
];

export default function DbtModelsCatalogPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTag, setSelectedTag] = useState<string>("all");
  const [selectedSchema, setSelectedSchema] = useState<string>("all");
  const [selectedMaterialization, setSelectedMaterialization] = useState<string>("all");
  const [selectedProject, setSelectedProject] = useState<string>("all");

  // Fetch projects for filtering
  const { data: projects } = useDbtProjects();

  // Fetch models with current filters
  const {
    data: models,
    isLoading,
    refetch,
    isFetching,
  } = useDbtModels({
    search: searchQuery || undefined,
    tag: selectedTag !== "all" ? selectedTag : undefined,
    schema: selectedSchema !== "all" ? selectedSchema : undefined,
    materialization: selectedMaterialization !== "all" ? selectedMaterialization : undefined,
    projectId: selectedProject !== "all" ? selectedProject : undefined,
  });

  // Extract unique tags and schemas for filter options
  const { uniqueTags, uniqueSchemas } = useMemo(() => {
    if (!models) return { uniqueTags: [], uniqueSchemas: [] };

    const tags = new Set<string>();
    const schemas = new Set<string>();

    models.forEach((model) => {
      model.tags.forEach((tag) => tags.add(tag));
      schemas.add(model.schema);
    });

    return {
      uniqueTags: Array.from(tags).sort(),
      uniqueSchemas: Array.from(schemas).sort(),
    };
  }, [models]);

  // Check if any filters are active
  const hasActiveFilters =
    searchQuery ||
    selectedTag !== "all" ||
    selectedSchema !== "all" ||
    selectedMaterialization !== "all" ||
    selectedProject !== "all";

  const clearFilters = () => {
    setSearchQuery("");
    setSelectedTag("all");
    setSelectedSchema("all");
    setSelectedMaterialization("all");
    setSelectedProject("all");
  };

  // Stats
  const stats = useMemo(() => {
    if (!models) return { total: 0, tables: 0, views: 0, incremental: 0 };
    return {
      total: models.length,
      tables: models.filter((m) => m.materialization === "table").length,
      views: models.filter((m) => m.materialization === "view").length,
      incremental: models.filter((m) => m.materialization === "incremental").length,
    };
  }, [models]);

  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb
        items={[
          { label: "Settings", href: "/settings" },
          { label: "dbt Projects", href: "/settings/dbt" },
          { label: "Models Catalog" },
        ]}
      />

      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">dbt Models Catalog</h1>
          <p className="text-muted-foreground">
            Browse and explore all dbt models from your parsed manifests
          </p>
        </div>
        <Button
          variant="outline"
          onClick={() => refetch()}
          disabled={isFetching}
        >
          {isFetching ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <RefreshCw className="mr-2 h-4 w-4" />
          )}
          Refresh
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Workflow className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.total}</p>
              <p className="text-sm text-muted-foreground">Total Models</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-blue-100 rounded-lg">
              <Database className="h-5 w-5 text-blue-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.tables}</p>
              <p className="text-sm text-muted-foreground">Tables</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-green-100 rounded-lg">
              <Database className="h-5 w-5 text-green-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.views}</p>
              <p className="text-sm text-muted-foreground">Views</p>
            </div>
          </div>
        </Card>
        <Card className="p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-purple-100 rounded-lg">
              <Layers className="h-5 w-5 text-purple-600" />
            </div>
            <div>
              <p className="text-2xl font-bold">{stats.incremental}</p>
              <p className="text-sm text-muted-foreground">Incremental</p>
            </div>
          </div>
        </Card>
      </div>

      {/* Filters */}
      <Card className="p-4">
        <div className="flex flex-col gap-4">
          <div className="flex items-center gap-2">
            <Filter className="h-4 w-4 text-muted-foreground" />
            <span className="font-medium">Filters</span>
            {hasActiveFilters && (
              <Button
                variant="ghost"
                size="sm"
                onClick={clearFilters}
                className="h-7 px-2 text-xs"
              >
                <X className="h-3 w-3 mr-1" />
                Clear all
              </Button>
            )}
          </div>

          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-5">
            {/* Search */}
            <div className="relative lg:col-span-2">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search models by name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10"
              />
            </div>

            {/* Project Filter */}
            <Select value={selectedProject} onValueChange={setSelectedProject}>
              <SelectTrigger>
                <SelectValue placeholder="All Projects" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Projects</SelectItem>
                {projects?.map((project) => (
                  <SelectItem key={project.id} value={project.id}>
                    {project.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Materialization Filter */}
            <Select
              value={selectedMaterialization}
              onValueChange={setSelectedMaterialization}
            >
              <SelectTrigger>
                <SelectValue placeholder="Materialization" />
              </SelectTrigger>
              <SelectContent>
                {materializationOptions.map((option) => (
                  <SelectItem key={option.value} value={option.value}>
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Schema Filter */}
            <Select value={selectedSchema} onValueChange={setSelectedSchema}>
              <SelectTrigger>
                <SelectValue placeholder="All Schemas" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Schemas</SelectItem>
                {uniqueSchemas.map((schema) => (
                  <SelectItem key={schema} value={schema}>
                    {schema}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          {/* Tags */}
          {uniqueTags.length > 0 && (
            <div className="flex items-center gap-2 flex-wrap">
              <Tag className="h-4 w-4 text-muted-foreground" />
              <Badge
                variant={selectedTag === "all" ? "default" : "outline"}
                className="cursor-pointer"
                onClick={() => setSelectedTag("all")}
              >
                All
              </Badge>
              {uniqueTags.slice(0, 10).map((tag) => (
                <Badge
                  key={tag}
                  variant={selectedTag === tag ? "default" : "outline"}
                  className="cursor-pointer"
                  onClick={() => setSelectedTag(tag)}
                >
                  {tag}
                </Badge>
              ))}
              {uniqueTags.length > 10 && (
                <span className="text-xs text-muted-foreground">
                  +{uniqueTags.length - 10} more
                </span>
              )}
            </div>
          )}
        </div>
      </Card>

      {/* Models Grid */}
      {isLoading ? (
        <ModelCardSkeleton count={6} />
      ) : !models || models.length === 0 ? (
        <Card>
          <CardContent className="flex flex-col items-center justify-center py-12">
            <Workflow className="h-12 w-12 text-muted-foreground mb-4" />
            <CardTitle className="mb-2">No Models Found</CardTitle>
            <CardDescription className="text-center max-w-md">
              {hasActiveFilters ? (
                <>
                  No models match your current filters.{" "}
                  <Button
                    variant="link"
                    className="p-0 h-auto"
                    onClick={clearFilters}
                  >
                    Clear filters
                  </Button>{" "}
                  to see all models.
                </>
              ) : (
                <>
                  No dbt models have been parsed yet. Add a dbt project and run it
                  to populate the models catalog.
                </>
              )}
            </CardDescription>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              Showing {models.length} model{models.length !== 1 ? "s" : ""}
            </p>
          </div>
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {models.map((model) => (
              <ModelCard key={model.id} model={model} />
            ))}
          </div>
        </>
      )}
    </div>
  );
}
