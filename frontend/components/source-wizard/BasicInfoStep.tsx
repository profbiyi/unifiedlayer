"use client";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { SourceWizardData } from "@/app/(dashboard)/sources/new/page";
import {
  Database,
  FileText,
  Cloud,
  Laptop,
  CreditCard,
  Sheet,
  Banknote,
  FileSpreadsheet,
  Landmark,
  Building2,
  Smartphone,
  Wallet,
  MessageCircle,
  Globe,
  Zap,
} from "lucide-react";

interface BasicInfoStepProps {
  data: SourceWizardData;
  onUpdate: (updates: Partial<SourceWizardData>) => void;
}

interface SourceType {
  value: string;
  label: string;
  description: string;
  icon: React.ElementType;
  category: string;
  isNew?: boolean;
}

const SOURCE_TYPES: SourceType[] = [
  // --- Payments ---
  {
    value: "stripe",
    label: "Stripe",
    description: "Sync payments, customers, subscriptions & invoices from Stripe",
    icon: CreditCard,
    category: "Payments",
  },
  {
    value: "paystack",
    label: "Paystack",
    description: "Sync transactions, customers & settlements from Paystack",
    icon: CreditCard,
    category: "Payments",
  },
  {
    value: "gocardless",
    label: "GoCardless",
    description: "Sync payments, mandates & customers from GoCardless",
    icon: Banknote,
    category: "Payments",
  },
  {
    value: "flutterwave",
    label: "Flutterwave",
    description: "Sync transactions, transfers & settlements from Flutterwave",
    icon: Wallet,
    category: "Payments",
  },
  {
    value: "mtn_momo",
    label: "MTN Mobile Money",
    description: "Sync collections, disbursements & transfers from MTN MoMo",
    icon: Smartphone,
    category: "Payments",
  },
  {
    value: "mpesa",
    label: "M-Pesa",
    description: "Sync transactions & balances from Safaricom M-Pesa",
    icon: Smartphone,
    category: "Payments",
  },
  // --- Accounting ---
  {
    value: "xero",
    label: "Xero",
    description: "Connect to Xero accounting via OAuth",
    icon: FileSpreadsheet,
    category: "Accounting",
  },
  // --- Banking ---
  {
    value: "open_banking",
    label: "Open Banking",
    description: "Connect your UK bank account via Open Banking",
    icon: Building2,
    category: "Banking",
  },
  {
    value: "hmrc_mtd",
    label: "HMRC MTD",
    description: "Connect to HMRC Making Tax Digital",
    icon: Landmark,
    category: "Banking",
  },
  // --- Databases ---
  {
    value: "postgresql",
    label: "PostgreSQL",
    description: "Connect to PostgreSQL database",
    icon: Database,
    category: "Databases",
  },
  {
    value: "mysql",
    label: "MySQL",
    description: "Connect to MySQL database",
    icon: Database,
    category: "Databases",
  },
  {
    value: "mongodb",
    label: "MongoDB",
    description: "Connect to MongoDB database",
    icon: Database,
    category: "Databases",
  },
  // --- Files ---
  {
    value: "csv",
    label: "CSV File",
    description: "Upload CSV files",
    icon: FileText,
    category: "Files",
  },
  {
    value: "local",
    label: "Local File",
    description: "Import from local filesystem",
    icon: Laptop,
    category: "Files",
  },
  {
    value: "http_file",
    label: "HTTP / Public File",
    description:
      "Sync CSV, JSONL or Parquet files from any public URL — open data, government datasets, exports",
    icon: Globe,
    category: "Files",
    isNew: true,
  },
  // --- APIs ---
  {
    value: "google_sheets",
    label: "Google Sheets",
    description: "Read data from Google Spreadsheets",
    icon: Sheet,
    category: "APIs",
  },
  {
    value: "rest_api",
    label: "REST API",
    description: "Connect to REST API endpoint",
    icon: Cloud,
    category: "APIs",
  },
  {
    value: "rest_api_declarative",
    label: "REST API (Custom)",
    description:
      "Connect to any REST API. Configure endpoints, auth, and incremental sync — no code needed",
    icon: Zap,
    category: "APIs",
    isNew: true,
  },
  // --- Messaging ---
  {
    value: "whatsapp",
    label: "WhatsApp Business",
    description: "Sync messages and contacts from WhatsApp Business API",
    icon: MessageCircle,
    category: "Messaging",
  },
];

// Group source types by category, preserving order of first appearance
const CATEGORY_ORDER = [
  "Payments",
  "Accounting",
  "Banking",
  "Databases",
  "Files",
  "APIs",
  "Messaging",
];

const groupedSourceTypes = CATEGORY_ORDER.reduce<Record<string, SourceType[]>>(
  (acc, category) => {
    acc[category] = SOURCE_TYPES.filter((st) => st.category === category);
    return acc;
  },
  {}
);

export default function BasicInfoStep({ data, onUpdate }: BasicInfoStepProps) {
  const selectedSourceType = SOURCE_TYPES.find((st) => st.value === data.source_type);

  return (
    <div className="space-y-6">
      <div className="space-y-2">
        <Label htmlFor="name">
          Source Name <span className="text-destructive">*</span>
        </Label>
        <Input
          id="name"
          placeholder="e.g., Production PostgreSQL"
          value={data.name}
          onChange={(e) => onUpdate({ name: e.target.value })}
        />
        <p className="text-xs text-muted-foreground">
          A descriptive name for this data source
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="description">Description</Label>
        <Textarea
          id="description"
          placeholder="Optional description of this data source"
          value={data.description}
          onChange={(e) => onUpdate({ description: e.target.value })}
          rows={3}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="source_type">
          Source Type <span className="text-destructive">*</span>
        </Label>
        <Select
          value={data.source_type}
          onValueChange={(value) =>
            onUpdate({ source_type: value, config: {} })
          }
        >
          <SelectTrigger id="source_type">
            <SelectValue placeholder="Select a source type" />
          </SelectTrigger>
          <SelectContent>
            {CATEGORY_ORDER.map((category) => (
              <SelectGroup key={category}>
                <SelectLabel>{category}</SelectLabel>
                {groupedSourceTypes[category].map((sourceType) => {
                  const Icon = sourceType.icon;
                  return (
                    <SelectItem key={sourceType.value} value={sourceType.value}>
                      <div className="flex items-center gap-2">
                        <Icon className="h-4 w-4 shrink-0 text-muted-foreground" />
                        <div className="flex items-center gap-1.5">
                          <span className="font-medium">{sourceType.label}</span>
                          {sourceType.isNew && (
                            <Badge
                              variant="secondary"
                              className="h-4 px-1 text-[10px] font-semibold bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-0"
                            >
                              New
                            </Badge>
                          )}
                        </div>
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectGroup>
            ))}
          </SelectContent>
        </Select>
        {selectedSourceType && (
          <p className="text-xs text-muted-foreground">
            {selectedSourceType.description}
          </p>
        )}
      </div>
    </div>
  );
}
