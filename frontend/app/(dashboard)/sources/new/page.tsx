"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { ArrowLeft, ArrowRight, Check, Loader2 } from "lucide-react";
import Link from "next/link";

// Step Components
import BasicInfoStep from "@/components/source-wizard/BasicInfoStep";
import ConnectionDetailsStep from "@/components/source-wizard/ConnectionDetailsStep";
import TestConnectionStep from "@/components/source-wizard/TestConnectionStep";
import SchemaDiscoveryStep from "@/components/source-wizard/SchemaDiscoveryStep";
import SyncConfigStep from "@/components/source-wizard/SyncConfigStep";
import ReviewStep from "@/components/source-wizard/ReviewStep";

import { useCreateSource } from "@/hooks/queries/useSources";
import { useCurrentUser } from "@/hooks/queries/useAuth";

export interface SourceWizardData {
  // Basic Info
  name: string;
  description: string;
  source_type: string;

  // Connection Details
  config: Record<string, any>;

  // Connection Test
  connectionTested: boolean;
  connectionMetadata?: Record<string, any>;

  // Schema Discovery
  discoveredTables?: any[];
  selectedTables: Set<string>;
  tableConfigs: Record<string, {
    sync_mode: "full_refresh" | "incremental";
    cursor_field?: string;
    primary_key?: string[];
  }>;
}

const steps = [
  { id: 1, name: "Pick Source", description: "Choose connector" },
  { id: 2, name: "Credentials", description: "Connection details" },
  { id: 3, name: "Test", description: "Verify connection" },
  { id: 4, name: "Tables", description: "Select tables" },
  { id: 5, name: "Sync Mode", description: "Configure sync" },
  { id: 6, name: "Review", description: "Review & create" },
];

export default function NewSourceWizardPage() {
  const router = useRouter();
  const { data: currentUser } = useCurrentUser();
  const createSource = useCreateSource();

  const [currentStep, setCurrentStep] = useState(1);
  const [wizardData, setWizardData] = useState<SourceWizardData>({
    name: "",
    description: "",
    source_type: "",
    config: {},
    connectionTested: false,
    selectedTables: new Set(),
    tableConfigs: {},
  });

  const updateWizardData = (updates: Partial<SourceWizardData>) => {
    setWizardData((prev) => ({ ...prev, ...updates }));
  };

  const handleNext = () => {
    if (currentStep < steps.length) {
      // Skip schema discovery and sync config for file-based sources only
      const skipSchemaDiscovery = ["csv", "local", "xero", "open_banking", "hmrc_mtd", "http_file", "rest_api_declarative"].includes(wizardData.source_type);

      if (skipSchemaDiscovery && currentStep === 3) {
        // Jump directly to review after connection test
        setCurrentStep(6);
      } else if (skipSchemaDiscovery && (currentStep === 4 || currentStep === 5)) {
        // Skip these steps if somehow we land here
        setCurrentStep(6);
      } else {
        setCurrentStep(currentStep + 1);
      }
    }
  };

  const handleBack = () => {
    if (currentStep > 1) {
      // Skip schema discovery and sync config for file-based sources only
      const skipSchemaDiscovery = ["csv", "local", "xero", "open_banking", "hmrc_mtd", "http_file", "rest_api_declarative"].includes(wizardData.source_type);

      if (skipSchemaDiscovery && currentStep === 6) {
        // Jump back to connection test
        setCurrentStep(3);
      } else if (skipSchemaDiscovery && (currentStep === 4 || currentStep === 5)) {
        // Skip these steps if somehow we land here
        setCurrentStep(3);
      } else {
        setCurrentStep(currentStep - 1);
      }
    }
  };

  const canProceed = () => {
    const skipSchemaDiscovery = ["csv", "local", "xero", "open_banking", "hmrc_mtd", "http_file", "rest_api_declarative"].includes(wizardData.source_type);

    switch (currentStep) {
      case 1:
        return wizardData.name.trim() !== "" && wizardData.source_type !== "";
      case 2:
        return Object.keys(wizardData.config).length > 0;
      case 3:
        return wizardData.connectionTested;
      case 4:
        // Skip table selection requirement for file-based sources only
        return skipSchemaDiscovery || wizardData.selectedTables.size > 0;
      case 5:
        return true; // Sync config is optional
      case 6:
        return true;
      default:
        return false;
    }
  };

  const handleSubmit = async () => {
    if (!currentUser) {
      return;
    }

    const skipSchemaDiscovery = ["csv", "local", "xero", "open_banking", "hmrc_mtd", "http_file", "rest_api_declarative"].includes(wizardData.source_type);

    // Build final config with table selections (only for sources that support it)
    const finalConfig = skipSchemaDiscovery
      ? wizardData.config
      : {
          ...wizardData.config,
          tables: Array.from(wizardData.selectedTables).map((tableId) => {
            const syncConfig = wizardData.tableConfigs[tableId] || {
              sync_mode: "full_refresh",
            };
            return {
              table: tableId,
              ...syncConfig,
            };
          }),
        };

    createSource.mutate(
      {
        name: wizardData.name,
        description: wizardData.description || "",
        source_type: wizardData.source_type,
        config: finalConfig,
        organization_id: currentUser.organization_id,
      } as any,
      {
        onSuccess: (data) => {
          // Check if an auto-dashboard was created
          if (data.auto_dashboard) {
            // Store notification in sessionStorage for the sources page to display
            sessionStorage.setItem(
              "auto_dashboard_notification",
              JSON.stringify(data.auto_dashboard)
            );
          }
          // Navigate to sources page
          router.push("/sources");
        },
      }
    );
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 1:
        return (
          <BasicInfoStep
            data={wizardData}
            onUpdate={updateWizardData}
          />
        );
      case 2:
        return (
          <ConnectionDetailsStep
            data={wizardData}
            onUpdate={updateWizardData}
          />
        );
      case 3:
        return (
          <TestConnectionStep
            data={wizardData}
            onUpdate={updateWizardData}
            onNext={handleNext}
          />
        );
      case 4:
        return (
          <SchemaDiscoveryStep
            data={wizardData}
            onUpdate={updateWizardData}
          />
        );
      case 5:
        return (
          <SyncConfigStep
            data={wizardData}
            onUpdate={updateWizardData}
          />
        );
      case 6:
        return <ReviewStep data={wizardData} />;
      default:
        return null;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/sources">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="mr-2 h-4 w-4" />
            Back to Sources
          </Button>
        </Link>
      </div>

      <div>
        <h1 className="text-3xl font-bold tracking-tight">Add Data Source</h1>
        <p className="text-muted-foreground">
          Follow the steps to connect a new data source
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
          {renderStepContent()}

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
                disabled={createSource.isPending || !canProceed()}
              >
                {createSource.isPending ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating...
                  </>
                ) : (
                  <>
                    <Check className="mr-2 h-4 w-4" />
                    Create Source
                  </>
                )}
              </Button>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
