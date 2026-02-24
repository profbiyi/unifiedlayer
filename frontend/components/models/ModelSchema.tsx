"use client";

import { useState } from "react";
import { GeneratedModel, ModelColumn, ModelRelationship } from "@/types/models";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  ChevronDown,
  ChevronRight,
  Key,
  Link2,
  Type,
  Hash,
  Calendar,
  ToggleLeft,
  FileText,
  ArrowRight,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface ModelSchemaProps {
  model: GeneratedModel;
  className?: string;
}

// Map SQL types to icons
function getTypeIcon(type: string) {
  const typeLower = type.toLowerCase();
  if (typeLower.includes("int") || typeLower.includes("numeric") || typeLower.includes("decimal") || typeLower.includes("float")) {
    return <Hash className="h-3.5 w-3.5 text-blue-500" />;
  }
  if (typeLower.includes("varchar") || typeLower.includes("text") || typeLower.includes("char")) {
    return <Type className="h-3.5 w-3.5 text-green-500" />;
  }
  if (typeLower.includes("date") || typeLower.includes("time") || typeLower.includes("timestamp")) {
    return <Calendar className="h-3.5 w-3.5 text-orange-500" />;
  }
  if (typeLower.includes("bool")) {
    return <ToggleLeft className="h-3.5 w-3.5 text-purple-500" />;
  }
  if (typeLower.includes("json") || typeLower.includes("blob")) {
    return <FileText className="h-3.5 w-3.5 text-pink-500" />;
  }
  return <Type className="h-3.5 w-3.5 text-muted-foreground" />;
}

function isPrimaryKey(column: ModelColumn, relationships: ModelRelationship[]) {
  // Check if column name suggests it's a primary key
  const nameLower = column.name.toLowerCase();
  return nameLower === "id" || nameLower.endsWith("_id") || nameLower.endsWith("_key");
}

function isForeignKey(column: ModelColumn, relationships: ModelRelationship[]) {
  return relationships.some((rel) => rel.from_column === column.name);
}

function ColumnRow({
  column,
  relationships,
}: {
  column: ModelColumn;
  relationships: ModelRelationship[];
}) {
  const isPK = isPrimaryKey(column, relationships);
  const isFK = isForeignKey(column, relationships);
  const relatedTo = relationships.find((rel) => rel.from_column === column.name);

  return (
    <div className="flex items-start gap-3 py-2 px-3 hover:bg-muted/50 rounded-md transition-colors">
      <div className="flex-shrink-0 mt-0.5">{getTypeIcon(column.type)}</div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-medium">{column.name}</span>
          {isPK && (
            <Badge variant="outline" className="text-xs px-1.5 py-0 border-amber-500 text-amber-600">
              <Key className="h-2.5 w-2.5 mr-1" />
              PK
            </Badge>
          )}
          {isFK && (
            <Badge variant="outline" className="text-xs px-1.5 py-0 border-blue-500 text-blue-600">
              <Link2 className="h-2.5 w-2.5 mr-1" />
              FK
            </Badge>
          )}
        </div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground mt-0.5">
          <span className="font-mono">{column.type}</span>
          {column.description && (
            <>
              <span>-</span>
              <span className="truncate">{column.description}</span>
            </>
          )}
        </div>
        {relatedTo && (
          <div className="flex items-center gap-1 text-xs text-blue-600 mt-1">
            <ArrowRight className="h-3 w-3" />
            <span>
              {relatedTo.to_table}.{relatedTo.to_column}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}

function RelationshipRow({ relationship }: { relationship: ModelRelationship }) {
  return (
    <div className="flex items-center gap-2 py-2 px-3 hover:bg-muted/50 rounded-md transition-colors">
      <Link2 className="h-4 w-4 text-blue-500 flex-shrink-0" />
      <span className="font-mono text-sm">{relationship.from_column}</span>
      <ArrowRight className="h-3 w-3 text-muted-foreground" />
      <span className="font-mono text-sm text-blue-600">
        {relationship.to_table}
      </span>
      <span className="text-muted-foreground">.</span>
      <span className="font-mono text-sm">{relationship.to_column}</span>
    </div>
  );
}

export function ModelSchema({ model, className }: ModelSchemaProps) {
  const [columnsExpanded, setColumnsExpanded] = useState(true);
  const [relationshipsExpanded, setRelationshipsExpanded] = useState(true);

  return (
    <div className={cn("space-y-4", className)}>
      {/* Columns Section */}
      <Card>
        <CardHeader className="pb-2">
          <Button
            variant="ghost"
            className="w-full justify-between p-0 h-auto hover:bg-transparent"
            onClick={() => setColumnsExpanded(!columnsExpanded)}
          >
            <CardTitle className="text-base flex items-center gap-2">
              <Type className="h-4 w-4" />
              Columns
              <Badge variant="secondary" className="ml-2">
                {model.columns.length}
              </Badge>
            </CardTitle>
            {columnsExpanded ? (
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            ) : (
              <ChevronRight className="h-4 w-4 text-muted-foreground" />
            )}
          </Button>
        </CardHeader>
        <AnimatePresence>
          {columnsExpanded && (
            <motion.div
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: "auto", opacity: 1 }}
              exit={{ height: 0, opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <CardContent className="pt-0">
                <div className="border rounded-lg divide-y">
                  {model.columns.map((column, index) => (
                    <ColumnRow
                      key={index}
                      column={column}
                      relationships={model.relationships}
                    />
                  ))}
                </div>
              </CardContent>
            </motion.div>
          )}
        </AnimatePresence>
      </Card>

      {/* Relationships Section */}
      {model.relationships.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <Button
              variant="ghost"
              className="w-full justify-between p-0 h-auto hover:bg-transparent"
              onClick={() => setRelationshipsExpanded(!relationshipsExpanded)}
            >
              <CardTitle className="text-base flex items-center gap-2">
                <Link2 className="h-4 w-4" />
                Relationships
                <Badge variant="secondary" className="ml-2">
                  {model.relationships.length}
                </Badge>
              </CardTitle>
              {relationshipsExpanded ? (
                <ChevronDown className="h-4 w-4 text-muted-foreground" />
              ) : (
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              )}
            </Button>
          </CardHeader>
          <AnimatePresence>
            {relationshipsExpanded && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: "auto", opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2 }}
              >
                <CardContent className="pt-0">
                  <div className="border rounded-lg divide-y">
                    {model.relationships.map((relationship, index) => (
                      <RelationshipRow key={index} relationship={relationship} />
                    ))}
                  </div>
                </CardContent>
              </motion.div>
            )}
          </AnimatePresence>
        </Card>
      )}
    </div>
  );
}

export default ModelSchema;
