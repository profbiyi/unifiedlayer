"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useCreatePipeline } from "@/hooks/queries/usePipelines";
import { useSources } from "@/hooks/queries/useSources";
import { useDestinations } from "@/hooks/queries/useDestinations";
import { useCurrentUser } from "@/hooks/queries/useAuth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ArrowLeft, ArrowRight, Check, Database, HardDrive, Plus } from "lucide-react";
import Link from "next/link";
import { CreatePipelineRequest, TransformationConfig } from "@/types/pipeline";
import TransformationStep from "@/components/pipeline/TransformationStep";

const steps = [
  { id: 1, name: "Basic Info", description: "Name and description" },
  { id: 2, name: "Source", description: "Select data source" },
  { id: 3, name: "Destination", description: "Select destination" },
  { id: 4, name: "Settings", description: "Schedule & data handling" },
  { id: 5, name: "Transform", description: "Data transformations" },
  { id: 6, name: "Review", description: "Review and create" },
];

// Human-readable labels for write_mode and schema_contract
const WRITE_MODE_LABELS: Record<string, string> = {
  merge: "Merge (Delete-Insert)",
  upsert: "Upsert — Update or Insert",
  append: "Append — Always Add Rows",
  insert_only: "Deduplicated Append — Idempotent",
  scd2: "SCD2 — Historical Tracking",
  replace: "Replace (Full Reload)",
};

const SCHEMA_CONTRACT_LABELS: Record<string, string> = {
  evolve: "Evolve — Auto-adapt",
  freeze: "Freeze — Alert on change",
  discard_columns: "Discard New Columns",
  discard_rows: "Discard Rows with Unknown Fields",
};

export default function NewPipelinePage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(1);
  const [formData, setFormData] = useState<CreatePipelineRequest>({
    name: "",
    description: "",
    source_id: "",
    destination_id: "",
    schedule: "",
    is_active: true,
    write_mode: "merge",
    schema_contract: "evolve",
    config: {},
  });
  const [transformations, setTransformations] = useState<TransformationConfig>({});

  const { data: sources, isLoading: sourcesLoading } = useSources();
  const { data: destinations, isLoading: destinationsLoading } = useDestinations();
  const { data: currentUser } = useCurrentUser();
  const createPipeline = useCreatePipeline();

  const handleNext = () => {
    if (currentStep < steps.length) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    if (!currentUser) {
      return;
    }

    // Build config with transformations if any are configured
    const hasTransformations =
      (transformations.excluded_columns && transformations.excluded_columns.length > 0) ||
      (transformations.column_mapping && Object.keys(transformations.column_mapping).length > 0) ||
      (transformations.type_casts && Object.keys(transformations.type_casts).length > 0) ||
      (transformations.filters && transformations.filters.length > 0);

    const pipelineConfig = hasTransformations
      ? { transformations }
      : undefined;

    await createPipeline.mutateAsync({
      ...formData,
      config: pipelineConfig,
      organization_id: currentUser.organization_id,
    } as any);
    router.push("/pipelines");
  };

  const canProceed = () => {
    switch (currentStep) {
      case 1:
        return formData.name.trim() !== "";
      case 2:
        return formData.source_id !== "";
      case 3:
        return formData.destination_id !== "";
      case 4:
        return true; // Schedule + settings are optional / have defaults
      case 5:
        return true; // Transformations are optional
      case 6:
        return true;
      default:
        return false;
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Link href="/pipelines">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Pipelines
          </Button>
        </Link>
      </div>

      <div>
        <h1 className="text-3xl font-bold tracking-tight">Create Pipeline</h1>
        <p className="text-muted-foreground">
          Follow the steps to create a new data pipeline
        </p>
      </div>

      {/* Progress Steps */}
      <div className="flex items-center justify-between">
        {steps.map((step, index) => (
          <div key={step.id} className="flex items-center">
            <div className="flex flex-col items-center">
              <div
                className={`flex h-10 w-10 items-center justify-center rounded-full border-2 ${
                  currentStep > step.id
                    ? "border-primary bg-primary text-primary-foreground"
                    : currentStep === step.id
                    ? "border-primary text-primary"
                    : "border-muted text-muted-foreground"
                }`}
              >
                {currentStep > step.id ? (
                  <Check className="h-5 w-5" />
                ) : (
                  step.id
                )}
              </div>
              <div className="mt-2 text-center">
                <p className="text-sm font-medium">{step.name}</p>
                <p className="text-xs text-muted-foreground">
                  {step.description}
                </p>
              </div>
            </div>
            {index < steps.length - 1 && (
              <div
                className={`mx-4 h-0.5 w-16 ${
                  currentStep > step.id ? "bg-primary" : "bg-muted"
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <Card>
        <CardHeader>
          <CardTitle>{steps[currentStep - 1].name}</CardTitle>
          <CardDescription>
            {steps[currentStep - 1].description}
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Step 1: Basic Info */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Pipeline Name *</Label>
                <Input
                  id="name"
                  placeholder="e.g., MySQL to BigQuery Sync"
                  value={formData.name}
                  onChange={(e) =>
                    setFormData({ ...formData, name: e.target.value })
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Input
                  id="description"
                  placeholder="Describe what this pipeline does"
                  value={formData.description || ""}
                  onChange={(e) =>
                    setFormData({ ...formData, description: e.target.value })
                  }
                />
              </div>
            </div>
          )}

          {/* Step 2: Source */}
          {currentStep === 2 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="source">Data Source *</Label>
                {sourcesLoading ? (
                  <p className="text-sm text-muted-foreground">
                    Loading sources...
                  </p>
                ) : sources && sources.length > 0 ? (
                  <Select
                    value={formData.source_id}
                    onValueChange={(value) =>
                      setFormData({ ...formData, source_id: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select a source" />
                    </SelectTrigger>
                    <SelectContent>
                      {sources.map((source) => (
                        <SelectItem key={source.id} value={source.id}>
                          {source.name} ({source.type})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <div className="rounded-lg border-2 border-dashed border-muted p-6 text-center space-y-3">
                    <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                      <Database className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <h4 className="font-medium">No data sources yet</h4>
                      <p className="text-sm text-muted-foreground mt-1">
                        You need to connect a data source before creating a pipeline.
                        This is where your data will come from.
                      </p>
                    </div>
                    <Link href="/sources/new">
                      <Button className="mt-2">
                        <Plus className="mr-2 h-4 w-4" />
                        Add Your First Source
                      </Button>
                    </Link>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 3: Destination */}
          {currentStep === 3 && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="destination">Destination *</Label>
                {destinationsLoading ? (
                  <p className="text-sm text-muted-foreground">
                    Loading destinations...
                  </p>
                ) : destinations && destinations.length > 0 ? (
                  <Select
                    value={formData.destination_id}
                    onValueChange={(value) =>
                      setFormData({ ...formData, destination_id: value })
                    }
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Select a destination" />
                    </SelectTrigger>
                    <SelectContent>
                      {destinations.map((destination) => (
                        <SelectItem key={destination.id} value={destination.id}>
                          {destination.name} ({destination.type})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                ) : (
                  <div className="rounded-lg border-2 border-dashed border-muted p-6 text-center space-y-3">
                    <div className="mx-auto w-12 h-12 rounded-full bg-primary/10 flex items-center justify-center">
                      <HardDrive className="h-6 w-6 text-primary" />
                    </div>
                    <div>
                      <h4 className="font-medium">No destinations yet</h4>
                      <p className="text-sm text-muted-foreground mt-1">
                        You need to add a destination where your synced data will be stored.
                        We support PostgreSQL, BigQuery, Snowflake, and more.
                      </p>
                    </div>
                    <Link href="/destinations/new">
                      <Button className="mt-2">
                        <Plus className="mr-2 h-4 w-4" />
                        Add Your First Destination
                      </Button>
                    </Link>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Step 4: Settings (Schedule + Write Mode + Schema Contract) */}
          {currentStep === 4 && (
            <div className="space-y-6">
              {/* Run Frequency */}
              <div className="space-y-2">
                <Label htmlFor="frequency">Run Frequency</Label>
                <Select
                  value={
                    formData.schedule === "" ? "manual" :
                    formData.schedule === "*/15 * * * *" ? "15min" :
                    formData.schedule === "0 * * * *" ? "hourly" :
                    formData.schedule === "0 */6 * * *" ? "6hours" :
                    formData.schedule === "0 0 * * *" ? "daily" :
                    formData.schedule === "0 0 * * 0" ? "weekly" :
                    formData.schedule === "0 0 1 * *" ? "monthly" :
                    "custom"
                  }
                  onValueChange={(value) => {
                    const cronMap: Record<string, string> = {
                      manual: "",
                      "15min": "*/15 * * * *",
                      hourly: "0 * * * *",
                      "6hours": "0 */6 * * *",
                      daily: "0 0 * * *",
                      weekly: "0 0 * * 0",
                      monthly: "0 0 1 * *",
                      custom: formData.schedule || "",
                    };
                    setFormData({ ...formData, schedule: cronMap[value] });
                  }}
                >
                  <SelectTrigger>
                    <SelectValue placeholder="Select frequency" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="manual">Manual only</SelectItem>
                    <SelectItem value="15min">Every 15 minutes</SelectItem>
                    <SelectItem value="hourly">Every hour</SelectItem>
                    <SelectItem value="6hours">Every 6 hours</SelectItem>
                    <SelectItem value="daily">Daily (midnight)</SelectItem>
                    <SelectItem value="weekly">Weekly (Sunday midnight)</SelectItem>
                    <SelectItem value="monthly">Monthly (1st of month)</SelectItem>
                    <SelectItem value="custom">Custom (cron expression)</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Show cron input for custom or if value doesn't match presets */}
              {(formData.schedule !== "" &&
                !["*/15 * * * *", "0 * * * *", "0 */6 * * *", "0 0 * * *", "0 0 * * 0", "0 0 1 * *"].includes(formData.schedule || "")) && (
                <div className="space-y-2">
                  <Label htmlFor="schedule">Custom Cron Expression</Label>
                  <Input
                    id="schedule"
                    placeholder="e.g., 0 0 * * * (daily at midnight)"
                    value={formData.schedule || ""}
                    onChange={(e) =>
                      setFormData({ ...formData, schedule: e.target.value })
                    }
                  />
                  <p className="text-xs text-muted-foreground">
                    Format: minute hour day-of-month month day-of-week
                  </p>
                </div>
              )}

              {formData.schedule && (
                <div className="rounded-md bg-muted p-3">
                  <p className="text-sm">
                    <span className="font-medium">Schedule: </span>
                    <code className="text-xs bg-background px-1 py-0.5 rounded">{formData.schedule}</code>
                  </p>
                </div>
              )}

              <div className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id="is_active"
                  checked={formData.is_active}
                  onChange={(e) =>
                    setFormData({ ...formData, is_active: e.target.checked })
                  }
                  className="h-4 w-4"
                />
                <Label htmlFor="is_active" className="cursor-pointer">
                  Activate pipeline immediately
                </Label>
              </div>

              {/* Divider */}
              <div className="border-t pt-4">
                <p className="text-sm font-medium text-muted-foreground mb-4">Data Handling</p>

                {/* Write Mode */}
                <div className="space-y-2">
                  <Label htmlFor="write_mode">Write Mode</Label>
                  <Select
                    value={formData.write_mode || "merge"}
                    onValueChange={(value) =>
                      setFormData({
                        ...formData,
                        write_mode: value as CreatePipelineRequest["write_mode"],
                      })
                    }
                  >
                    <SelectTrigger id="write_mode">
                      <SelectValue placeholder="Select write mode" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="merge">
                        <div>
                          <div className="font-medium">Merge (Delete-Insert) — Recommended</div>
                          <div className="text-xs text-muted-foreground">
                            Delete matching rows, then insert. Safe default for most data.
                          </div>
                        </div>
                      </SelectItem>
                      <SelectItem value="upsert">
                        <div>
                          <div className="font-medium">Upsert — Update or Insert</div>
                          <div className="text-xs text-muted-foreground">
                            True upsert: update existing rows in-place, insert new. Best for dimension tables.
                          </div>
                        </div>
                      </SelectItem>
                      <SelectItem value="append">
                        <div>
                          <div className="font-medium">Append — Always Add Rows</div>
                          <div className="text-xs text-muted-foreground">
                            Always add new rows. Best for event logs and transactions.
                          </div>
                        </div>
                      </SelectItem>
                      <SelectItem value="insert_only">
                        <div>
                          <div className="font-medium">Deduplicated Append</div>
                          <div className="text-xs text-muted-foreground">
                            Idempotent append: only adds rows with new primary keys. Safe retries.
                          </div>
                        </div>
                      </SelectItem>
                      <SelectItem value="scd2">
                        <div>
                          <div className="font-medium">SCD2 — Historical Tracking</div>
                          <div className="text-xs text-muted-foreground">
                            Track all changes over time with valid_from/valid_to dates.
                            Great for compliance and auditing.
                          </div>
                        </div>
                      </SelectItem>
                      <SelectItem value="replace">
                        <div>
                          <div className="font-medium">Replace (Full Reload)</div>
                          <div className="text-xs text-muted-foreground">
                            Drop and reload every sync. Best for small reference tables.
                          </div>
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Controls how new data is combined with existing data in your warehouse.
                  </p>
                </div>

                {/* Schema Contract */}
                <div className="space-y-2 mt-4">
                  <Label htmlFor="schema_contract">Schema Contract</Label>
                  <Select
                    value={formData.schema_contract || "evolve"}
                    onValueChange={(value) =>
                      setFormData({
                        ...formData,
                        schema_contract: value as CreatePipelineRequest["schema_contract"],
                      })
                    }
                  >
                    <SelectTrigger id="schema_contract">
                      <SelectValue placeholder="Select schema contract" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="evolve">
                        <div>
                          <div className="font-medium">Evolve — Auto-adapt (Default)</div>
                          <div className="text-xs text-muted-foreground">
                            New columns from the source are automatically added.
                          </div>
                        </div>
                      </SelectItem>
                      <SelectItem value="freeze">
                        <div>
                          <div className="font-medium">Freeze — Alert on change</div>
                          <div className="text-xs text-muted-foreground">
                            Reject syncs if the source adds unexpected columns. Keeps your
                            schema stable.
                          </div>
                        </div>
                      </SelectItem>
                      <SelectItem value="discard_columns">
                        <div>
                          <div className="font-medium">Discard New Columns</div>
                          <div className="text-xs text-muted-foreground">
                            Ignore new columns from the source, load everything else.
                          </div>
                        </div>
                      </SelectItem>
                      <SelectItem value="discard_rows">
                        <div>
                          <div className="font-medium">Discard Rows with Unknown Fields</div>
                          <div className="text-xs text-muted-foreground">
                            Drop any rows that contain unexpected data types or fields.
                          </div>
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <p className="text-xs text-muted-foreground">
                    Controls how schema changes from your source are handled.
                  </p>
                </div>
              </div>
            </div>
          )}

          {/* Step 5: Transformations (Optional) */}
          {currentStep === 5 && (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                Optionally configure data transformations. You can rename columns,
                exclude columns, cast types, and filter rows. Skip this step if
                no transformations are needed.
              </p>
              <TransformationStep
                config={transformations}
                onUpdate={setTransformations}
              />
            </div>
          )}

          {/* Step 6: Review */}
          {currentStep === 6 && (
            <div className="space-y-4">
              <div className="rounded-lg border p-4 space-y-3">
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Name</p>
                  <p className="text-base">{formData.name}</p>
                </div>
                {formData.description && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Description</p>
                    <p className="text-base">{formData.description}</p>
                  </div>
                )}
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Source</p>
                  <p className="text-base">
                    {sources?.find((s) => s.id === formData.source_id)?.name ||
                      formData.source_id}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Destination</p>
                  <p className="text-base">
                    {destinations?.find((d) => d.id === formData.destination_id)
                      ?.name || formData.destination_id}
                  </p>
                </div>
                {formData.schedule && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Schedule</p>
                    <p className="text-base">{formData.schedule}</p>
                  </div>
                )}
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Write Mode</p>
                  <p className="text-base">
                    {WRITE_MODE_LABELS[formData.write_mode || "merge"]}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Schema Contract</p>
                  <p className="text-base">
                    {SCHEMA_CONTRACT_LABELS[formData.schema_contract || "evolve"]}
                  </p>
                </div>
                <div>
                  <p className="text-sm font-medium text-muted-foreground">Status</p>
                  <p className="text-base">
                    {formData.is_active ? "Active" : "Inactive"}
                  </p>
                </div>
                {((transformations.excluded_columns && transformations.excluded_columns.length > 0) ||
                  (transformations.column_mapping && Object.keys(transformations.column_mapping).length > 0) ||
                  (transformations.type_casts && Object.keys(transformations.type_casts).length > 0) ||
                  (transformations.filters && transformations.filters.length > 0)) && (
                  <div>
                    <p className="text-sm font-medium text-muted-foreground">Transformations</p>
                    <ul className="text-sm list-disc list-inside space-y-1 mt-1">
                      {transformations.excluded_columns && transformations.excluded_columns.length > 0 && (
                        <li>{transformations.excluded_columns.length} column(s) excluded</li>
                      )}
                      {transformations.column_mapping && Object.keys(transformations.column_mapping).length > 0 && (
                        <li>{Object.keys(transformations.column_mapping).length} column mapping(s)</li>
                      )}
                      {transformations.type_casts && Object.keys(transformations.type_casts).length > 0 && (
                        <li>{Object.keys(transformations.type_casts).length} type cast(s)</li>
                      )}
                      {transformations.filters && transformations.filters.length > 0 && (
                        <li>{transformations.filters.length} row filter(s)</li>
                      )}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Navigation Buttons */}
          <div className="flex justify-between pt-6">
            <Button
              variant="outline"
              onClick={handleBack}
              disabled={currentStep === 1}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back
            </Button>
            {currentStep < steps.length ? (
              <Button onClick={handleNext} disabled={!canProceed()}>
                Next
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            ) : (
              <Button
                onClick={handleSubmit}
                disabled={createPipeline.isPending || !canProceed()}
              >
                {createPipeline.isPending ? "Creating..." : "Create Pipeline"}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
