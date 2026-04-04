/**
 * Centralized connector icon, color, and metadata registry.
 *
 * Used by ConnectorCard, ConnectorPicker, source/destination listings,
 * and the pipeline builder to render consistent visuals across the app.
 */
import {
  Database,
  CreditCard,
  FileSpreadsheet,
  Globe,
  HardDrive,
  Smartphone,
  Landmark,
  Receipt,
  FileText,
  CloudUpload,
  MessageCircle,
  Banknote,
  Building2,
  Warehouse,
  Server,
  FileUp,
  Link2,
  Table2,
  type LucideIcon,
} from "lucide-react";

// ── Source connector definitions ────────────────────────────────────

export interface ConnectorMeta {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
  color: string;        // Tailwind bg class e.g. "bg-purple-500"
  textColor: string;    // Tailwind text class for contrast
  category: ConnectorCategory;
  fields: FieldDef[];   // Credential fields needed
  popular?: boolean;
  isNew?: boolean;
}

export interface FieldDef {
  key: string;
  label: string;
  type: "text" | "password" | "number" | "textarea" | "select";
  placeholder?: string;
  required?: boolean;
  defaultValue?: string | number;
  options?: { value: string; label: string }[];
  helpText?: string;
}

export type ConnectorCategory =
  | "payments"
  | "accounting"
  | "banking"
  | "database"
  | "files"
  | "apis"
  | "messaging";

export const CATEGORY_META: Record<ConnectorCategory, { label: string; color: string }> = {
  payments:   { label: "Payments",   color: "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400" },
  accounting: { label: "Accounting", color: "bg-blue-500/10 text-blue-600 dark:text-blue-400" },
  banking:    { label: "Banking",    color: "bg-purple-500/10 text-purple-600 dark:text-purple-400" },
  database:   { label: "Database",   color: "bg-orange-500/10 text-orange-600 dark:text-orange-400" },
  files:      { label: "Files",      color: "bg-gray-500/10 text-gray-600 dark:text-gray-400" },
  apis:       { label: "APIs",       color: "bg-teal-500/10 text-teal-600 dark:text-teal-400" },
  messaging:  { label: "Messaging",  color: "bg-green-500/10 text-green-600 dark:text-green-400" },
};

// ── Source Connectors ───────────────────────────────────────────────

export const SOURCE_CONNECTORS: ConnectorMeta[] = [
  // ── Payments ──
  {
    id: "stripe",
    name: "Stripe",
    description: "Sync payments, customers, subscriptions and invoices",
    icon: CreditCard,
    color: "bg-purple-500",
    textColor: "text-white",
    category: "payments",
    popular: true,
    fields: [
      { key: "api_key", label: "Secret Key", type: "password", placeholder: "sk_live_...", required: true, helpText: "Find this in Stripe Dashboard → Developers → API keys" },
    ],
  },
  {
    id: "paystack",
    name: "Paystack",
    description: "Transactions, customers, settlements for Africa",
    icon: Banknote,
    color: "bg-teal-500",
    textColor: "text-white",
    category: "payments",
    popular: true,
    fields: [
      { key: "api_key", label: "Secret Key", type: "password", placeholder: "sk_live_...", required: true, helpText: "Settings → API Keys & Webhooks" },
    ],
  },
  {
    id: "flutterwave",
    name: "Flutterwave",
    description: "Transactions, transfers and settlements",
    icon: Banknote,
    color: "bg-yellow-500",
    textColor: "text-white",
    category: "payments",
    fields: [
      { key: "api_key", label: "Secret Key", type: "password", placeholder: "FLWSECK-...", required: true },
    ],
  },
  {
    id: "gocardless",
    name: "GoCardless",
    description: "Direct debit payments, mandates and payouts",
    icon: Landmark,
    color: "bg-sky-500",
    textColor: "text-white",
    category: "payments",
    fields: [
      { key: "access_token", label: "Access Token", type: "password", required: true },
      { key: "environment", label: "Environment", type: "select", required: true, defaultValue: "live", options: [{ value: "live", label: "Live" }, { value: "sandbox", label: "Sandbox" }] },
    ],
  },
  {
    id: "mtn_momo",
    name: "MTN MoMo",
    description: "Mobile Money collections and disbursements",
    icon: Smartphone,
    color: "bg-yellow-400",
    textColor: "text-black",
    category: "payments",
    fields: [
      { key: "subscription_key", label: "Subscription Key", type: "password", required: true },
      { key: "api_user", label: "API User", type: "text", required: true },
      { key: "api_key", label: "API Key", type: "password", required: true },
      { key: "environment", label: "Environment", type: "select", required: true, defaultValue: "sandbox", options: [{ value: "sandbox", label: "Sandbox" }, { value: "production", label: "Production" }] },
    ],
  },
  {
    id: "mpesa",
    name: "M-Pesa",
    description: "M-Pesa transactions and balances",
    icon: Smartphone,
    color: "bg-green-600",
    textColor: "text-white",
    category: "payments",
    fields: [
      { key: "consumer_key", label: "Consumer Key", type: "password", required: true },
      { key: "consumer_secret", label: "Consumer Secret", type: "password", required: true },
      { key: "environment", label: "Environment", type: "select", required: true, defaultValue: "sandbox", options: [{ value: "sandbox", label: "Sandbox" }, { value: "production", label: "Production" }] },
    ],
  },

  // ── Accounting ──
  {
    id: "xero",
    name: "Xero",
    description: "Accounting data — accounts, contacts, invoices",
    icon: Receipt,
    color: "bg-blue-500",
    textColor: "text-white",
    category: "accounting",
    popular: true,
    fields: [
      { key: "client_id", label: "Client ID", type: "text", required: true },
      { key: "client_secret", label: "Client Secret", type: "password", required: true },
    ],
  },

  // ── Banking ──
  {
    id: "open_banking",
    name: "Open Banking",
    description: "UK bank accounts via TrueLayer",
    icon: Landmark,
    color: "bg-indigo-500",
    textColor: "text-white",
    category: "banking",
    fields: [
      { key: "client_id", label: "Client ID", type: "text", required: true },
      { key: "client_secret", label: "Client Secret", type: "password", required: true },
    ],
  },
  {
    id: "hmrc_mtd",
    name: "HMRC MTD",
    description: "Making Tax Digital — UK VAT & tax data",
    icon: Building2,
    color: "bg-red-600",
    textColor: "text-white",
    category: "banking",
    fields: [
      { key: "client_id", label: "Client ID", type: "text", required: true },
      { key: "client_secret", label: "Client Secret", type: "password", required: true },
    ],
  },

  // ── Databases ──
  {
    id: "postgresql",
    name: "PostgreSQL",
    description: "Connect to any PostgreSQL database with CDC support",
    icon: Database,
    color: "bg-blue-700",
    textColor: "text-white",
    category: "database",
    popular: true,
    fields: [
      { key: "host", label: "Host", type: "text", placeholder: "db.example.com", required: true },
      { key: "port", label: "Port", type: "number", placeholder: "5432", required: true, defaultValue: 5432 },
      { key: "database", label: "Database", type: "text", placeholder: "my_database", required: true },
      { key: "username", label: "Username", type: "text", required: true },
      { key: "password", label: "Password", type: "password", required: true },
      { key: "schema", label: "Schema", type: "text", placeholder: "public", defaultValue: "public" },
    ],
  },
  {
    id: "mysql",
    name: "MySQL",
    description: "Connect to MySQL or MariaDB databases",
    icon: Database,
    color: "bg-orange-600",
    textColor: "text-white",
    category: "database",
    fields: [
      { key: "host", label: "Host", type: "text", placeholder: "db.example.com", required: true },
      { key: "port", label: "Port", type: "number", placeholder: "3306", required: true, defaultValue: 3306 },
      { key: "database", label: "Database", type: "text", required: true },
      { key: "username", label: "Username", type: "text", required: true },
      { key: "password", label: "Password", type: "password", required: true },
    ],
  },
  {
    id: "mongodb",
    name: "MongoDB",
    description: "Sync collections from MongoDB",
    icon: Database,
    color: "bg-green-700",
    textColor: "text-white",
    category: "database",
    fields: [
      { key: "connection_string", label: "Connection String", type: "password", placeholder: "mongodb+srv://...", required: true },
      { key: "database", label: "Database", type: "text", required: true },
    ],
  },

  // ── Files ──
  {
    id: "google_sheets",
    name: "Google Sheets",
    description: "Import data from Google Spreadsheets",
    icon: FileSpreadsheet,
    color: "bg-green-500",
    textColor: "text-white",
    category: "files",
    fields: [
      { key: "spreadsheet_id", label: "Spreadsheet ID", type: "text", required: true, helpText: "The ID from your Google Sheets URL" },
      { key: "credentials_json", label: "Service Account JSON", type: "textarea", required: true, helpText: "Paste the full JSON key from Google Cloud Console" },
    ],
  },
  {
    id: "csv",
    name: "CSV File",
    description: "Upload and sync CSV files",
    icon: FileText,
    color: "bg-gray-500",
    textColor: "text-white",
    category: "files",
    fields: [
      { key: "file_path", label: "File Path", type: "text", required: true },
      { key: "delimiter", label: "Delimiter", type: "text", defaultValue: ",", placeholder: "," },
    ],
  },
  {
    id: "local",
    name: "Local File",
    description: "Import from local filesystem",
    icon: FileUp,
    color: "bg-gray-600",
    textColor: "text-white",
    category: "files",
    fields: [
      { key: "path", label: "Directory Path", type: "text", placeholder: "/data/exports/", required: true },
      { key: "file_pattern", label: "File Pattern", type: "text", placeholder: "*.csv", defaultValue: "*.csv" },
    ],
  },
  {
    id: "http_file",
    name: "HTTP / Public File",
    description: "Sync CSV, JSONL or Parquet from any public URL",
    icon: Globe,
    color: "bg-indigo-500",
    textColor: "text-white",
    category: "files",
    isNew: true,
    fields: [
      { key: "url", label: "File URL", type: "text", placeholder: "https://data.gov.uk/dataset.csv", required: true },
      { key: "file_format", label: "Format", type: "select", defaultValue: "auto", options: [{ value: "auto", label: "Auto-detect" }, { value: "csv", label: "CSV" }, { value: "jsonl", label: "JSONL" }, { value: "parquet", label: "Parquet" }] },
      { key: "table_name", label: "Table Name", type: "text", placeholder: "my_data" },
    ],
  },

  // ── APIs ──
  {
    id: "rest_api",
    name: "REST API",
    description: "Connect to any REST API with pagination support",
    icon: Globe,
    color: "bg-teal-600",
    textColor: "text-white",
    category: "apis",
    fields: [
      { key: "base_url", label: "Base URL", type: "text", placeholder: "https://api.example.com/v1", required: true },
      { key: "auth_type", label: "Auth Type", type: "select", required: true, defaultValue: "none", options: [{ value: "none", label: "No Auth" }, { value: "bearer", label: "Bearer Token" }, { value: "api_key", label: "API Key" }, { value: "basic", label: "Basic Auth" }] },
      { key: "auth_token", label: "Auth Token / API Key", type: "password", helpText: "Required if auth type is Bearer or API Key" },
    ],
  },

  {
    id: "rest_api_declarative",
    name: "REST API (Custom)",
    description: "Connect to any REST API — configure endpoints, auth, and pagination",
    icon: Link2,
    color: "bg-violet-600",
    textColor: "text-white",
    category: "apis",
    isNew: true,
    fields: [
      { key: "base_url", label: "Base URL", type: "text", placeholder: "https://api.example.com/v1", required: true },
      { key: "auth_type", label: "Auth Type", type: "select", required: true, defaultValue: "none", options: [{ value: "none", label: "No Auth" }, { value: "bearer", label: "Bearer Token" }, { value: "api_key", label: "API Key" }, { value: "basic", label: "Basic Auth" }] },
      { key: "auth_token", label: "Auth Token / API Key", type: "password", helpText: "Required if auth type is Bearer or API Key" },
    ],
  },

  // ── Messaging ──
  {
    id: "whatsapp",
    name: "WhatsApp Business",
    description: "Sync WhatsApp Business messages and contacts",
    icon: MessageCircle,
    color: "bg-green-500",
    textColor: "text-white",
    category: "messaging",
    isNew: true,
    fields: [
      { key: "access_token", label: "Access Token", type: "password", required: true },
      { key: "phone_number_id", label: "Phone Number ID", type: "text", required: true },
      { key: "business_account_id", label: "Business Account ID", type: "text", required: true },
    ],
  },
];

// ── Destination Connectors ──────────────────────────────────────────

export interface DestinationMeta {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
  color: string;
  textColor: string;
  fields: FieldDef[];
  popular?: boolean;
}

export const DESTINATION_CONNECTORS: DestinationMeta[] = [
  {
    id: "postgres",
    name: "PostgreSQL",
    description: "Load data into any PostgreSQL database",
    icon: Database,
    color: "bg-blue-700",
    textColor: "text-white",
    popular: true,
    fields: [
      { key: "host", label: "Host", type: "text", placeholder: "db.example.com", required: true },
      { key: "port", label: "Port", type: "number", defaultValue: 5432, required: true },
      { key: "database", label: "Database", type: "text", required: true },
      { key: "username", label: "Username", type: "text", required: true },
      { key: "password", label: "Password", type: "password", required: true },
    ],
  },
  {
    id: "bigquery",
    name: "BigQuery",
    description: "Google BigQuery data warehouse",
    icon: Warehouse,
    color: "bg-blue-500",
    textColor: "text-white",
    popular: true,
    fields: [
      { key: "project_id", label: "Project ID", type: "text", required: true },
      { key: "dataset", label: "Dataset", type: "text", required: true },
      { key: "credentials_json", label: "Service Account JSON", type: "textarea", required: true },
    ],
  },
  {
    id: "snowflake",
    name: "Snowflake",
    description: "Snowflake cloud data warehouse",
    icon: Server,
    color: "bg-sky-500",
    textColor: "text-white",
    popular: true,
    fields: [
      { key: "account", label: "Account", type: "text", placeholder: "org-account", required: true },
      { key: "warehouse", label: "Warehouse", type: "text", required: true },
      { key: "database", label: "Database", type: "text", required: true },
      { key: "schema", label: "Schema", type: "text", defaultValue: "PUBLIC" },
      { key: "username", label: "Username", type: "text", required: true },
      { key: "password", label: "Password", type: "password", required: true },
    ],
  },
  {
    id: "duckdb",
    name: "DuckDB",
    description: "Fast local analytics database — great for testing",
    icon: Database,
    color: "bg-yellow-500",
    textColor: "text-black",
    fields: [
      { key: "database_path", label: "Database Path", type: "text", placeholder: "/data/analytics.duckdb", required: true },
    ],
  },
  {
    id: "redshift",
    name: "Redshift",
    description: "Amazon Redshift data warehouse",
    icon: Server,
    color: "bg-red-600",
    textColor: "text-white",
    fields: [
      { key: "host", label: "Host", type: "text", required: true },
      { key: "port", label: "Port", type: "number", defaultValue: 5439, required: true },
      { key: "database", label: "Database", type: "text", required: true },
      { key: "username", label: "Username", type: "text", required: true },
      { key: "password", label: "Password", type: "password", required: true },
    ],
  },
  {
    id: "s3",
    name: "Amazon S3",
    description: "Store data as Parquet files in S3",
    icon: CloudUpload,
    color: "bg-orange-500",
    textColor: "text-white",
    fields: [
      { key: "bucket_name", label: "Bucket Name", type: "text", required: true },
      { key: "region", label: "Region", type: "text", defaultValue: "us-east-1", required: true },
      { key: "access_key_id", label: "Access Key ID", type: "text", required: true },
      { key: "secret_access_key", label: "Secret Access Key", type: "password", required: true },
    ],
  },
  {
    id: "gcs",
    name: "Google Cloud Storage",
    description: "Store data as Parquet files in GCS",
    icon: CloudUpload,
    color: "bg-blue-500",
    textColor: "text-white",
    fields: [
      { key: "bucket_name", label: "Bucket Name", type: "text", required: true },
      { key: "credentials_json", label: "Service Account JSON", type: "textarea", required: true },
    ],
  },
];

// ── Helpers ─────────────────────────────────────────────────────────

export function getSourceMeta(id: string): ConnectorMeta | undefined {
  return SOURCE_CONNECTORS.find((c) => c.id === id);
}

export function getDestinationMeta(id: string): DestinationMeta | undefined {
  return DESTINATION_CONNECTORS.find((c) => c.id === id);
}

export function getSourcesByCategory(category: ConnectorCategory): ConnectorMeta[] {
  return SOURCE_CONNECTORS.filter((c) => c.category === category);
}

export function getPopularSources(): ConnectorMeta[] {
  return SOURCE_CONNECTORS.filter((c) => c.popular);
}

export function getPopularDestinations(): DestinationMeta[] {
  return DESTINATION_CONNECTORS.filter((c) => c.popular);
}
