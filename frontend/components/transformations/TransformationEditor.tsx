"use client";

import React, { useState, useCallback, useEffect } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Switch } from "@/components/ui/switch";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  Loader2,
  Play,
  Save,
  Code2,
  Table,
  Clock,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import {
  SQLTransformation,
  CreateTransformationRequest,
  UpdateTransformationRequest,
  WriteMode,
  SQLPreviewResult,
} from "@/types/transformation";
import { useTestSQL } from "@/hooks/queries/useTransformations";
import { SQLPreview } from "./SQLPreview";
import { cn } from "@/lib/utils";

// Dynamic import for Monaco Editor
import dynamic from "next/dynamic";

const MonacoEditor = dynamic(
  () => import("@monaco-editor/react").then((mod) => mod.default),
  {
    ssr: false,
    loading: () => (
      <div className="flex items-center justify-center h-[300px] border rounded-lg bg-muted/30">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    ),
  }
);

interface TransformationEditorProps {
  pipelineId: string;
  transformation?: SQLTransformation;
  isOpen: boolean;
  onClose: () => void;
  onSave: (
    data: CreateTransformationRequest | UpdateTransformationRequest
  ) => Promise<void>;
  isSaving: boolean;
}

const WRITE_MODES: { value: WriteMode; label: string; description: string }[] = [
  {
    value: "replace",
    label: "Replace",
    description: "Drop and recreate the target table with new data",
  },
  {
    value: "append",
    label: "Append",
    description: "Add new rows to the existing table",
  },
  {
    value: "merge",
    label: "Merge",
    description: "Update existing rows and insert new ones",
  },
];

const TIMEOUT_OPTIONS = [
  { value: 60, label: "1 minute" },
  { value: 300, label: "5 minutes" },
  { value: 600, label: "10 minutes" },
  { value: 1800, label: "30 minutes" },
  { value: 3600, label: "1 hour" },
  { value: 0, label: "No timeout" },
];

export function TransformationEditor({
  pipelineId,
  transformation,
  isOpen,
  onClose,
  onSave,
  isSaving,
}: TransformationEditorProps) {
  const isEditing = !!transformation;

  // Form state
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [sqlQuery, setSqlQuery] = useState("");
  const [targetTable, setTargetTable] = useState("");
  const [writeMode, setWriteMode] = useState<WriteMode>("replace");
  const [timeoutSeconds, setTimeoutSeconds] = useState(300);
  const [continueOnError, setContinueOnError] = useState(false);
  const [isActive, setIsActive] = useState(true);

  // UI state
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [previewResult, setPreviewResult] = useState<SQLPreviewResult | null>(null);

  // Test SQL mutation
  const testSQL = useTestSQL(pipelineId);

  // Reset form when transformation changes
  useEffect(() => {
    if (transformation) {
      setName(transformation.name);
      setDescription(transformation.description || "");
      setSqlQuery(transformation.sql_query);
      setTargetTable(transformation.target_table || "");
      setWriteMode(transformation.write_mode);
      setTimeoutSeconds(transformation.timeout_seconds);
      setContinueOnError(transformation.continue_on_error);
      setIsActive(transformation.is_active);
    } else {
      // Reset to defaults for new transformation
      setName("");
      setDescription("");
      setSqlQuery("SELECT * FROM source_table\nWHERE condition = 'value'");
      setTargetTable("");
      setWriteMode("replace");
      setTimeoutSeconds(300);
      setContinueOnError(false);
      setIsActive(true);
    }
    setPreviewResult(null);
    setShowAdvanced(false);
  }, [transformation, isOpen]);

  const handleTestSQL = useCallback(async () => {
    if (!sqlQuery.trim()) {
      return;
    }

    const result = await testSQL.mutateAsync({
      sql_query: sqlQuery,
      limit: 100,
    });
    setPreviewResult(result);
  }, [sqlQuery, testSQL]);

  const handleSave = useCallback(async () => {
    if (!name.trim() || !sqlQuery.trim()) {
      return;
    }

    const data: CreateTransformationRequest | UpdateTransformationRequest = {
      name: name.trim(),
      description: description.trim() || undefined,
      sql_query: sqlQuery,
      target_table: targetTable.trim() || undefined,
      write_mode: writeMode,
      timeout_seconds: timeoutSeconds,
      continue_on_error: continueOnError,
      is_active: isActive,
    };

    await onSave(data);
  }, [
    name,
    description,
    sqlQuery,
    targetTable,
    writeMode,
    timeoutSeconds,
    continueOnError,
    isActive,
    onSave,
  ]);

  const isValid = name.trim().length > 0 && sqlQuery.trim().length > 0;

  return (
    <Dialog open={isOpen} onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Code2 className="h-5 w-5" />
            {isEditing ? "Edit Transformation" : "New Transformation"}
          </DialogTitle>
          <DialogDescription>
            {isEditing
              ? "Update the SQL transformation settings."
              : "Create a new SQL transformation to process your data."}
          </DialogDescription>
        </DialogHeader>

        <div className="flex-1 overflow-y-auto space-y-6 py-4 pr-2">
          {/* Basic Info */}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="name">
                Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                placeholder="e.g., Calculate Monthly Revenue"
                value={name}
                onChange={(e) => setName(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="target-table">Target Table</Label>
              <Input
                id="target-table"
                placeholder="e.g., monthly_revenue"
                value={targetTable}
                onChange={(e) => setTargetTable(e.target.value)}
              />
              <p className="text-xs text-muted-foreground">
                Leave empty to run SQL as statement only
              </p>
            </div>
          </div>

          <div className="space-y-2">
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              placeholder="Describe what this transformation does..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={2}
            />
          </div>

          {/* SQL Editor */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <Label className="flex items-center gap-2">
                <Code2 className="h-4 w-4" />
                SQL Query <span className="text-destructive">*</span>
              </Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={handleTestSQL}
                disabled={!sqlQuery.trim() || testSQL.isPending}
              >
                {testSQL.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    Testing...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Test SQL
                  </>
                )}
              </Button>
            </div>
            <div className="rounded-lg border overflow-hidden">
              <MonacoEditor
                height="300px"
                language="sql"
                theme="vs-dark"
                value={sqlQuery}
                onChange={(value) => setSqlQuery(value || "")}
                options={{
                  minimap: { enabled: false },
                  fontSize: 14,
                  lineNumbers: "on",
                  scrollBeyondLastLine: false,
                  wordWrap: "on",
                  tabSize: 2,
                  automaticLayout: true,
                  padding: { top: 12, bottom: 12 },
                }}
              />
            </div>
          </div>

          {/* Write Mode */}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <Label>Write Mode</Label>
              <Select
                value={writeMode}
                onValueChange={(value) => setWriteMode(value as WriteMode)}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select write mode" />
                </SelectTrigger>
                <SelectContent>
                  {WRITE_MODES.map((mode) => (
                    <SelectItem key={mode.value} value={mode.value}>
                      <div className="flex flex-col">
                        <span>{mode.label}</span>
                      </div>
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              <p className="text-xs text-muted-foreground">
                {WRITE_MODES.find((m) => m.value === writeMode)?.description}
              </p>
            </div>

            <div className="space-y-2">
              <Label>Timeout</Label>
              <Select
                value={timeoutSeconds.toString()}
                onValueChange={(value) => setTimeoutSeconds(parseInt(value))}
              >
                <SelectTrigger>
                  <SelectValue placeholder="Select timeout" />
                </SelectTrigger>
                <SelectContent>
                  {TIMEOUT_OPTIONS.map((option) => (
                    <SelectItem key={option.value} value={option.value.toString()}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          </div>

          {/* Advanced Options */}
          <div className="space-y-3">
            <button
              type="button"
              onClick={() => setShowAdvanced(!showAdvanced)}
              className="flex items-center gap-2 text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              {showAdvanced ? (
                <ChevronUp className="h-4 w-4" />
              ) : (
                <ChevronDown className="h-4 w-4" />
              )}
              Advanced Options
            </button>

            {showAdvanced && (
              <div className="rounded-lg border p-4 space-y-4 bg-muted/30">
                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="continue-on-error" className="flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-warning" />
                      Continue on Error
                    </Label>
                    <p className="text-xs text-muted-foreground">
                      Pipeline will continue even if this transformation fails
                    </p>
                  </div>
                  <Switch
                    id="continue-on-error"
                    checked={continueOnError}
                    onCheckedChange={setContinueOnError}
                  />
                </div>

                <Separator />

                <div className="flex items-center justify-between">
                  <div className="space-y-0.5">
                    <Label htmlFor="is-active">Active</Label>
                    <p className="text-xs text-muted-foreground">
                      Inactive transformations will be skipped during pipeline runs
                    </p>
                  </div>
                  <Switch
                    id="is-active"
                    checked={isActive}
                    onCheckedChange={setIsActive}
                  />
                </div>
              </div>
            )}
          </div>

          {/* Preview Results */}
          <div className="space-y-2">
            <Label className="flex items-center gap-2">
              <Table className="h-4 w-4" />
              Preview Results
            </Label>
            <SQLPreview
              result={previewResult}
              isLoading={testSQL.isPending}
              error={testSQL.error?.message}
            />
          </div>
        </div>

        <Separator className="my-2" />

        <DialogFooter>
          <Button variant="outline" onClick={onClose} disabled={isSaving}>
            Cancel
          </Button>
          <Button onClick={handleSave} disabled={!isValid || isSaving}>
            {isSaving ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                {isEditing ? "Update" : "Create"} Transformation
              </>
            )}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

export default TransformationEditor;
