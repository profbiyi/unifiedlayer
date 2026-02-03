"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { ArrowLeft, Check, Zap, Loader2, CheckCircle, XCircle } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCreateDestination } from "@/hooks/queries/useDestinations";
import { useCurrentUser } from "@/hooks/queries/useAuth";
import toast from "react-hot-toast";
import api from "@/lib/api-client";

const DESTINATION_TYPES = [
  { value: "postgres", label: "PostgreSQL", icon: "🐘" },
  { value: "duckdb", label: "DuckDB", icon: "🦆" },
  { value: "bigquery", label: "BigQuery", icon: "📊" },
  { value: "snowflake", label: "Snowflake", icon: "❄️" },
  { value: "redshift", label: "Redshift", icon: "🔴" },
  { value: "s3", label: "Amazon S3", icon: "☁️" },
  { value: "gcs", label: "Google Cloud Storage", icon: "☁️" },
  { value: "azure_blob", label: "Azure Blob Storage", icon: "☁️" },
];

export default function NewDestinationPage() {
  const router = useRouter();
  const [selectedType, setSelectedType] = useState("");
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const createDestination = useCreateDestination();
  const { data: currentUser } = useCurrentUser();
  const { register, handleSubmit, getValues, formState: { errors } } = useForm();

  const buildConfig = (data: any) => {
    const config: any = {};

    if (selectedType === "postgres") {
      config.host = data.host;
      config.port = parseInt(data.port) || 5432;
      config.database = data.database;
      config.username = data.username;
      config.password = data.password;
    } else if (selectedType === "bigquery") {
      config.project_id = data.project_id;
      config.dataset_name = data.dataset;
      config.credentials_json = data.credentials;
    } else if (selectedType === "snowflake") {
      config.account = data.account;
      config.host = data.account;
      config.warehouse = data.warehouse;
      config.database = data.database;
      config.schema = data.schema;
      config.username = data.username;
      config.password = data.password;
      config.dataset_name = data.schema;
      if (data.role) {
        config.role = data.role;
      }
    } else if (selectedType === "s3") {
      config.bucket_url = `s3://${data.bucket}`;
      config.aws_access_key_id = data.access_key;
      config.aws_secret_access_key = data.secret_key;
      if (data.region) {
        config.region = data.region;
      }
    }

    return config;
  };

  const handleTestConnection = async () => {
    const data = getValues();
    const config = buildConfig(data);

    if (Object.keys(config).length === 0) {
      toast.error("Please fill in the connection details first");
      return;
    }

    setIsTesting(true);
    setTestResult(null);

    try {
      const response = await api.post("/destinations/discovery/test-connection", {
        destination_type: selectedType,
        config: config,
      });

      setTestResult({
        success: response.data.success,
        message: response.data.message,
      });

      if (response.data.success) {
        toast.success(response.data.message);
      } else {
        toast.error(response.data.message);
      }
    } catch (error: any) {
      const message = error.response?.data?.detail || error.response?.data?.message || "Connection test failed";
      setTestResult({
        success: false,
        message: message,
      });
      toast.error(message);
    } finally {
      setIsTesting(false);
    }
  };

  const onSubmit = async (data: any) => {
    if (!selectedType) {
      toast.error("Please select a destination type");
      return;
    }

    if (!currentUser) {
      toast.error("User not authenticated");
      return;
    }

    const config = buildConfig(data);

    createDestination.mutate({
      name: data.name,
      description: data.description || "",
      destination_type: selectedType,
      config: config,
      organization_id: currentUser.organization_id,
    } as any, {
      onSuccess: () => {
        router.push("/destinations");
      },
    });
  };

  const renderConfigFields = () => {
    if (!selectedType) return null;

    if (selectedType === "postgres") {
      return (
        <>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="host">Host *</Label>
              <Input
                id="host"
                placeholder="localhost"
                {...register("host", { required: true })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="port">Port *</Label>
              <Input
                id="port"
                type="number"
                placeholder="5432"
                {...register("port", { required: true })}
              />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="database">Database *</Label>
            <Input
              id="database"
              placeholder="my_warehouse"
              {...register("database", { required: true })}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username *</Label>
              <Input
                id="username"
                placeholder="postgres"
                {...register("username", { required: true })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password *</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                {...register("password", { required: true })}
              />
            </div>
          </div>
        </>
      );
    }

    if (selectedType === "bigquery") {
      return (
        <>
          <div className="space-y-2">
            <Label htmlFor="project_id">Project ID *</Label>
            <Input
              id="project_id"
              placeholder="my-project-123"
              {...register("project_id", { required: true })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="dataset">Dataset *</Label>
            <Input
              id="dataset"
              placeholder="my_dataset"
              {...register("dataset", { required: true })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="credentials">Service Account JSON *</Label>
            <Textarea
              id="credentials"
              placeholder='{"type": "service_account", ...}'
              rows={4}
              {...register("credentials", { required: true })}
            />
            <p className="text-xs text-muted-foreground">
              Paste your Google Cloud service account JSON key
            </p>
          </div>
        </>
      );
    }

    if (selectedType === "snowflake") {
      return (
        <>
          <div className="space-y-2">
            <Label htmlFor="account">Account Identifier *</Label>
            <Input
              id="account"
              placeholder="xy12345.us-east-1"
              {...register("account", { required: true })}
            />
            <p className="text-xs text-muted-foreground">
              Your Snowflake account identifier (e.g., xy12345.us-east-1 or xy12345.us-east-1.aws)
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="warehouse">Warehouse *</Label>
              <Input
                id="warehouse"
                placeholder="COMPUTE_WH"
                {...register("warehouse", { required: true })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Input
                id="role"
                placeholder="ACCOUNTADMIN"
                {...register("role")}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="database">Database *</Label>
              <Input
                id="database"
                placeholder="MY_DATABASE"
                {...register("database", { required: true })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="schema">Schema *</Label>
              <Input
                id="schema"
                placeholder="PUBLIC"
                {...register("schema", { required: true })}
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username *</Label>
              <Input
                id="username"
                placeholder="your_username"
                {...register("username", { required: true })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password *</Label>
              <Input
                id="password"
                type="password"
                placeholder="••••••••"
                {...register("password", { required: true })}
              />
            </div>
          </div>
        </>
      );
    }

    if (selectedType === "s3") {
      return (
        <>
          <div className="space-y-2">
            <Label htmlFor="bucket">Bucket Name *</Label>
            <Input
              id="bucket"
              placeholder="my-data-warehouse"
              {...register("bucket", { required: true })}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="region">Region *</Label>
            <Input
              id="region"
              placeholder="us-east-1"
              {...register("region", { required: true })}
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="access_key">Access Key *</Label>
              <Input
                id="access_key"
                placeholder="AKIA..."
                {...register("access_key", { required: true })}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="secret_key">Secret Key *</Label>
              <Input
                id="secret_key"
                type="password"
                placeholder="••••••••"
                {...register("secret_key", { required: true })}
              />
            </div>
          </div>
        </>
      );
    }

    return (
      <div className="text-sm text-muted-foreground">
        Configuration for {DESTINATION_TYPES.find(t => t.value === selectedType)?.label} coming soon!
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button
          variant="ghost"
          size="icon"
          onClick={() => router.back()}
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Add Destination</h1>
          <p className="text-muted-foreground">
            Connect a new data destination to your platform
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)}>
        <Card>
          <CardHeader>
            <CardTitle>Destination Details</CardTitle>
            <CardDescription>
              Enter the details for your new data destination
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Basic Info */}
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="name">Destination Name *</Label>
                <Input
                  id="name"
                  placeholder="My Data Warehouse"
                  {...register("name", { required: true })}
                />
                {errors.name && (
                  <p className="text-sm text-destructive">Name is required</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea
                  id="description"
                  placeholder="Optional description of this destination"
                  {...register("description")}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="destination_type">Destination Type *</Label>
                <Select value={selectedType} onValueChange={setSelectedType}>
                  <SelectTrigger>
                    <SelectValue placeholder="Select destination type" />
                  </SelectTrigger>
                  <SelectContent>
                    {DESTINATION_TYPES.map((type) => (
                      <SelectItem key={type.value} value={type.value}>
                        {type.icon} {type.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>

            {/* Connection Config */}
            {selectedType && (
              <div className="space-y-4 pt-4 border-t">
                <h3 className="font-semibold">Connection Configuration</h3>
                {renderConfigFields()}

                {/* Test Connection */}
                <div className="pt-4 space-y-3">
                  <Button
                    type="button"
                    variant="outline"
                    onClick={handleTestConnection}
                    disabled={isTesting}
                  >
                    {isTesting ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Testing...
                      </>
                    ) : (
                      <>
                        <Zap className="mr-2 h-4 w-4" />
                        Test Connection
                      </>
                    )}
                  </Button>

                  {testResult && (
                    <div
                      className={`flex items-center gap-2 p-3 rounded-md ${
                        testResult.success
                          ? "bg-green-50 text-green-800 dark:bg-green-900/20 dark:text-green-400"
                          : "bg-red-50 text-red-800 dark:bg-red-900/20 dark:text-red-400"
                      }`}
                    >
                      {testResult.success ? (
                        <CheckCircle className="h-5 w-5" />
                      ) : (
                        <XCircle className="h-5 w-5" />
                      )}
                      <span className="text-sm">{testResult.message}</span>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Actions */}
            <div className="flex gap-3 pt-4">
              <Button
                type="submit"
                disabled={createDestination.isPending || !selectedType}
              >
                {createDestination.isPending ? (
                  "Creating..."
                ) : (
                  <>
                    <Check className="mr-2 h-4 w-4" />
                    Create Destination
                  </>
                )}
              </Button>
              <Button
                type="button"
                variant="outline"
                onClick={() => router.back()}
              >
                Cancel
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
