"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { Loader2, ArrowRight, ArrowLeft } from "lucide-react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  useTemplate,
  useDeployTemplate,
  TemplateCredentialField,
} from "@/hooks/queries/useTemplates";

function CredentialField({
  field,
  value,
  onChange,
}: {
  field: TemplateCredentialField;
  value: string;
  onChange: (val: string) => void;
}) {
  if (field.type === "textarea") {
    return (
      <div className="space-y-2">
        <Label>
          {field.label}
          {field.required && <span className="text-destructive"> *</span>}
        </Label>
        <Textarea
          placeholder={field.placeholder}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          rows={4}
        />
      </div>
    );
  }

  if (field.type === "select" && field.options) {
    return (
      <div className="space-y-2">
        <Label>
          {field.label}
          {field.required && <span className="text-destructive"> *</span>}
        </Label>
        <Select value={value} onValueChange={onChange}>
          <SelectTrigger>
            <SelectValue placeholder={`Select ${field.label.toLowerCase()}`} />
          </SelectTrigger>
          <SelectContent>
            {field.options.map((opt) => (
              <SelectItem key={opt} value={opt}>
                {opt}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <Label>
        {field.label}
        {field.required && <span className="text-destructive"> *</span>}
      </Label>
      <Input
        type={field.type === "password" ? "password" : field.type === "number" ? "number" : "text"}
        placeholder={field.placeholder}
        value={value}
        onChange={(e) => onChange(e.target.value)}
      />
    </div>
  );
}

export default function DeployTemplatePage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const { data: template, isLoading } = useTemplate(id);
  const deployMutation = useDeployTemplate();

  const [pipelineName, setPipelineName] = useState("");
  const [schedule, setSchedule] = useState("");
  const [sourceCreds, setSourceCreds] = useState<Record<string, string>>({});
  const [destCreds, setDestCreds] = useState<Record<string, string>>({});

  const updateSourceCred = (field: string, value: string) => {
    setSourceCreds((prev) => ({ ...prev, [field]: value }));
  };

  const updateDestCred = (field: string, value: string) => {
    setDestCreds((prev) => ({ ...prev, [field]: value }));
  };

  const handleDeploy = async () => {
    if (!template) return;

    // Parse credentials_json fields from string to object
    const parsedSourceCreds = { ...sourceCreds };
    const parsedDestCreds = { ...destCreds };

    for (const field of template.source_credential_schema) {
      if (field.type === "textarea" && parsedSourceCreds[field.field]) {
        try {
          parsedSourceCreds[field.field] = JSON.parse(parsedSourceCreds[field.field]);
        } catch {
          // Keep as string
        }
      }
    }
    for (const field of template.destination_credential_schema) {
      if (field.type === "textarea" && parsedDestCreds[field.field]) {
        try {
          parsedDestCreds[field.field] = JSON.parse(parsedDestCreds[field.field]);
        } catch {
          // Keep as string
        }
      }
    }

    const result = await deployMutation.mutateAsync({
      templateId: id,
      request: {
        source_credentials: parsedSourceCreds,
        destination_credentials: parsedDestCreds,
        pipeline_name: pipelineName || `${template.name} Pipeline`,
        schedule: schedule || undefined,
      },
    });

    router.push(`/pipelines`);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!template) {
    return (
      <div className="flex items-center justify-center h-64">
        <p className="text-muted-foreground">Template not found</p>
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-5xl">
      <div className="flex items-center gap-4">
        <Button variant="ghost" size="icon" onClick={() => router.back()}>
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div>
          <h1 className="text-2xl font-bold tracking-tight">
            Deploy: {template.name}
          </h1>
          <p className="text-muted-foreground">{template.description}</p>
        </div>
      </div>

      <div className="flex items-center gap-2 text-sm">
        <Badge variant="outline">{template.source_type}</Badge>
        <ArrowRight className="h-3 w-3 text-muted-foreground" />
        <Badge variant="outline">{template.destination_type}</Badge>
      </div>

      {/* Pipeline Name */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Pipeline Configuration</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="space-y-2">
            <Label>Pipeline Name</Label>
            <Input
              placeholder={`${template.name} Pipeline`}
              value={pipelineName}
              onChange={(e) => setPipelineName(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label>Schedule (cron, optional)</Label>
            <Input
              placeholder="e.g. 0 0 * * * (daily at midnight)"
              value={schedule}
              onChange={(e) => setSchedule(e.target.value)}
            />
          </div>
        </CardContent>
      </Card>

      {/* Two-panel credentials */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Source Credentials</CardTitle>
            <CardDescription>
              {template.source_type} connection details
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {template.source_credential_schema.map((field) => (
              <CredentialField
                key={field.field}
                field={field}
                value={sourceCreds[field.field] || ""}
                onChange={(val) => updateSourceCred(field.field, val)}
              />
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Destination Credentials</CardTitle>
            <CardDescription>
              {template.destination_type} connection details
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {template.destination_credential_schema.map((field) => (
              <CredentialField
                key={field.field}
                field={field}
                value={destCreds[field.field] || ""}
                onChange={(val) => updateDestCred(field.field, val)}
              />
            ))}
          </CardContent>
        </Card>
      </div>

      <Button
        className="w-full"
        size="lg"
        onClick={handleDeploy}
        disabled={deployMutation.isPending}
      >
        {deployMutation.isPending ? (
          <>
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            Deploying...
          </>
        ) : (
          <>
            Deploy Pipeline
            <ArrowRight className="ml-2 h-4 w-4" />
          </>
        )}
      </Button>
    </div>
  );
}
