"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Card,
  CardContent,
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
import { ChevronDown, ChevronRight, Plus, Trash2 } from "lucide-react";
import { TransformationConfig } from "@/types/pipeline";

interface TransformationStepProps {
  config: TransformationConfig;
  onUpdate: (config: TransformationConfig) => void;
}

function CollapsibleSection({
  title,
  description,
  children,
  defaultOpen = false,
}: {
  title: string;
  description: string;
  children: React.ReactNode;
  defaultOpen?: boolean;
}) {
  const [open, setOpen] = useState(defaultOpen);

  return (
    <Card>
      <CardHeader
        className="cursor-pointer select-none"
        onClick={() => setOpen(!open)}
      >
        <div className="flex items-center gap-2">
          {open ? (
            <ChevronDown className="h-4 w-4" />
          ) : (
            <ChevronRight className="h-4 w-4" />
          )}
          <div>
            <CardTitle className="text-base">{title}</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">{description}</p>
          </div>
        </div>
      </CardHeader>
      {open && <CardContent>{children}</CardContent>}
    </Card>
  );
}

export default function TransformationStep({
  config,
  onUpdate,
}: TransformationStepProps) {
  // --- Excluded Columns ---
  const excludedColumns = config.excluded_columns || [];

  const addExcludedColumn = () => {
    onUpdate({
      ...config,
      excluded_columns: [...excludedColumns, ""],
    });
  };

  const updateExcludedColumn = (index: number, value: string) => {
    const updated = [...excludedColumns];
    updated[index] = value;
    onUpdate({ ...config, excluded_columns: updated });
  };

  const removeExcludedColumn = (index: number) => {
    const updated = excludedColumns.filter((_, i) => i !== index);
    onUpdate({ ...config, excluded_columns: updated });
  };

  // --- Column Mapping ---
  const columnMapping = config.column_mapping || {};
  const mappingEntries = Object.entries(columnMapping);

  const addMapping = () => {
    onUpdate({
      ...config,
      column_mapping: { ...columnMapping, "": "" },
    });
  };

  const updateMapping = (
    oldKey: string,
    newKey: string,
    newValue: string
  ) => {
    const updated = { ...columnMapping };
    if (oldKey !== newKey) {
      delete updated[oldKey];
    }
    updated[newKey] = newValue;
    onUpdate({ ...config, column_mapping: updated });
  };

  const removeMapping = (key: string) => {
    const updated = { ...columnMapping };
    delete updated[key];
    onUpdate({ ...config, column_mapping: updated });
  };

  // --- Type Casts ---
  const typeCasts = config.type_casts || {};
  const typeCastEntries = Object.entries(typeCasts);

  const addTypeCast = () => {
    onUpdate({
      ...config,
      type_casts: { ...typeCasts, "": "string" },
    });
  };

  const updateTypeCast = (
    oldKey: string,
    newKey: string,
    newType: string
  ) => {
    const updated = { ...typeCasts };
    if (oldKey !== newKey) {
      delete updated[oldKey];
    }
    updated[newKey] = newType;
    onUpdate({ ...config, type_casts: updated });
  };

  const removeTypeCast = (key: string) => {
    const updated = { ...typeCasts };
    delete updated[key];
    onUpdate({ ...config, type_casts: updated });
  };

  // --- Filters ---
  const filters = config.filters || [];

  const addFilter = () => {
    onUpdate({
      ...config,
      filters: [...filters, { column: "", operator: "=" as const, value: "" }],
    });
  };

  const updateFilter = (
    index: number,
    field: "column" | "operator" | "value",
    value: string
  ) => {
    const updated = [...filters];
    updated[index] = { ...updated[index], [field]: value };
    onUpdate({ ...config, filters: updated });
  };

  const removeFilter = (index: number) => {
    const updated = filters.filter((_, i) => i !== index);
    onUpdate({ ...config, filters: updated });
  };

  return (
    <div className="space-y-4">
      {/* Column Selection / Exclusion */}
      <CollapsibleSection
        title="Column Selection"
        description="Exclude columns from the output. Enter column names to remove from the data."
      >
        <div className="space-y-3">
          {excludedColumns.map((col, index) => (
            <div key={index} className="flex items-center gap-2">
              <Input
                placeholder="Column name to exclude"
                value={col}
                onChange={(e) => updateExcludedColumn(index, e.target.value)}
              />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeExcludedColumn(index)}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
          ))}
          <Button variant="outline" size="sm" onClick={addExcludedColumn}>
            <Plus className="mr-2 h-4 w-4" />
            Add Column
          </Button>
        </div>
      </CollapsibleSection>

      {/* Column Mapping */}
      <CollapsibleSection
        title="Column Mapping"
        description="Rename columns. Map source column names to new destination names."
      >
        <div className="space-y-3">
          {mappingEntries.map(([source, dest], index) => (
            <div key={index} className="flex items-center gap-2">
              <Input
                placeholder="Source column"
                value={source}
                onChange={(e) => updateMapping(source, e.target.value, dest)}
              />
              <span className="text-muted-foreground shrink-0">&rarr;</span>
              <Input
                placeholder="Destination column"
                value={dest}
                onChange={(e) => updateMapping(source, source, e.target.value)}
              />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeMapping(source)}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
          ))}
          <Button variant="outline" size="sm" onClick={addMapping}>
            <Plus className="mr-2 h-4 w-4" />
            Add Mapping
          </Button>
        </div>
      </CollapsibleSection>

      {/* Type Casting */}
      <CollapsibleSection
        title="Type Casting"
        description="Convert column values to a specific data type."
      >
        <div className="space-y-3">
          {typeCastEntries.map(([col, type], index) => (
            <div key={index} className="flex items-center gap-2">
              <Input
                placeholder="Column name"
                value={col}
                onChange={(e) => updateTypeCast(col, e.target.value, type)}
                className="flex-1"
              />
              <Select
                value={type}
                onValueChange={(val) => updateTypeCast(col, col, val)}
              >
                <SelectTrigger className="w-[160px]">
                  <SelectValue placeholder="Type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="string">String</SelectItem>
                  <SelectItem value="integer">Integer</SelectItem>
                  <SelectItem value="float">Float</SelectItem>
                  <SelectItem value="boolean">Boolean</SelectItem>
                  <SelectItem value="datetime">Datetime</SelectItem>
                </SelectContent>
              </Select>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeTypeCast(col)}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
          ))}
          <Button variant="outline" size="sm" onClick={addTypeCast}>
            <Plus className="mr-2 h-4 w-4" />
            Add Type Cast
          </Button>
        </div>
      </CollapsibleSection>

      {/* Row Filters */}
      <CollapsibleSection
        title="Row Filters"
        description="Filter rows based on column conditions. Only rows matching all filters will be included."
      >
        <div className="space-y-3">
          {filters.map((filter, index) => (
            <div key={index} className="flex items-center gap-2">
              <Input
                placeholder="Column"
                value={filter.column}
                onChange={(e) => updateFilter(index, "column", e.target.value)}
                className="flex-1"
              />
              <Select
                value={filter.operator}
                onValueChange={(val) => updateFilter(index, "operator", val)}
              >
                <SelectTrigger className="w-[120px]">
                  <SelectValue placeholder="Op" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="=">=</SelectItem>
                  <SelectItem value="!=">!=</SelectItem>
                  <SelectItem value=">">&gt;</SelectItem>
                  <SelectItem value="<">&lt;</SelectItem>
                  <SelectItem value="contains">contains</SelectItem>
                </SelectContent>
              </Select>
              <Input
                placeholder="Value"
                value={filter.value}
                onChange={(e) => updateFilter(index, "value", e.target.value)}
                className="flex-1"
              />
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeFilter(index)}
              >
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
          ))}
          <Button variant="outline" size="sm" onClick={addFilter}>
            <Plus className="mr-2 h-4 w-4" />
            Add Filter
          </Button>
        </div>
      </CollapsibleSection>
    </div>
  );
}
