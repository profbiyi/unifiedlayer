"use client";

import { useState } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
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
import { useUpdatePipeline } from "@/hooks/queries/usePipelines";
import { ShieldCheck } from "lucide-react";

interface PiiConfig {
  enabled?: boolean;
  strategy?: string;
  columns?: string[];
  auto_detect?: boolean;
}

interface PiiMaskingPanelProps {
  pipelineId: string;
  config?: Record<string, any>;
}

const STRATEGIES = [
  { value: "partial", label: "Partial — j***@example.com" },
  { value: "redact", label: "Redact — ***" },
  { value: "hash", label: "Hash — irreversible, keeps joins" },
  { value: "null", label: "Remove — empty the value" },
];

export function PiiMaskingPanel({ pipelineId, config }: PiiMaskingPanelProps) {
  const existing: PiiConfig = (config?.pii_masking as PiiConfig) || {};
  const [enabled, setEnabled] = useState(Boolean(existing.enabled));
  const [strategy, setStrategy] = useState(existing.strategy || "partial");
  const [columnsText, setColumnsText] = useState((existing.columns || []).join(", "));
  const [autoDetect, setAutoDetect] = useState(Boolean(existing.auto_detect));

  const update = useUpdatePipeline(pipelineId);

  const columns = columnsText
    .split(",")
    .map((c) => c.trim())
    .filter(Boolean);

  const handleSave = () => {
    // Read-modify-write: the API replaces the whole config object, so merge our
    // pii_masking block into the existing config rather than overwriting it.
    update.mutate({
      config: {
        ...(config || {}),
        pii_masking: { enabled, strategy, columns, auto_detect: autoDetect },
      },
    });
  };

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center gap-2">
          <ShieldCheck className="h-5 w-5 text-primary" />
          <CardTitle>Privacy &amp; PII masking</CardTitle>
        </div>
        <CardDescription>
          Mask sensitive column values as data syncs to the destination, so raw PII
          never leaves your source.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-5">
        <div className="flex items-center justify-between gap-4">
          <div>
            <Label htmlFor="pii-enabled">Enable PII masking</Label>
            <p className="text-sm text-muted-foreground">
              Apply masking to every run of this pipeline.
            </p>
          </div>
          <Switch id="pii-enabled" checked={enabled} onCheckedChange={setEnabled} />
        </div>

        {enabled && (
          <div className="space-y-5 rounded-lg border p-4">
            <div className="space-y-2">
              <Label>Masking strategy</Label>
              <Select value={strategy} onValueChange={setStrategy}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {STRATEGIES.map((s) => (
                    <SelectItem key={s.value} value={s.value}>
                      {s.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="pii-columns">Columns to mask</Label>
              <Input
                id="pii-columns"
                placeholder="email, phone, bvn"
                value={columnsText}
                onChange={(e) => setColumnsText(e.target.value)}
              />
              <p className="text-sm text-muted-foreground">
                Comma-separated column names (case-insensitive).
              </p>
              {columns.length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {columns.map((c) => (
                    <Badge key={c} variant="secondary">
                      {c}
                    </Badge>
                  ))}
                </div>
              )}
            </div>

            <div className="flex items-center justify-between gap-4">
              <div>
                <Label htmlFor="pii-auto">Auto-detect PII columns</Label>
                <p className="text-sm text-muted-foreground">
                  Also mask common PII names (email, phone, SSN, card, IBAN, BVN, DOB).
                </p>
              </div>
              <Switch
                id="pii-auto"
                checked={autoDetect}
                onCheckedChange={setAutoDetect}
              />
            </div>
          </div>
        )}

        <Button onClick={handleSave} disabled={update.isPending}>
          {update.isPending ? "Saving…" : "Save"}
        </Button>
      </CardContent>
    </Card>
  );
}
