"use client";

import { useState } from "react";
import Link from "next/link";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  ArrowLeft,
  Search,
  Database,
  CreditCard,
  Building2,
  FileSpreadsheet,
  Landmark,
  CheckCircle2,
  XCircle,
  Smartphone,
  MessageCircle,
  Plug,
} from "lucide-react";

interface Connector {
  name: string;
  display_name: string;
  description: string;
  category: string;
  version: string;
  coming_soon?: boolean;
  capabilities: {
    incremental: boolean;
    schema_discovery: boolean;
    connection_test: boolean;
    auth_types: string[];
  };
}

// Static connector data for the public marketing page.
// Only list connectors that exist in backend/connectors/ — anything on the
// roadmap must carry coming_soon: true. Africa-first ordering.
const staticConnectors: Connector[] = [
  {
    name: "paystack",
    display_name: "Paystack",
    description: "African payment processing data — transactions, customers, settlements, and refunds.",
    category: "payment",
    version: "1.0.0",
    capabilities: {
      incremental: true,
      schema_discovery: true,
      connection_test: true,
      auth_types: ["api_key"],
    },
  },
  {
    name: "flutterwave",
    display_name: "Flutterwave",
    description: "Pan-African payments — transactions, transfers, and settlement data across 30+ countries.",
    category: "payment",
    version: "1.0.0",
    capabilities: {
      incremental: true,
      schema_discovery: true,
      connection_test: true,
      auth_types: ["api_key"],
    },
  },
  {
    name: "mpesa",
    display_name: "M-Pesa",
    description: "Safaricom M-Pesa transactions and settlement data for businesses operating in Kenya.",
    category: "mobile_money",
    version: "1.0.0",
    capabilities: {
      incremental: true,
      schema_discovery: true,
      connection_test: true,
      auth_types: ["api_key"],
    },
  },
  {
    name: "mtn_momo",
    display_name: "MTN Mobile Money",
    description: "MTN MoMo wallet and collection data — the dominant mobile money rail in Ghana and beyond.",
    category: "mobile_money",
    version: "1.0.0",
    capabilities: {
      incremental: true,
      schema_discovery: true,
      connection_test: true,
      auth_types: ["api_key"],
    },
  },
  {
    name: "whatsapp_business",
    display_name: "WhatsApp Business",
    description: "Customer conversations and order messages from the channel African SMEs actually sell on.",
    category: "messaging",
    version: "1.0.0",
    capabilities: {
      incremental: true,
      schema_discovery: true,
      connection_test: true,
      auth_types: ["api_key"],
    },
  },
  {
    name: "stripe",
    display_name: "Stripe",
    description: "Payment data, customers, invoices, and subscriptions — for France and EU operations.",
    category: "payment",
    version: "1.0.0",
    capabilities: {
      incremental: true,
      schema_discovery: true,
      connection_test: true,
      auth_types: ["api_key"],
    },
  },
  {
    name: "mono",
    display_name: "Mono",
    description: "African open banking — connect Nigerian bank accounts for transactions and account data.",
    category: "banking",
    version: "1.0.0",
    capabilities: {
      incremental: true,
      schema_discovery: true,
      connection_test: true,
      auth_types: ["api_key"],
    },
  },
  {
    name: "truelayer",
    display_name: "TrueLayer",
    description: "EU open banking — secure access to bank accounts and transaction data in Europe.",
    category: "banking",
    version: "1.0.0",
    capabilities: {
      incremental: true,
      schema_discovery: true,
      connection_test: true,
      auth_types: ["oauth2"],
    },
  },
  {
    name: "xero",
    display_name: "Xero",
    description: "Invoices, contacts, bank transactions, and account data from Xero.",
    category: "accounting",
    version: "1.0.0",
    capabilities: {
      incremental: true,
      schema_discovery: true,
      connection_test: true,
      auth_types: ["oauth2"],
    },
  },
  {
    name: "quickbooks",
    display_name: "QuickBooks Online",
    description: "Invoices, customers, payments, and financial reports from QuickBooks.",
    category: "accounting",
    version: "1.0.0",
    coming_soon: true,
    capabilities: {
      incremental: true,
      schema_discovery: true,
      connection_test: true,
      auth_types: ["oauth2"],
    },
  },
  {
    name: "sage",
    display_name: "Sage Business Cloud",
    description: "Contacts, invoices, and ledger entries from Sage.",
    category: "accounting",
    version: "1.0.0",
    coming_soon: true,
    capabilities: {
      incremental: true,
      schema_discovery: true,
      connection_test: true,
      auth_types: ["oauth2"],
    },
  },
  {
    name: "google_sheets",
    display_name: "Google Sheets",
    description: "Sync spreadsheets directly — where most SME record-keeping actually lives.",
    category: "file",
    version: "1.0.0",
    capabilities: {
      incremental: false,
      schema_discovery: true,
      connection_test: true,
      auth_types: ["oauth2"],
    },
  },
  {
    name: "rest_api",
    display_name: "REST API",
    description: "Connect any REST API — bring data from internal systems and custom tools.",
    category: "api",
    version: "1.0.0",
    capabilities: {
      incremental: true,
      schema_discovery: false,
      connection_test: true,
      auth_types: ["api_key", "oauth2", "none"],
    },
  },
  {
    name: "postgres",
    display_name: "PostgreSQL",
    description: "Connect to PostgreSQL databases to extract and sync table data.",
    category: "database",
    version: "1.0.0",
    capabilities: {
      incremental: true,
      schema_discovery: true,
      connection_test: true,
      auth_types: ["credentials"],
    },
  },
  {
    name: "mysql",
    display_name: "MySQL",
    description: "Extract data from MySQL databases with support for incremental syncs.",
    category: "database",
    version: "1.0.0",
    capabilities: {
      incremental: true,
      schema_discovery: true,
      connection_test: true,
      auth_types: ["credentials"],
    },
  },
  {
    name: "mongodb",
    display_name: "MongoDB",
    description: "Connect to MongoDB for document-based data extraction and sync.",
    category: "database",
    version: "1.0.0",
    capabilities: {
      incremental: true,
      schema_discovery: true,
      connection_test: true,
      auth_types: ["credentials"],
    },
  },
  {
    name: "csv",
    display_name: "CSV Upload",
    description: "Upload CSV files directly for quick data imports and one-time loads.",
    category: "file",
    version: "1.0.0",
    capabilities: {
      incremental: false,
      schema_discovery: true,
      connection_test: false,
      auth_types: ["none"],
    },
  },
];

const categoryIcons: Record<string, any> = {
  payment: CreditCard,
  mobile_money: Smartphone,
  messaging: MessageCircle,
  accounting: Building2,
  banking: Landmark,
  database: Database,
  file: FileSpreadsheet,
  api: Plug,
};

const categoryLabels: Record<string, string> = {
  payment: "Payments",
  mobile_money: "Mobile Money",
  messaging: "Messaging",
  accounting: "Accounting",
  banking: "Banking",
  database: "Databases",
  file: "Files & Sheets",
  api: "APIs",
};

const categoryColors: Record<string, string> = {
  payment: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  mobile_money: "bg-amber-100 text-amber-800 dark:bg-amber-900 dark:text-amber-200",
  messaging: "bg-teal-100 text-teal-800 dark:bg-teal-900 dark:text-teal-200",
  accounting: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  banking: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  database: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200",
  file: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
  api: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
};

export default function ConnectorsPage() {
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  const categories = Array.from(new Set(staticConnectors.map((c) => c.category)));

  const filteredConnectors = staticConnectors.filter((connector) => {
    const matchesSearch =
      connector.display_name.toLowerCase().includes(search.toLowerCase()) ||
      connector.description.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = !selectedCategory || connector.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container flex h-16 items-center justify-between">
          <Link href="/integrations">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Integrations
            </Button>
          </Link>
          <Link href="/">
            <span className="text-xl font-bold">UnifiedLayer</span>
          </Link>
        </div>
      </header>

      <main className="container py-8">
        {/* Title */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold tracking-tight mb-2">
            Available Integrations
          </h1>
          <p className="text-muted-foreground">
            Pre-built connectors for popular data sources. Connect in minutes, no coding required.
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search integrations..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="flex gap-2 flex-wrap">
            <Button
              variant={selectedCategory === null ? "default" : "outline"}
              size="sm"
              onClick={() => setSelectedCategory(null)}
            >
              All
            </Button>
            {categories.map((category) => (
              <Button
                key={category}
                variant={selectedCategory === category ? "default" : "outline"}
                size="sm"
                onClick={() => setSelectedCategory(category)}
              >
                {categoryLabels[category] ||
                  category.charAt(0).toUpperCase() + category.slice(1)}
              </Button>
            ))}
          </div>
        </div>

        {/* Connectors Grid */}
        {filteredConnectors.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No integrations found</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredConnectors.map((connector) => {
              const CategoryIcon = categoryIcons[connector.category] || Database;
              return (
                <Card
                  key={connector.name}
                  className={`flex flex-col hover:shadow-md transition-shadow ${
                    connector.coming_soon ? "opacity-75" : ""
                  }`}
                >
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                          <CategoryIcon className="h-5 w-5 text-primary" />
                        </div>
                        <div>
                          <CardTitle className="text-lg">
                            {connector.display_name}
                          </CardTitle>
                          <Badge
                            variant="secondary"
                            className={categoryColors[connector.category] || ""}
                          >
                            {categoryLabels[connector.category] || connector.category}
                          </Badge>
                        </div>
                      </div>
                      {connector.coming_soon && (
                        <Badge variant="outline">Coming soon</Badge>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="flex-1 flex flex-col">
                    <CardDescription className="flex-1 mb-4">
                      {connector.description}
                    </CardDescription>

                    {/* Capabilities */}
                    <div className="space-y-2 text-sm">
                      <div className="flex flex-wrap gap-3">
                        <div className="flex items-center gap-1">
                          {connector.capabilities.incremental ? (
                            <CheckCircle2 className="h-3 w-3 text-green-600" />
                          ) : (
                            <XCircle className="h-3 w-3 text-muted-foreground" />
                          )}
                          <span className="text-xs">Incremental Sync</span>
                        </div>
                        <div className="flex items-center gap-1">
                          {connector.capabilities.schema_discovery ? (
                            <CheckCircle2 className="h-3 w-3 text-green-600" />
                          ) : (
                            <XCircle className="h-3 w-3 text-muted-foreground" />
                          )}
                          <span className="text-xs">Auto-Discovery</span>
                        </div>
                        <div className="flex items-center gap-1">
                          {connector.capabilities.connection_test ? (
                            <CheckCircle2 className="h-3 w-3 text-green-600" />
                          ) : (
                            <XCircle className="h-3 w-3 text-muted-foreground" />
                          )}
                          <span className="text-xs">Test Connection</span>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}

        {/* Stats */}
        <div className="mt-8 pt-8 border-t">
          <div className="flex items-center justify-center gap-8 text-sm text-muted-foreground">
            <div>
              <span className="font-bold text-foreground">{staticConnectors.length}</span> integrations
            </div>
            <div>
              <span className="font-bold text-foreground">{categories.length}</span> categories
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="mt-12 text-center">
          <p className="text-muted-foreground mb-4">
            Ready to connect your data?
          </p>
          <Link href="/request-access">
            <Button size="lg">Request Access</Button>
          </Link>
        </div>
      </main>
    </div>
  );
}
