"use client";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Checkbox } from "@/components/ui/checkbox";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Info } from "lucide-react";
import { SourceWizardData } from "@/app/(dashboard)/sources/new/page";

interface HttpFileFormProps {
  data: SourceWizardData;
  onUpdate: (updates: Partial<SourceWizardData>) => void;
}

export default function HttpFileForm({ data, onUpdate }: HttpFileFormProps) {
  const updateConfig = (key: string, value: unknown) => {
    onUpdate({
      config: {
        ...data.config,
        [key]: value,
      },
    });
  };

  const fileFormat: string = data.config.file_format || "auto";
  const isCSV = fileFormat === "csv";

  return (
    <div className="space-y-4">
      {/* URL */}
      <div className="space-y-2">
        <Label htmlFor="http_url">
          File URL <span className="text-destructive">*</span>
        </Label>
        <Input
          id="http_url"
          type="url"
          placeholder="https://data.example.com/sales.csv"
          value={data.config.url || ""}
          onChange={(e) => updateConfig("url", e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          Public HTTPS URL to a CSV, JSONL, or Parquet file
        </p>
      </div>

      {/* File Format */}
      <div className="space-y-2">
        <Label htmlFor="file_format">File Format</Label>
        <Select
          value={fileFormat}
          onValueChange={(value) => updateConfig("file_format", value)}
        >
          <SelectTrigger id="file_format">
            <SelectValue placeholder="Auto-detect from URL" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="auto">Auto-detect from URL</SelectItem>
            <SelectItem value="csv">CSV</SelectItem>
            <SelectItem value="jsonl">JSONL</SelectItem>
            <SelectItem value="parquet">Parquet</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          Leave as Auto-detect to infer the format from the file extension
        </p>
      </div>

      {/* Table Name */}
      <div className="space-y-2">
        <Label htmlFor="table_name">Destination Table Name</Label>
        <Input
          id="table_name"
          placeholder="sales_data"
          value={data.config.table_name || ""}
          onChange={(e) => updateConfig("table_name", e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          Auto-derived from filename if not set
        </p>
      </div>

      {/* CSV-specific options */}
      {isCSV && (
        <>
          <div className="space-y-2">
            <Label htmlFor="csv_delimiter">CSV Delimiter</Label>
            <Input
              id="csv_delimiter"
              placeholder=","
              maxLength={1}
              value={data.config.csv_delimiter !== undefined ? data.config.csv_delimiter : ","}
              onChange={(e) => updateConfig("csv_delimiter", e.target.value)}
              className="max-w-[120px]"
            />
            <p className="text-xs text-muted-foreground">
              Single character used to separate fields (default: comma)
            </p>
          </div>

          <div className="flex items-center space-x-2">
            <Checkbox
              id="has_header_row"
              checked={data.config.has_header_row !== false}
              onCheckedChange={(checked) =>
                updateConfig("has_header_row", checked === true)
              }
            />
            <Label htmlFor="has_header_row" className="font-normal cursor-pointer">
              Has header row
            </Label>
          </div>
        </>
      )}

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          The file must be publicly accessible via HTTPS. Authentication for
          file URLs is not supported. For private files, use the REST API
          (Custom) connector instead.
        </AlertDescription>
      </Alert>
    </div>
  );
}
