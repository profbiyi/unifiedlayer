"use client";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SourceWizardData } from "@/app/(dashboard)/sources/new/page";
import { Database, FileText, Cloud, Laptop, CreditCard, Sheet, Banknote, FileSpreadsheet, Landmark, Building2, Smartphone, Wallet, MessageCircle } from "lucide-react";

interface BasicInfoStepProps {
  data: SourceWizardData;
  onUpdate: (updates: Partial<SourceWizardData>) => void;
}

const SOURCE_TYPES = [
  {
    value: "postgresql",
    label: "PostgreSQL",
    description: "Connect to PostgreSQL database",
    icon: Database,
  },
  {
    value: "mysql",
    label: "MySQL",
    description: "Connect to MySQL database",
    icon: Database,
  },
  {
    value: "mongodb",
    label: "MongoDB",
    description: "Connect to MongoDB database",
    icon: Database,
  },
  {
    value: "paystack",
    label: "Paystack",
    description: "Sync transactions, customers & settlements from Paystack",
    icon: CreditCard,
  },
  {
    value: "google_sheets",
    label: "Google Sheets",
    description: "Read data from Google Spreadsheets",
    icon: Sheet,
  },
  {
    value: "rest_api",
    label: "REST API",
    description: "Connect to REST API endpoint",
    icon: Cloud,
  },
  {
    value: "csv",
    label: "CSV File",
    description: "Upload CSV files",
    icon: FileText,
  },
  {
    value: "local",
    label: "Local File",
    description: "Import from local filesystem",
    icon: Laptop,
  },
  {
    value: "gocardless",
    label: "GoCardless",
    description: "Sync payments, mandates & customers from GoCardless",
    icon: Banknote,
  },
  {
    value: "xero",
    label: "Xero",
    description: "Connect to Xero accounting via OAuth",
    icon: FileSpreadsheet,
  },
  {
    value: "open_banking",
    label: "Open Banking",
    description: "Connect your UK bank account via Open Banking",
    icon: Building2,
  },
  {
    value: "hmrc_mtd",
    label: "HMRC MTD",
    description: "Connect to HMRC Making Tax Digital",
    icon: Landmark,
  },
  {
    value: "flutterwave",
    label: "Flutterwave",
    description: "Sync transactions, transfers & settlements from Flutterwave",
    icon: Wallet,
  },
  {
    value: "mtn_momo",
    label: "MTN Mobile Money",
    description: "Sync collections, disbursements & transfers from MTN MoMo",
    icon: Smartphone,
  },
  {
    value: "mpesa",
    label: "M-Pesa",
    description: "Sync transactions & balances from Safaricom M-Pesa",
    icon: Smartphone,
  },
  {
    value: "whatsapp",
    label: "WhatsApp Business",
    description: "Sync messages and contacts from WhatsApp Business API",
    icon: MessageCircle,
  },
];

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
            {SOURCE_TYPES.map((sourceType) => {
              const Icon = sourceType.icon;
              return (
                <SelectItem key={sourceType.value} value={sourceType.value}>
                  <div className="flex items-center gap-2">
                    <Icon className="h-4 w-4 text-muted-foreground" />
                    <div>
                      <p className="font-medium">{sourceType.label}</p>
                      <p className="text-xs text-muted-foreground">
                        {sourceType.description}
                      </p>
                    </div>
                  </div>
                </SelectItem>
              );
            })}
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
