"use client";

import { useState, useEffect, useCallback } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { scaleIn } from "@/lib/animations";
import {
  type ConnectorMeta,
  type DestinationMeta,
  type FieldDef,
  getSourceMeta,
  getDestinationMeta,
} from "@/lib/connector-icons";
import api from "@/lib/api-client";
import {
  CheckCircle2,
  XCircle,
  Loader2,
  ArrowRight,
  Info,
  RefreshCw,
} from "lucide-react";

interface CredentialFormProps {
  connectorId: string;
  mode: "source" | "destination";
  values: Record<string, string>;
  onChange: (values: Record<string, string>) => void;
  onTestResult?: (success: boolean, metadata?: Record<string, any>) => void;
  autoTest?: boolean;
}

type TestState = "idle" | "testing" | "success" | "error";

export default function CredentialForm({
  connectorId,
  mode,
  values,
  onChange,
  onTestResult,
  autoTest = true,
}: CredentialFormProps) {
  const [testState, setTestState] = useState<TestState>("idle");
  const [testMessage, setTestMessage] = useState("");
  const [testMetadata, setTestMetadata] = useState<Record<string, any> | null>(null);

  const meta: ConnectorMeta | DestinationMeta | undefined =
    mode === "source" ? getSourceMeta(connectorId) : getDestinationMeta(connectorId);

  if (!meta) return null;

  const fields = meta.fields;
  const Icon = meta.icon;
  const requiredFields = fields.filter((f) => f.required);

  const allRequiredFilled = requiredFields.every(
    (f) => values[f.key] && values[f.key].trim() !== ""
  );

  const handleFieldChange = (key: string, value: string) => {
    const next = { ...values, [key]: value };
    onChange(next);
    // Reset test when credentials change
    if (testState === "success" || testState === "error") {
      setTestState("idle");
      setTestMessage("");
      setTestMetadata(null);
    }
  };

  const runTest = async () => {
    if (!allRequiredFilled) return;

    setTestState("testing");
    setTestMessage("");
    setTestMetadata(null);

    try {
      const endpoint =
        mode === "source"
          ? "/sources/discovery/test-connection"
          : "/destinations/discovery/test-connection";

      const payload =
        mode === "source"
          ? { source_type: connectorId, config: values }
          : { destination_type: connectorId, config: values };

      const { data } = await api.post(endpoint, payload);

      if (data.success) {
        setTestState("success");
        setTestMessage(data.message || "Connection successful!");
        setTestMetadata(data.metadata || null);
        onTestResult?.(true, data.metadata);
      } else {
        setTestState("error");
        setTestMessage(data.message || "Connection failed");
        onTestResult?.(false);
      }
    } catch (err: any) {
      setTestState("error");
      setTestMessage(
        err.response?.data?.detail || err.message || "Connection test failed"
      );
      onTestResult?.(false);
    }
  };

  // Auto-test when all required fields are filled (debounced)
  useEffect(() => {
    if (!autoTest || !allRequiredFilled || testState === "testing") return;

    const timer = setTimeout(() => {
      if (testState === "idle") {
        runTest();
      }
    }, 800);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [allRequiredFilled, autoTest]);

  const renderField = (field: FieldDef) => {
    const value = values[field.key] || field.defaultValue?.toString() || "";

    return (
      <div key={field.key} className="space-y-2">
        <Label htmlFor={field.key} className="text-sm">
          {field.label}
          {field.required && <span className="text-destructive ml-0.5">*</span>}
        </Label>

        {field.type === "textarea" ? (
          <Textarea
            id={field.key}
            value={value}
            onChange={(e) => handleFieldChange(field.key, e.target.value)}
            placeholder={field.placeholder}
            className="min-h-[100px] font-mono text-xs"
          />
        ) : field.type === "select" ? (
          <Select
            value={value}
            onValueChange={(v) => handleFieldChange(field.key, v)}
          >
            <SelectTrigger>
              <SelectValue placeholder={`Select ${field.label.toLowerCase()}`} />
            </SelectTrigger>
            <SelectContent>
              {field.options?.map((opt) => (
                <SelectItem key={opt.value} value={opt.value}>
                  {opt.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        ) : (
          <Input
            id={field.key}
            type={field.type === "password" ? "password" : field.type === "number" ? "number" : "text"}
            value={value}
            onChange={(e) => handleFieldChange(field.key, e.target.value)}
            placeholder={field.placeholder}
          />
        )}

        {field.helpText && (
          <p className="text-[11px] text-muted-foreground flex items-start gap-1">
            <Info className="h-3 w-3 mt-0.5 shrink-0" />
            {field.helpText}
          </p>
        )}
      </div>
    );
  };

  // Split fields into grid-friendly layout
  const shortFields = fields.filter(
    (f) => f.type !== "textarea"
  );
  const longFields = fields.filter((f) => f.type === "textarea");
  const shouldGrid = shortFields.length >= 2;

  return (
    <div className="space-y-6">
      {/* Connector header */}
      <div className="flex items-center gap-4">
        <div className={`flex h-14 w-14 items-center justify-center rounded-xl ${meta.color} shadow-sm`}>
          <Icon className={`h-7 w-7 ${meta.textColor}`} />
        </div>
        <div>
          <h3 className="text-lg font-semibold">{meta.name}</h3>
          <p className="text-sm text-muted-foreground">{meta.description}</p>
        </div>
      </div>

      {/* Fields */}
      <div className="space-y-4">
        {shouldGrid ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            {shortFields.map(renderField)}
          </div>
        ) : (
          shortFields.map(renderField)
        )}
        {longFields.map(renderField)}
      </div>

      {/* Connection test */}
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <Button
            type="button"
            variant={testState === "success" ? "outline" : "default"}
            size="sm"
            onClick={runTest}
            disabled={!allRequiredFilled || testState === "testing"}
            className="h-9"
          >
            {testState === "testing" ? (
              <>
                <Loader2 className="mr-2 h-3.5 w-3.5 animate-spin" />
                Testing...
              </>
            ) : testState === "success" ? (
              <>
                <RefreshCw className="mr-2 h-3.5 w-3.5" />
                Re-test
              </>
            ) : (
              <>
                <ArrowRight className="mr-2 h-3.5 w-3.5" />
                Test Connection
              </>
            )}
          </Button>

          {/* Inline status */}
          <AnimatePresence mode="wait">
            {testState === "success" && (
              <motion.div
                key="success"
                variants={scaleIn}
                initial="initial"
                animate="animate"
                exit="exit"
                className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400"
              >
                <CheckCircle2 className="h-4 w-4" />
                <span className="text-sm font-medium">Connected!</span>
              </motion.div>
            )}
            {testState === "error" && (
              <motion.div
                key="error"
                variants={scaleIn}
                initial="initial"
                animate="animate"
                exit="exit"
                className="flex items-center gap-1.5 text-destructive"
              >
                <XCircle className="h-4 w-4" />
                <span className="text-sm">{testMessage}</span>
              </motion.div>
            )}
            {testState === "testing" && (
              <motion.span
                key="testing"
                variants={scaleIn}
                initial="initial"
                animate="animate"
                exit="exit"
                className="text-sm text-muted-foreground"
              >
                Verifying credentials...
              </motion.span>
            )}
          </AnimatePresence>
        </div>

        {/* Metadata on success */}
        {testState === "success" && testMetadata && Object.keys(testMetadata).length > 0 && (
          <motion.div
            variants={scaleIn}
            initial="initial"
            animate="animate"
            className="rounded-lg border border-emerald-200 bg-emerald-50 dark:bg-emerald-950/20 dark:border-emerald-900 p-3"
          >
            <div className="flex flex-wrap gap-3">
              {Object.entries(testMetadata).map(([key, val]) => (
                <div key={key} className="text-xs">
                  <span className="text-muted-foreground capitalize">
                    {key.replace(/_/g, " ")}:
                  </span>{" "}
                  <span className="font-medium">{String(val)}</span>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  );
}
