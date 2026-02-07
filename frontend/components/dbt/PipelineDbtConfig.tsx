"use client";

import { useState, useEffect } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  ChevronDown,
  ChevronUp,
  Database,
  X,
  Plus,
  HelpCircle,
  AlertCircle,
} from "lucide-react";
import { DbtPipelineConfig, DbtProject } from "@/types/dbt";
import { useDbtProjects } from "@/hooks/queries/useDbt";

interface PipelineDbtConfigProps {
  value?: DbtPipelineConfig;
  onChange: (config: DbtPipelineConfig | undefined) => void;
  disabled?: boolean;
}

export default function PipelineDbtConfig({
  value,
  onChange,
  disabled = false,
}: PipelineDbtConfigProps) {
  const { data: projects, isLoading } = useDbtProjects();

  const [enabled, setEnabled] = useState(!!value);
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [modelInput, setModelInput] = useState("");

  // Local state for config
  const [projectId, setProjectId] = useState(value?.project_id || "");
  const [models, setModels] = useState<string[]>(value?.models || []);
  const [fullRefresh, setFullRefresh] = useState(value?.full_refresh || false);
  const [runOnSuccess, setRunOnSuccess] = useState(
    value?.run_on_success !== false
  );
  const [failPipelineOnError, setFailPipelineOnError] = useState(
    value?.fail_pipeline_on_error !== false
  );

  // Sync with external value changes
  useEffect(() => {
    if (value) {
      setEnabled(true);
      setProjectId(value.project_id);
      setModels(value.models);
      setFullRefresh(value.full_refresh);
      setRunOnSuccess(value.run_on_success);
      setFailPipelineOnError(value.fail_pipeline_on_error);
    } else {
      setEnabled(false);
    }
  }, [value]);

  // Update parent when values change
  useEffect(() => {
    if (enabled && projectId) {
      onChange({
        project_id: projectId,
        models,
        full_refresh: fullRefresh,
        run_on_success: runOnSuccess,
        fail_pipeline_on_error: failPipelineOnError,
      });
    } else if (!enabled) {
      onChange(undefined);
    }
  }, [enabled, projectId, models, fullRefresh, runOnSuccess, failPipelineOnError]);

  const handleAddModel = () => {
    const trimmed = modelInput.trim();
    if (trimmed && !models.includes(trimmed)) {
      setModels([...models, trimmed]);
      setModelInput("");
    }
  };

  const handleRemoveModel = (model: string) => {
    setModels(models.filter((m) => m !== model));
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddModel();
    }
  };

  const selectedProject = projects?.find((p) => p.id === projectId);
  const activeProjects = projects?.filter((p) => p.is_active) || [];

  if (!enabled) {
    return (
      <Card className="border-dashed">
        <CardContent className="py-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <Database className="h-5 w-5 text-muted-foreground" />
              <div>
                <p className="font-medium">dbt Transformation</p>
                <p className="text-sm text-muted-foreground">
                  Run dbt models after pipeline completion
                </p>
              </div>
            </div>
            <Button
              variant="outline"
              onClick={() => setEnabled(true)}
              disabled={disabled || activeProjects.length === 0}
            >
              <Plus className="mr-2 h-4 w-4" />
              Add dbt Step
            </Button>
          </div>
          {activeProjects.length === 0 && !isLoading && (
            <div className="mt-4 flex items-center gap-2 text-sm text-muted-foreground">
              <AlertCircle className="h-4 w-4" />
              No active dbt projects available.{" "}
              <a href="/settings/dbt" className="text-primary hover:underline">
                Create one first
              </a>
            </div>
          )}
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            <CardTitle className="text-lg">dbt Transformation</CardTitle>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => {
              setEnabled(false);
              setProjectId("");
              setModels([]);
            }}
            disabled={disabled}
          >
            <X className="h-4 w-4" />
          </Button>
        </div>
        <CardDescription>
          Configure dbt models to run after successful pipeline execution
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Project Selection */}
        <div className="space-y-2">
          <Label>dbt Project</Label>
          <Select
            value={projectId}
            onValueChange={setProjectId}
            disabled={disabled}
          >
            <SelectTrigger>
              <SelectValue placeholder="Select a dbt project" />
            </SelectTrigger>
            <SelectContent>
              {activeProjects.map((project: DbtProject) => (
                <SelectItem key={project.id} value={project.id}>
                  {project.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {selectedProject?.description && (
            <p className="text-xs text-muted-foreground">
              {selectedProject.description}
            </p>
          )}
        </div>

        {/* Model Selection */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <Label>Models to Run</Label>
            <span title="Use dbt selectors like 'staging.*', 'tag:daily', or specific model names">
              <HelpCircle className="h-3 w-3 text-muted-foreground" />
            </span>
          </div>
          <div className="flex gap-2">
            <Input
              placeholder="e.g., staging.customers or tag:hourly"
              value={modelInput}
              onChange={(e) => setModelInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={disabled}
            />
            <Button
              type="button"
              variant="outline"
              onClick={handleAddModel}
              disabled={disabled || !modelInput.trim()}
            >
              Add
            </Button>
          </div>
          {models.length > 0 ? (
            <div className="flex flex-wrap gap-2 mt-2">
              {models.map((model) => (
                <Badge
                  key={model}
                  variant="secondary"
                  className="flex items-center gap-1"
                >
                  {model}
                  <button
                    type="button"
                    onClick={() => handleRemoveModel(model)}
                    className="hover:text-destructive"
                    disabled={disabled}
                  >
                    <X className="h-3 w-3" />
                  </button>
                </Badge>
              ))}
            </div>
          ) : (
            <p className="text-xs text-muted-foreground">
              Leave empty to run all models, or add specific models/selectors
            </p>
          )}
        </div>

        {/* Quick Toggles */}
        <div className="space-y-3 pt-2">
          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="font-normal">Run on Success Only</Label>
              <p className="text-xs text-muted-foreground">
                Only run dbt when the pipeline completes successfully
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={runOnSuccess}
              onClick={() => setRunOnSuccess(!runOnSuccess)}
              disabled={disabled}
              className={`
                relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                ${runOnSuccess ? "bg-primary" : "bg-muted"}
                ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
              `}
            >
              <span
                className={`
                  inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                  ${runOnSuccess ? "translate-x-6" : "translate-x-1"}
                `}
              />
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div className="space-y-0.5">
              <Label className="font-normal">Fail Pipeline on dbt Error</Label>
              <p className="text-xs text-muted-foreground">
                Mark the pipeline as failed if dbt run fails
              </p>
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={failPipelineOnError}
              onClick={() => setFailPipelineOnError(!failPipelineOnError)}
              disabled={disabled}
              className={`
                relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                ${failPipelineOnError ? "bg-primary" : "bg-muted"}
                ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
              `}
            >
              <span
                className={`
                  inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                  ${failPipelineOnError ? "translate-x-6" : "translate-x-1"}
                `}
              />
            </button>
          </div>
        </div>

        {/* Advanced Options */}
        <div className="border-t pt-4">
          <button
            type="button"
            className="flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground"
            onClick={() => setShowAdvanced(!showAdvanced)}
          >
            {showAdvanced ? (
              <ChevronUp className="h-4 w-4" />
            ) : (
              <ChevronDown className="h-4 w-4" />
            )}
            Advanced Options
          </button>
          {showAdvanced && (
            <div className="mt-4 space-y-3">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label className="font-normal">Full Refresh</Label>
                  <p className="text-xs text-muted-foreground">
                    Rebuild all incremental models from scratch
                  </p>
                </div>
                <button
                  type="button"
                  role="switch"
                  aria-checked={fullRefresh}
                  onClick={() => setFullRefresh(!fullRefresh)}
                  disabled={disabled}
                  className={`
                    relative inline-flex h-6 w-11 items-center rounded-full transition-colors
                    ${fullRefresh ? "bg-primary" : "bg-muted"}
                    ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
                  `}
                >
                  <span
                    className={`
                      inline-block h-4 w-4 transform rounded-full bg-white transition-transform
                      ${fullRefresh ? "translate-x-6" : "translate-x-1"}
                    `}
                  />
                </button>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
