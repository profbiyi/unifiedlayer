"use client";

import { useState, useEffect, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { SourceWizardData } from "@/app/(dashboard)/sources/new/page";
import {
  Search,
  ChevronRight,
  ChevronDown,
  Database,
  Table as TableIcon,
  Loader2,
  CheckSquare,
  Square,
  MinusSquare,
} from "lucide-react";
import api from "@/lib/api-client";

interface TableMetadata {
  schema: string;
  table: string;
  row_count?: number;
  size_mb?: number;
  columns?: Array<{
    name: string;
    type: string;
    nullable: boolean;
  }>;
}

interface SchemaGroup {
  schema: string;
  tables: TableMetadata[];
  expanded: boolean;
}

interface SchemaDiscoveryStepProps {
  data: SourceWizardData;
  onUpdate: (updates: Partial<SourceWizardData>) => void;
}

export default function SchemaDiscoveryStep({
  data,
  onUpdate,
}: SchemaDiscoveryStepProps) {
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const [schemaGroups, setSchemaGroups] = useState<SchemaGroup[]>([]);
  const [expandedSchemas, setExpandedSchemas] = useState<Set<string>>(new Set());

  useEffect(() => {
    if (data.connectionTested && !data.discoveredTables) {
      discoverSchema();
    } else if (data.discoveredTables) {
      // Group tables by schema
      groupTablesBySchema(data.discoveredTables);
    }
  }, [data.connectionTested]);

  const discoverSchema = async () => {
    setLoading(true);
    try {
      const response = await api.post("/sources/discovery/discover-schema", {
        source_type: data.source_type,
        config: data.config,
      });

      const tables: TableMetadata[] = response.data.tables || [];
      onUpdate({ discoveredTables: tables });
      groupTablesBySchema(tables);
    } catch (error: any) {
      // Schema discovery error handled by UI state
    } finally {
      setLoading(false);
    }
  };

  const groupTablesBySchema = (tables: TableMetadata[]) => {
    const grouped = tables.reduce((acc, table) => {
      const schema = table.schema || "default";
      if (!acc[schema]) {
        acc[schema] = [];
      }
      acc[schema].push(table);
      return acc;
    }, {} as Record<string, TableMetadata[]>);

    const groups: SchemaGroup[] = Object.entries(grouped).map(
      ([schema, tables]) => ({
        schema,
        tables,
        expanded: true,
      })
    );

    setSchemaGroups(groups);
    setExpandedSchemas(new Set(groups.map((g) => g.schema)));
  };

  const toggleSchema = (schema: string) => {
    setExpandedSchemas((prev) => {
      const next = new Set(prev);
      if (next.has(schema)) {
        next.delete(schema);
      } else {
        next.add(schema);
      }
      return next;
    });
  };

  const getTableId = (table: TableMetadata) => {
    return `${table.schema}.${table.table}`;
  };

  const isTableSelected = (table: TableMetadata) => {
    return data.selectedTables.has(getTableId(table));
  };

  const toggleTable = (table: TableMetadata) => {
    const tableId = getTableId(table);
    const newSelected = new Set(data.selectedTables);

    if (newSelected.has(tableId)) {
      newSelected.delete(tableId);
    } else {
      newSelected.add(tableId);
    }

    onUpdate({ selectedTables: newSelected });
  };

  const isSchemaFullySelected = (schema: string) => {
    const group = schemaGroups.find((g) => g.schema === schema);
    if (!group) return false;

    const filteredTables = group.tables.filter((table) =>
      matchesSearch(table)
    );

    return (
      filteredTables.length > 0 &&
      filteredTables.every((table) => isTableSelected(table))
    );
  };

  const isSchemaPartiallySelected = (schema: string) => {
    const group = schemaGroups.find((g) => g.schema === schema);
    if (!group) return false;

    const filteredTables = group.tables.filter((table) =>
      matchesSearch(table)
    );

    const selectedCount = filteredTables.filter((table) =>
      isTableSelected(table)
    ).length;

    return selectedCount > 0 && selectedCount < filteredTables.length;
  };

  const toggleSchemaSelection = (schema: string) => {
    const group = schemaGroups.find((g) => g.schema === schema);
    if (!group) return;

    const filteredTables = group.tables.filter((table) =>
      matchesSearch(table)
    );

    const allSelected = isSchemaFullySelected(schema);
    const newSelected = new Set(data.selectedTables);

    filteredTables.forEach((table) => {
      const tableId = getTableId(table);
      if (allSelected) {
        newSelected.delete(tableId);
      } else {
        newSelected.add(tableId);
      }
    });

    onUpdate({ selectedTables: newSelected });
  };

  const selectAll = () => {
    const newSelected = new Set<string>();
    schemaGroups.forEach((group) => {
      group.tables
        .filter((table) => matchesSearch(table))
        .forEach((table) => {
          newSelected.add(getTableId(table));
        });
    });
    onUpdate({ selectedTables: newSelected });
  };

  const deselectAll = () => {
    onUpdate({ selectedTables: new Set() });
  };

  const matchesSearch = (table: TableMetadata) => {
    if (!searchTerm) return true;
    const search = searchTerm.toLowerCase();
    return (
      table.table.toLowerCase().includes(search) ||
      table.schema.toLowerCase().includes(search)
    );
  };

  const filteredGroups = useMemo(() => {
    return schemaGroups
      .map((group) => ({
        ...group,
        tables: group.tables.filter(matchesSearch),
      }))
      .filter((group) => group.tables.length > 0);
  }, [schemaGroups, searchTerm]);

  const selectedCount = data.selectedTables.size;
  const totalCount = schemaGroups.reduce(
    (sum, group) => sum + group.tables.length,
    0
  );

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center space-y-4 py-12">
        <Loader2 className="h-12 w-12 animate-spin text-primary" />
        <div className="text-center">
          <h3 className="text-lg font-semibold">Discovering Schema...</h3>
          <p className="text-sm text-muted-foreground">
            Fetching tables and metadata from your data source
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with Search and Actions */}
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search tables..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9"
            />
          </div>
        </div>
        <div className="ml-4 flex gap-2">
          <Button variant="outline" size="sm" onClick={selectAll}>
            Select All
          </Button>
          <Button variant="outline" size="sm" onClick={deselectAll}>
            Deselect All
          </Button>
        </div>
      </div>

      {/* Selection Summary */}
      <div className="flex items-center justify-between rounded-lg border bg-muted/50 p-3">
        <span className="text-sm font-medium">
          {selectedCount} of {totalCount} tables selected
        </span>
        <Badge variant="secondary">{selectedCount} selected</Badge>
      </div>

      {/* Schema Tree */}
      <div className="max-h-[500px] space-y-2 overflow-y-auto rounded-lg border p-4">
        {filteredGroups.length === 0 ? (
          <div className="py-8 text-center text-sm text-muted-foreground">
            {searchTerm ? "No tables match your search" : "No tables found"}
          </div>
        ) : (
          filteredGroups.map((group) => (
            <div key={group.schema} className="space-y-1">
              {/* Schema Header */}
              <div
                className="flex items-center gap-2 rounded-md p-2 hover:bg-muted/50 cursor-pointer"
                onClick={() =>
                  setExpandedSchemas((prev) => {
                    const next = new Set(prev);
                    if (next.has(group.schema)) {
                      next.delete(group.schema);
                    } else {
                      next.add(group.schema);
                    }
                    return next;
                  })
                }
              >
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    toggleSchemaSelection(group.schema);
                  }}
                  className="flex h-5 w-5 items-center justify-center"
                >
                  {isSchemaFullySelected(group.schema) ? (
                    <CheckSquare className="h-5 w-5 text-primary" />
                  ) : isSchemaPartiallySelected(group.schema) ? (
                    <MinusSquare className="h-5 w-5 text-primary" />
                  ) : (
                    <Square className="h-5 w-5" />
                  )}
                </button>

                {expandedSchemas.has(group.schema) ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}

                <Database className="h-4 w-4 text-muted-foreground" />
                <span className="font-medium">{group.schema}</span>
                <Badge variant="secondary" className="ml-auto">
                  {group.tables.length}
                </Badge>
              </div>

              {/* Tables List */}
              {expandedSchemas.has(group.schema) && (
                <div className="ml-7 space-y-1">
                  {group.tables.map((table) => (
                    <div
                      key={getTableId(table)}
                      className="flex items-center gap-2 rounded-md p-2 hover:bg-muted/50 cursor-pointer"
                      onClick={() => toggleTable(table)}
                    >
                      {isTableSelected(table) ? (
                        <CheckSquare className="h-5 w-5 text-primary" />
                      ) : (
                        <Square className="h-5 w-5" />
                      )}

                      <TableIcon className="h-4 w-4 text-muted-foreground" />
                      <span className="flex-1 text-sm">{table.table}</span>

                      <div className="flex gap-2">
                        {table.row_count !== undefined && table.row_count !== null && (
                          <Badge variant="outline" className="text-xs">
                            {typeof table.row_count === 'number' ? table.row_count.toLocaleString() : table.row_count} rows
                          </Badge>
                        )}
                        {table.size_mb !== undefined && table.size_mb !== null && (
                          <Badge variant="outline" className="text-xs">
                            {typeof table.size_mb === 'number' ? table.size_mb.toFixed(2) : table.size_mb} MB
                          </Badge>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
}
