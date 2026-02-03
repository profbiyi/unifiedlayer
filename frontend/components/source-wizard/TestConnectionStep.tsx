"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { SourceWizardData } from "@/app/(dashboard)/sources/new/page";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  Database,
  AlertCircle,
  Info,
} from "lucide-react";
import api from "@/lib/api-client";

interface TestConnectionStepProps {
  data: SourceWizardData;
  onUpdate: (updates: Partial<SourceWizardData>) => void;
  onNext: () => void;
}

interface TestResult {
  success: boolean;
  message: string;
  error?: string;
  metadata?: {
    version?: string;
    database?: string;
    tables_count?: number;
    schemas?: string[];
    [key: string]: any;
  };
}

export default function TestConnectionStep({
  data,
  onUpdate,
  onNext,
}: TestConnectionStepProps) {
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);

  const handleTestConnection = async () => {
    setTesting(true);
    setTestResult(null);

    try {
      // Call backend to test connection
      const response = await api.post("/sources/discovery/test-connection", {
        source_type: data.source_type,
        config: data.config,
      });

      const result: TestResult = response.data;
      setTestResult(result);

      if (result.success) {
        onUpdate({
          connectionTested: true,
          connectionMetadata: result.metadata,
        });
      } else {
        onUpdate({
          connectionTested: false,
          connectionMetadata: undefined,
        });
      }
    } catch (error: any) {
      const errorMessage =
        error.response?.data?.detail || error.message || "Connection test failed";
      setTestResult({
        success: false,
        message: errorMessage,
      });
      onUpdate({
        connectionTested: false,
        connectionMetadata: undefined,
      });
    } finally {
      setTesting(false);
    }
  };

  return (
    <div className="space-y-6">
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Test your connection before proceeding. This ensures the credentials and
          configuration are correct.
        </AlertDescription>
      </Alert>

      <div className="flex flex-col items-center justify-center space-y-4 py-8">
        <Database className="h-16 w-16 text-muted-foreground" />
        <div className="text-center">
          <h3 className="text-lg font-semibold">Test Connection</h3>
          <p className="text-sm text-muted-foreground">
            Click the button below to verify your connection settings
          </p>
        </div>

        <Button
          onClick={handleTestConnection}
          disabled={testing}
          size="lg"
          className="mt-4"
        >
          {testing ? (
            <>
              <Loader2 className="mr-2 h-5 w-5 animate-spin" />
              Testing Connection...
            </>
          ) : (
            <>
              <Database className="mr-2 h-5 w-5" />
              Test Connection
            </>
          )}
        </Button>
      </div>

      {testResult && (
        <div className="space-y-4">
          <Alert
            variant={testResult.success ? "default" : "destructive"}
            className={
              testResult.success
                ? "border-green-500 bg-green-50 dark:bg-green-950"
                : ""
            }
          >
            {testResult.success ? (
              <CheckCircle2 className="h-4 w-4 text-green-600" />
            ) : (
              <XCircle className="h-4 w-4" />
            )}
            <AlertDescription>
              <div className="flex items-center justify-between">
                <span className="font-medium">
                  {testResult.success ? "Connection Successful!" : "Connection Failed"}
                </span>
                <Badge
                  variant={testResult.success ? "default" : "destructive"}
                  className={
                    testResult.success
                      ? "bg-green-600 hover:bg-green-700"
                      : ""
                  }
                >
                  {testResult.success ? "Success" : "Failed"}
                </Badge>
              </div>
              <p className="mt-2 text-sm">{testResult.message}</p>
            </AlertDescription>
          </Alert>

          {testResult.success && testResult.metadata && (
            <div className="rounded-lg border bg-card p-4">
              <h4 className="mb-3 font-semibold">Connection Details</h4>
              <dl className="grid grid-cols-2 gap-3 text-sm">
                {testResult.metadata.version && (
                  <>
                    <dt className="text-muted-foreground">Version:</dt>
                    <dd className="font-mono">{testResult.metadata.version}</dd>
                  </>
                )}
                {testResult.metadata.database && (
                  <>
                    <dt className="text-muted-foreground">Database:</dt>
                    <dd className="font-mono">{testResult.metadata.database}</dd>
                  </>
                )}
                {testResult.metadata.url && (
                  <>
                    <dt className="text-muted-foreground">URL:</dt>
                    <dd className="font-mono text-xs break-all">{testResult.metadata.url}</dd>
                  </>
                )}
                {testResult.metadata.status_code && (
                  <>
                    <dt className="text-muted-foreground">Status Code:</dt>
                    <dd className="font-semibold">{testResult.metadata.status_code}</dd>
                  </>
                )}
                {testResult.metadata.data_path && (
                  <>
                    <dt className="text-muted-foreground">Data Path:</dt>
                    <dd className="font-mono">{testResult.metadata.data_path}</dd>
                  </>
                )}
                {testResult.metadata.record_count !== undefined && (
                  <>
                    <dt className="text-muted-foreground">Records Found:</dt>
                    <dd className="font-semibold">{testResult.metadata.record_count}</dd>
                  </>
                )}
                {testResult.metadata.tables_count !== undefined && (
                  <>
                    <dt className="text-muted-foreground">Tables Found:</dt>
                    <dd className="font-semibold">
                      {testResult.metadata.tables_count}
                    </dd>
                  </>
                )}
                {testResult.metadata.schemas && Array.isArray(testResult.metadata.schemas) && (
                  <>
                    <dt className="text-muted-foreground">Schemas:</dt>
                    <dd className="font-mono">
                      {testResult.metadata.schemas.join(", ")}
                    </dd>
                  </>
                )}
              </dl>
            </div>
          )}

          {!testResult.success && (
            <>
              {testResult.error && (
                <Alert variant="destructive">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    <p className="font-medium mb-2">Error Details:</p>
                    <pre className="text-xs bg-destructive/10 p-2 rounded overflow-x-auto">
                      {testResult.error}
                    </pre>
                  </AlertDescription>
                </Alert>
              )}
              <Alert>
                <AlertCircle className="h-4 w-4" />
                <AlertDescription>
                  <p className="font-medium">Troubleshooting Tips:</p>
                  <ul className="mt-2 list-inside list-disc space-y-1 text-sm">
                    <li>Verify your credentials are correct</li>
                    <li>Check that the host/port are reachable</li>
                    <li>Ensure firewall rules allow the connection</li>
                    <li>Confirm the database/resource exists</li>
                    <li>Check if the database server is running</li>
                  </ul>
                </AlertDescription>
              </Alert>
            </>
          )}
        </div>
      )}
    </div>
  );
}
