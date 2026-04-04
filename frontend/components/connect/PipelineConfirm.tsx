"use client";

import { motion } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { scaleIn } from "@/lib/animations";
import { getSourceMeta, getDestinationMeta } from "@/lib/connector-icons";
import {
  ArrowRight,
  Play,
  Clock,
  Loader2,
  Sparkles,
  Zap,
} from "lucide-react";
import type { WriteMode } from "@/types/pipeline";

interface PipelineConfirmProps {
  sourceType: string;
  destinationType: string;
  pipelineName: string;
  schedule: string;
  writeMode: WriteMode;
  onNameChange: (name: string) => void;
  onScheduleChange: (schedule: string) => void;
  onWriteModeChange: (mode: WriteMode) => void;
  onSubmit: () => void;
  isSubmitting: boolean;
}

const SCHEDULE_OPTIONS = [
  { value: "", label: "Manual", description: "Run on demand", icon: Play },
  { value: "0 * * * *", label: "Hourly", description: "Every hour", icon: Clock },
  { value: "0 */6 * * *", label: "Every 6 hours", description: "4 times a day", icon: Clock },
  { value: "0 6 * * *", label: "Daily", description: "Every day at 6 AM", icon: Clock },
  { value: "0 6 * * 1", label: "Weekly", description: "Every Monday at 6 AM", icon: Clock },
];

const WRITE_MODE_OPTIONS: { value: WriteMode; label: string; description: string }[] = [
  { value: "merge", label: "Merge", description: "Update existing rows, insert new ones" },
  { value: "upsert", label: "Upsert", description: "True upsert — best for dimension tables" },
  { value: "append", label: "Append", description: "Always add rows — best for event data" },
  { value: "insert_only", label: "Deduplicated Append", description: "Append with primary key dedup" },
  { value: "scd2", label: "SCD Type 2", description: "Track full change history" },
  { value: "replace", label: "Full Reload", description: "Drop and reload every sync" },
];

export default function PipelineConfirm({
  sourceType,
  destinationType,
  pipelineName,
  schedule,
  writeMode,
  onNameChange,
  onScheduleChange,
  onWriteModeChange,
  onSubmit,
  isSubmitting,
}: PipelineConfirmProps) {
  const sourceMeta = getSourceMeta(sourceType);
  const destMeta = getDestinationMeta(destinationType);

  const SourceIcon = sourceMeta?.icon || Zap;
  const DestIcon = destMeta?.icon || Zap;

  return (
    <motion.div
      variants={scaleIn}
      initial="initial"
      animate="animate"
      className="space-y-8"
    >
      {/* Header */}
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">Almost there!</h2>
        <p className="text-muted-foreground">Name your pipeline and choose a sync schedule</p>
      </div>

      {/* Visual flow: Source → Destination */}
      <div className="flex items-center justify-center gap-4">
        <div className="flex items-center gap-3 rounded-xl border bg-card p-4 shadow-sm">
          <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${sourceMeta?.color || "bg-gray-500"}`}>
            <SourceIcon className={`h-5 w-5 ${sourceMeta?.textColor || "text-white"}`} />
          </div>
          <span className="font-medium text-sm">{sourceMeta?.name || sourceType}</span>
        </div>

        <div className="flex flex-col items-center gap-1">
          <ArrowRight className="h-5 w-5 text-muted-foreground" />
          <span className="text-[10px] text-muted-foreground">sync</span>
        </div>

        <div className="flex items-center gap-3 rounded-xl border bg-card p-4 shadow-sm">
          <div className={`flex h-10 w-10 items-center justify-center rounded-lg ${destMeta?.color || "bg-gray-500"}`}>
            <DestIcon className={`h-5 w-5 ${destMeta?.textColor || "text-white"}`} />
          </div>
          <span className="font-medium text-sm">{destMeta?.name || destinationType}</span>
        </div>
      </div>

      {/* Settings */}
      <Card>
        <CardContent className="pt-6 space-y-6">
          {/* Pipeline name */}
          <div className="space-y-2">
            <Label htmlFor="pipeline-name">Pipeline Name</Label>
            <Input
              id="pipeline-name"
              value={pipelineName}
              onChange={(e) => onNameChange(e.target.value)}
              placeholder="My Pipeline"
              className="h-11"
            />
          </div>

          {/* Schedule - visual buttons */}
          <div className="space-y-3">
            <Label>Sync Schedule</Label>
            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-2">
              {SCHEDULE_OPTIONS.map((opt) => {
                const isActive = schedule === opt.value;
                const OptIcon = opt.icon;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => onScheduleChange(opt.value)}
                    className={`
                      flex flex-col items-center gap-1 rounded-lg border p-3 transition-all text-center
                      ${isActive
                        ? "border-primary bg-primary/5 ring-1 ring-primary/20"
                        : "border-border hover:border-primary/30 hover:bg-accent/50"
                      }
                    `}
                  >
                    <OptIcon className={`h-4 w-4 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
                    <span className={`text-xs font-medium ${isActive ? "text-primary" : ""}`}>{opt.label}</span>
                    <span className="text-[10px] text-muted-foreground">{opt.description}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Write mode */}
          <div className="space-y-2">
            <Label>Write Mode</Label>
            <Select value={writeMode} onValueChange={(v) => onWriteModeChange(v as WriteMode)}>
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {WRITE_MODE_OPTIONS.map((opt) => (
                  <SelectItem key={opt.value} value={opt.value}>
                    <div className="flex flex-col">
                      <span>{opt.label}</span>
                      <span className="text-xs text-muted-foreground">{opt.description}</span>
                    </div>
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Submit */}
      <div className="flex justify-center">
        <Button
          size="lg"
          onClick={onSubmit}
          disabled={!pipelineName.trim() || isSubmitting}
          className="h-12 px-8 rounded-xl text-base gap-2"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-5 w-5 animate-spin" />
              Creating...
            </>
          ) : (
            <>
              <Sparkles className="h-5 w-5" />
              Start Syncing
            </>
          )}
        </Button>
      </div>
    </motion.div>
  );
}
