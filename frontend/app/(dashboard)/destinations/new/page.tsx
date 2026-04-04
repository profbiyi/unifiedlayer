"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
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
import { ArrowLeft, Check, Zap, Loader2, CheckCircle, XCircle, CheckCircle2, Search } from "lucide-react";
import { useRouter } from "next/navigation";
import { useCreateDestination } from "@/hooks/queries/useDestinations";
import { useCurrentUser } from "@/hooks/queries/useAuth";
import { hoverLift, tapScale } from "@/lib/animations";
import {
  DESTINATION_CONNECTORS,
  type DestinationMeta,
  getDestinationMeta,
} from "@/lib/connector-icons";
import toast from "react-hot-toast";
import api from "@/lib/api-client";

export default function NewDestinationPage() {
  const router = useRouter();
  const [selectedType, setSelectedType] = useState("");
  const [search, setSearch] = useState("");
  const [isTesting, setIsTesting] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const createDestination = useCreateDestination();
  const { data: currentUser } = useCurrentUser();
  const { register, handleSubmit, getValues, formState: { errors } } = useForm();

  const selectedMeta = selectedType ? getDestinationMeta(selectedType) : undefined;

  const filtered = search.trim()
    ? DESTINATION_CONNECTORS.filter(
        (c) =>
          c.name.toLowerCase().includes(search.toLowerCase()) ||
          c.description.toLowerCase().includes(search.toLowerCase())
      )
    : DESTINATION_CONNECTORS;

  const handleSelect = (connector: DestinationMeta) => {
    if (selectedType === connector.id) {
      setSelectedType("");
    } else {
      setSelectedType(connector.id);
      setTestResult(null);
    }
  };

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
    } else if (selectedType === "duckdb") {
      config.database_path = data.database_path;
    } else if (selectedType === "redshift") {
      config.host = data.host;
      config.port = parseInt(data.port) || 5439;
      config.database = data.database;
      config.username = data.username;
      config.password = data.password;
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
              <Input id="host" placeholder="localhost" {...register("host", { required: true })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="port">Port *</Label>
              <Input id="port" type="number" placeholder="5432" {...register("port", { required: true })} />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="database">Database *</Label>
            <Input id="database" placeholder="my_warehouse" {...register("database", { required: true })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username *</Label>
              <Input id="username" placeholder="postgres" {...register("username", { required: true })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password *</Label>
              <Input id="password" type="password" placeholder="••••••••" {...register("password", { required: true })} />
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
            <Input id="project_id" placeholder="my-project-123" {...register("project_id", { required: true })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="dataset">Dataset *</Label>
            <Input id="dataset" placeholder="my_dataset" {...register("dataset", { required: true })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="credentials">Service Account JSON *</Label>
            <Textarea
              id="credentials"
              placeholder='{"type": "service_account", ...}'
              rows={4}
              className="font-mono text-xs"
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
            <Input id="account" placeholder="xy12345.us-east-1" {...register("account", { required: true })} />
            <p className="text-xs text-muted-foreground">
              Your Snowflake account identifier (e.g., xy12345.us-east-1)
            </p>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="warehouse">Warehouse *</Label>
              <Input id="warehouse" placeholder="COMPUTE_WH" {...register("warehouse", { required: true })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="role">Role</Label>
              <Input id="role" placeholder="ACCOUNTADMIN" {...register("role")} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="database">Database *</Label>
              <Input id="database" placeholder="MY_DATABASE" {...register("database", { required: true })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="schema">Schema *</Label>
              <Input id="schema" placeholder="PUBLIC" {...register("schema", { required: true })} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username *</Label>
              <Input id="username" placeholder="your_username" {...register("username", { required: true })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password *</Label>
              <Input id="password" type="password" placeholder="••••••••" {...register("password", { required: true })} />
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
            <Input id="bucket" placeholder="my-data-warehouse" {...register("bucket", { required: true })} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="region">Region *</Label>
            <Input id="region" placeholder="us-east-1" {...register("region", { required: true })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="access_key">Access Key *</Label>
              <Input id="access_key" placeholder="AKIA..." {...register("access_key", { required: true })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="secret_key">Secret Key *</Label>
              <Input id="secret_key" type="password" placeholder="••••••••" {...register("secret_key", { required: true })} />
            </div>
          </div>
        </>
      );
    }

    if (selectedType === "duckdb") {
      return (
        <div className="space-y-2">
          <Label htmlFor="database_path">Database Path *</Label>
          <Input id="database_path" placeholder="/data/analytics.duckdb" {...register("database_path", { required: true })} />
          <p className="text-xs text-muted-foreground">
            Path where the DuckDB database file will be created
          </p>
        </div>
      );
    }

    if (selectedType === "redshift") {
      return (
        <>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="host">Host *</Label>
              <Input id="host" placeholder="cluster.region.redshift.amazonaws.com" {...register("host", { required: true })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="port">Port *</Label>
              <Input id="port" type="number" placeholder="5439" {...register("port", { required: true })} />
            </div>
          </div>
          <div className="space-y-2">
            <Label htmlFor="database">Database *</Label>
            <Input id="database" placeholder="dev" {...register("database", { required: true })} />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div className="space-y-2">
              <Label htmlFor="username">Username *</Label>
              <Input id="username" placeholder="admin" {...register("username", { required: true })} />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password *</Label>
              <Input id="password" type="password" placeholder="••••••••" {...register("password", { required: true })} />
            </div>
          </div>
        </>
      );
    }

    const meta = getDestinationMeta(selectedType);
    return (
      <div className="text-sm text-muted-foreground">
        Configuration for {meta?.name || selectedType} coming soon!
      </div>
    );
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Add Destination</h1>
          <p className="text-muted-foreground">
            Choose where your data should be stored
          </p>
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)}>
        <Card>
          <CardHeader>
            <CardTitle>Pick a Destination</CardTitle>
            <CardDescription>
              Select the warehouse or storage where your synced data will land
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            {/* Search */}
            <div className="relative max-w-md">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search destinations..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9 h-10 rounded-xl"
              />
            </div>

            {/* Destination Cards Grid */}
            <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
              {filtered.map((connector) => {
                const Icon = connector.icon;
                const isSelected = selectedType === connector.id;
                return (
                  <motion.button
                    key={connector.id}
                    type="button"
                    whileHover={hoverLift}
                    whileTap={tapScale}
                    onClick={() => handleSelect(connector)}
                    className={`group relative flex flex-col items-center gap-2 rounded-xl border p-4 text-center transition-all cursor-pointer ${
                      isSelected
                        ? "border-primary ring-2 ring-primary/20 bg-primary/5"
                        : "hover:border-primary/30 hover:bg-accent/50 hover:shadow-sm"
                    }`}
                  >
                    <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${connector.color} shadow-sm`}>
                      <Icon className={`h-6 w-6 ${connector.textColor}`} />
                    </div>
                    <div>
                      <p className="text-sm font-medium">{connector.name}</p>
                      <p className="text-[11px] text-muted-foreground line-clamp-2 mt-0.5">{connector.description}</p>
                    </div>
                    {isSelected && (
                      <CheckCircle2 className="absolute top-2 right-2 h-4 w-4 text-primary" />
                    )}
                    {connector.popular && !isSelected && (
                      <span className="absolute top-1.5 right-1.5 text-[9px] font-semibold text-amber-600 dark:text-amber-400">
                        Popular
                      </span>
                    )}
                  </motion.button>
                );
              })}
            </div>

            {filtered.length === 0 && (
              <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
                <Search className="h-6 w-6 mb-2 opacity-50" />
                <p className="text-sm">No destinations found</p>
              </div>
            )}

            {/* Selected destination details */}
            <AnimatePresence>
              {selectedMeta && (
                <motion.div
                  initial={{ opacity: 0, height: 0 }}
                  animate={{ opacity: 1, height: "auto" }}
                  exit={{ opacity: 0, height: 0 }}
                  transition={{ duration: 0.2 }}
                  className="space-y-6 border-t pt-5"
                >
                  {/* Selected indicator */}
                  <div className="flex items-center gap-3">
                    {(() => {
                      const Icon = selectedMeta.icon;
                      return (
                        <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${selectedMeta.color}`}>
                          <Icon className={`h-4 w-4 ${selectedMeta.textColor}`} />
                        </div>
                      );
                    })()}
                    <div>
                      <p className="text-sm font-semibold">{selectedMeta.name} selected</p>
                      <p className="text-xs text-muted-foreground">{selectedMeta.description}</p>
                    </div>
                  </div>

                  {/* Basic Info */}
                  <div className="space-y-4">
                    <div className="space-y-2">
                      <Label htmlFor="name">Destination Name *</Label>
                      <Input
                        id="name"
                        placeholder={`My ${selectedMeta.name} Warehouse`}
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
                        rows={2}
                        {...register("description")}
                      />
                    </div>
                  </div>

                  {/* Connection Config */}
                  <div className="space-y-4">
                    <h3 className="font-semibold text-sm">Connection Details</h3>
                    {renderConfigFields()}

                    {/* Test Connection */}
                    <div className="pt-2 space-y-3">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={handleTestConnection}
                        disabled={isTesting}
                        className="h-9"
                      >
                        {isTesting ? (
                          <>
                            <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                            Testing...
                          </>
                        ) : (
                          <>
                            <Zap className="mr-2 h-3.5 w-3.5" />
                            Test Connection
                          </>
                        )}
                      </Button>

                      {testResult && (
                        <div
                          className={`flex items-center gap-2 p-3 rounded-lg text-sm ${
                            testResult.success
                              ? "bg-emerald-50 text-emerald-800 border border-emerald-200 dark:bg-emerald-950/20 dark:text-emerald-400 dark:border-emerald-900"
                              : "bg-red-50 text-red-800 border border-red-200 dark:bg-red-950/20 dark:text-red-400 dark:border-red-900"
                          }`}
                        >
                          {testResult.success ? (
                            <CheckCircle className="h-4 w-4 shrink-0" />
                          ) : (
                            <XCircle className="h-4 w-4 shrink-0" />
                          )}
                          <span>{testResult.message}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex gap-3 pt-2">
                    <Button
                      type="submit"
                      disabled={createDestination.isPending}
                    >
                      {createDestination.isPending ? (
                        <>
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                          Creating...
                        </>
                      ) : (
                        <>
                          <Check className="mr-2 h-4 w-4" />
                          Create Destination
                        </>
                      )}
                    </Button>
                    <Button type="button" variant="outline" onClick={() => router.back()}>
                      Cancel
                    </Button>
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </CardContent>
        </Card>
      </form>
    </div>
  );
}
