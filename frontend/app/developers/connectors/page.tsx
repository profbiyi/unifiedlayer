"use client";

import { useState, useEffect } from "react";
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
  Receipt,
  Loader2,
  CheckCircle2,
  XCircle,
} from "lucide-react";

interface Connector {
  name: string;
  display_name: string;
  description: string;
  icon: string;
  category: string;
  version: string;
  author: string;
  capabilities: {
    incremental: boolean;
    cdc: boolean;
    schema_discovery: boolean;
    connection_test: boolean;
    auth_types: string[];
  };
}

const categoryIcons: Record<string, any> = {
  payment: CreditCard,
  accounting: Building2,
  banking: Landmark,
  tax: Receipt,
  database: Database,
  file: FileSpreadsheet,
};

const categoryColors: Record<string, string> = {
  payment: "bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200",
  accounting: "bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200",
  banking: "bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200",
  tax: "bg-orange-100 text-orange-800 dark:bg-orange-900 dark:text-orange-200",
  database: "bg-cyan-100 text-cyan-800 dark:bg-cyan-900 dark:text-cyan-200",
  file: "bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-200",
};

export default function ConnectorsPage() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);

  useEffect(() => {
    async function fetchConnectors() {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/connectors/`);
        const data = await res.json();
        setConnectors(data.connectors || []);
      } catch (error) {
        console.error("Failed to fetch connectors:", error);
      } finally {
        setLoading(false);
      }
    }
    fetchConnectors();
  }, []);

  const categories = Array.from(new Set(connectors.map((c) => c.category)));

  const filteredConnectors = connectors.filter((connector) => {
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
          <Link href="/developers">
            <Button variant="ghost" size="sm">
              <ArrowLeft className="mr-2 h-4 w-4" />
              Back to Developers
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
            Available Connectors
          </h1>
          <p className="text-muted-foreground">
            Pre-built connectors for popular data sources. Each connector supports
            schema discovery, connection testing, and seamless integration with pipelines.
          </p>
        </div>

        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search connectors..."
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
                {category.charAt(0).toUpperCase() + category.slice(1)}
              </Button>
            ))}
          </div>
        </div>

        {/* Connectors Grid */}
        {loading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : filteredConnectors.length === 0 ? (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No connectors found</p>
          </div>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {filteredConnectors.map((connector) => {
              const CategoryIcon = categoryIcons[connector.category] || Database;
              return (
                <Card key={connector.name} className="flex flex-col">
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
                            {connector.category}
                          </Badge>
                        </div>
                      </div>
                      <Badge variant="outline" className="text-xs">
                        v{connector.version}
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="flex-1 flex flex-col">
                    <CardDescription className="flex-1 mb-4">
                      {connector.description}
                    </CardDescription>

                    {/* Capabilities */}
                    <div className="space-y-2 text-sm">
                      <p className="font-medium text-muted-foreground">Capabilities:</p>
                      <div className="flex flex-wrap gap-2">
                        <div className="flex items-center gap-1">
                          {connector.capabilities.incremental ? (
                            <CheckCircle2 className="h-3 w-3 text-green-600" />
                          ) : (
                            <XCircle className="h-3 w-3 text-muted-foreground" />
                          )}
                          <span className="text-xs">Incremental</span>
                        </div>
                        <div className="flex items-center gap-1">
                          {connector.capabilities.schema_discovery ? (
                            <CheckCircle2 className="h-3 w-3 text-green-600" />
                          ) : (
                            <XCircle className="h-3 w-3 text-muted-foreground" />
                          )}
                          <span className="text-xs">Schema Discovery</span>
                        </div>
                        <div className="flex items-center gap-1">
                          {connector.capabilities.connection_test ? (
                            <CheckCircle2 className="h-3 w-3 text-green-600" />
                          ) : (
                            <XCircle className="h-3 w-3 text-muted-foreground" />
                          )}
                          <span className="text-xs">Connection Test</span>
                        </div>
                      </div>
                      <div className="flex items-center gap-1 mt-2">
                        <span className="text-xs text-muted-foreground">Auth:</span>
                        {connector.capabilities.auth_types.map((auth) => (
                          <Badge key={auth} variant="outline" className="text-xs">
                            {auth}
                          </Badge>
                        ))}
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
              <span className="font-bold text-foreground">{connectors.length}</span> connectors
            </div>
            <div>
              <span className="font-bold text-foreground">{categories.length}</span> categories
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}
