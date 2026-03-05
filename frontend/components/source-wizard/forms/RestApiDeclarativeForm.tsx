"use client";

import { useState } from "react";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ChevronDown,
  ChevronUp,
  Plus,
  Trash2,
  Info,
} from "lucide-react";
import { SourceWizardData } from "@/app/(dashboard)/sources/new/page";

interface Endpoint {
  table_name: string;
  path: string;
  primary_key: string;
  cursor_field: string;
  write_mode: string;
}

interface HttpFileFormProps {
  data: SourceWizardData;
  onUpdate: (updates: Partial<SourceWizardData>) => void;
}

const DEFAULT_ENDPOINT: Endpoint = {
  table_name: "",
  path: "",
  primary_key: "",
  cursor_field: "",
  write_mode: "append",
};

export default function RestApiDeclarativeForm({
  data,
  onUpdate,
}: HttpFileFormProps) {
  const [paginationOpen, setPaginationOpen] = useState(false);

  const updateConfig = (key: string, value: unknown) => {
    onUpdate({
      config: {
        ...data.config,
        [key]: value,
      },
    });
  };

  const authType: string = data.config.auth_type || "none";
  const endpoints: Endpoint[] = data.config.endpoints || [{ ...DEFAULT_ENDPOINT }];
  const paginationType: string = data.config.pagination_type || "auto";

  const updateEndpoint = (index: number, field: keyof Endpoint, value: string) => {
    const updated = endpoints.map((ep, i) =>
      i === index ? { ...ep, [field]: value } : ep
    );
    updateConfig("endpoints", updated);
  };

  const addEndpoint = () => {
    updateConfig("endpoints", [...endpoints, { ...DEFAULT_ENDPOINT }]);
  };

  const removeEndpoint = (index: number) => {
    if (endpoints.length <= 1) return;
    updateConfig(
      "endpoints",
      endpoints.filter((_, i) => i !== index)
    );
  };

  return (
    <div className="space-y-6">
      <Tabs defaultValue="connection">
        <TabsList className="w-full">
          <TabsTrigger value="connection" className="flex-1">
            Connection
          </TabsTrigger>
          <TabsTrigger value="endpoints" className="flex-1">
            Endpoints
            <Badge variant="secondary" className="ml-2 h-5 min-w-5 px-1 text-xs">
              {endpoints.length}
            </Badge>
          </TabsTrigger>
          <TabsTrigger value="pagination" className="flex-1">
            Pagination
          </TabsTrigger>
        </TabsList>

        {/* ── Section 1: Connection ── */}
        <TabsContent value="connection" className="space-y-4 pt-4">
          <div className="space-y-2">
            <Label htmlFor="base_url">
              Base URL <span className="text-destructive">*</span>
            </Label>
            <Input
              id="base_url"
              type="url"
              placeholder="https://api.example.com/v1/"
              value={data.config.base_url || ""}
              onChange={(e) => updateConfig("base_url", e.target.value)}
            />
            <p className="text-xs text-muted-foreground">
              The root URL for all API requests. Endpoint paths are appended to this.
            </p>
          </div>

          <div className="space-y-2">
            <Label htmlFor="auth_type">Authentication Type</Label>
            <Select
              value={authType}
              onValueChange={(value) => updateConfig("auth_type", value)}
            >
              <SelectTrigger id="auth_type">
                <SelectValue placeholder="Select auth type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="none">None</SelectItem>
                <SelectItem value="bearer">Bearer Token</SelectItem>
                <SelectItem value="api_key">API Key</SelectItem>
                <SelectItem value="basic">Basic Auth</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Bearer Token */}
          {authType === "bearer" && (
            <div className="space-y-2">
              <Label htmlFor="bearer_token">
                Bearer Token <span className="text-destructive">*</span>
              </Label>
              <Input
                id="bearer_token"
                type="password"
                placeholder="••••••••"
                value={data.config.bearer_token || ""}
                onChange={(e) => updateConfig("bearer_token", e.target.value)}
              />
            </div>
          )}

          {/* API Key */}
          {authType === "api_key" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="api_key_value">
                  API Key <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="api_key_value"
                  type="password"
                  placeholder="••••••••"
                  value={data.config.api_key_value || ""}
                  onChange={(e) => updateConfig("api_key_value", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="api_key_header">Header Name</Label>
                <Input
                  id="api_key_header"
                  placeholder="X-API-Key"
                  value={data.config.api_key_header || "X-API-Key"}
                  onChange={(e) => updateConfig("api_key_header", e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  HTTP header used to send the API key (default: X-API-Key)
                </p>
              </div>
            </div>
          )}

          {/* Basic Auth */}
          {authType === "basic" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="basic_username">
                  Username <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="basic_username"
                  placeholder="username"
                  value={data.config.basic_username || ""}
                  onChange={(e) => updateConfig("basic_username", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="basic_password">
                  Password <span className="text-destructive">*</span>
                </Label>
                <Input
                  id="basic_password"
                  type="password"
                  placeholder="••••••••"
                  value={data.config.basic_password || ""}
                  onChange={(e) => updateConfig("basic_password", e.target.value)}
                />
              </div>
            </div>
          )}
        </TabsContent>

        {/* ── Section 2: Endpoints ── */}
        <TabsContent value="endpoints" className="space-y-4 pt-4">
          <p className="text-sm text-muted-foreground">
            Define one or more API endpoints (resources) to sync. Each endpoint
            maps to a table in your destination.
          </p>

          <div className="space-y-4">
            {endpoints.map((endpoint, index) => (
              <div
                key={index}
                className="rounded-lg border p-4 space-y-4 relative"
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-medium text-muted-foreground">
                    Endpoint {index + 1}
                  </span>
                  {endpoints.length > 1 && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => removeEndpoint(index)}
                      className="h-7 w-7 p-0 text-destructive hover:text-destructive"
                      aria-label={`Remove endpoint ${index + 1}`}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  )}
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor={`table_name_${index}`}>
                      Table Name <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id={`table_name_${index}`}
                      placeholder="orders"
                      value={endpoint.table_name}
                      onChange={(e) =>
                        updateEndpoint(index, "table_name", e.target.value)
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      Name of the destination table
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`path_${index}`}>
                      Endpoint Path <span className="text-destructive">*</span>
                    </Label>
                    <Input
                      id={`path_${index}`}
                      placeholder="orders"
                      value={endpoint.path}
                      onChange={(e) =>
                        updateEndpoint(index, "path", e.target.value)
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      Path appended to the base URL (e.g. orders or users/{"{id}"}/items)
                    </p>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label htmlFor={`primary_key_${index}`}>Primary Key</Label>
                    <Input
                      id={`primary_key_${index}`}
                      placeholder="id"
                      value={endpoint.primary_key}
                      onChange={(e) =>
                        updateEndpoint(index, "primary_key", e.target.value)
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      Field used for deduplication on upsert
                    </p>
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`cursor_field_${index}`}>Cursor Field</Label>
                    <Input
                      id={`cursor_field_${index}`}
                      placeholder="updated_at"
                      value={endpoint.cursor_field}
                      onChange={(e) =>
                        updateEndpoint(index, "cursor_field", e.target.value)
                      }
                    />
                    <p className="text-xs text-muted-foreground">
                      Date/timestamp field for incremental sync
                    </p>
                  </div>
                </div>

                <div className="space-y-2">
                  <Label htmlFor={`write_mode_${index}`}>Write Mode</Label>
                  <Select
                    value={endpoint.write_mode || "append"}
                    onValueChange={(value) =>
                      updateEndpoint(index, "write_mode", value)
                    }
                  >
                    <SelectTrigger id={`write_mode_${index}`}>
                      <SelectValue placeholder="Select write mode" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="append">Append</SelectItem>
                      <SelectItem value="merge">Merge (Upsert)</SelectItem>
                      <SelectItem value="replace">Replace</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
            ))}
          </div>

          <Button
            type="button"
            variant="outline"
            className="w-full"
            onClick={addEndpoint}
          >
            <Plus className="mr-2 h-4 w-4" />
            Add Another Endpoint
          </Button>
        </TabsContent>

        {/* ── Section 3: Pagination ── */}
        <TabsContent value="pagination" className="space-y-4 pt-4">
          <p className="text-sm text-muted-foreground">
            Configure how the connector navigates through paginated API
            responses. Leave as Auto-detect for most APIs.
          </p>

          <div className="space-y-2">
            <Label htmlFor="pagination_type">Pagination Type</Label>
            <Select
              value={paginationType}
              onValueChange={(value) =>
                updateConfig("pagination_type", value)
              }
            >
              <SelectTrigger id="pagination_type">
                <SelectValue placeholder="Select pagination type" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="auto">Auto-detect</SelectItem>
                <SelectItem value="cursor">Cursor-based</SelectItem>
                <SelectItem value="offset">Offset / Limit</SelectItem>
                <SelectItem value="page">Page Number</SelectItem>
                <SelectItem value="none">None (single page)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {paginationType === "cursor" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="cursor_path">Cursor Response Path</Label>
                <Input
                  id="cursor_path"
                  placeholder="meta.next_cursor"
                  value={data.config.cursor_path || ""}
                  onChange={(e) => updateConfig("cursor_path", e.target.value)}
                />
                <p className="text-xs text-muted-foreground">
                  JSON path to the next cursor value in the API response
                </p>
              </div>
              <div className="space-y-2">
                <Label htmlFor="cursor_param">Cursor Query Parameter</Label>
                <Input
                  id="cursor_param"
                  placeholder="cursor"
                  value={data.config.cursor_param || "cursor"}
                  onChange={(e) => updateConfig("cursor_param", e.target.value)}
                />
              </div>
            </div>
          )}

          {paginationType === "offset" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="offset_param">Offset Parameter</Label>
                <Input
                  id="offset_param"
                  placeholder="offset"
                  value={data.config.offset_param || "offset"}
                  onChange={(e) => updateConfig("offset_param", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="limit_param">Limit Parameter</Label>
                <Input
                  id="limit_param"
                  placeholder="limit"
                  value={data.config.limit_param || "limit"}
                  onChange={(e) => updateConfig("limit_param", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="page_size">Page Size</Label>
                <Input
                  id="page_size"
                  type="number"
                  placeholder="100"
                  value={data.config.page_size || ""}
                  onChange={(e) =>
                    updateConfig("page_size", parseInt(e.target.value) || 100)
                  }
                />
              </div>
            </div>
          )}

          {paginationType === "page" && (
            <div className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="page_param">Page Parameter</Label>
                <Input
                  id="page_param"
                  placeholder="page"
                  value={data.config.page_param || "page"}
                  onChange={(e) => updateConfig("page_param", e.target.value)}
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="per_page_param">Per-Page Parameter</Label>
                <Input
                  id="per_page_param"
                  placeholder="per_page"
                  value={data.config.per_page_param || "per_page"}
                  onChange={(e) =>
                    updateConfig("per_page_param", e.target.value)
                  }
                />
              </div>
              <div className="space-y-2">
                <Label htmlFor="page_size_page">Page Size</Label>
                <Input
                  id="page_size_page"
                  type="number"
                  placeholder="100"
                  value={data.config.page_size || ""}
                  onChange={(e) =>
                    updateConfig("page_size", parseInt(e.target.value) || 100)
                  }
                />
              </div>
            </div>
          )}

          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              Auto-detect works for most REST APIs that follow common pagination
              patterns (Link headers, next_url fields, etc.).
            </AlertDescription>
          </Alert>
        </TabsContent>
      </Tabs>
    </div>
  );
}
