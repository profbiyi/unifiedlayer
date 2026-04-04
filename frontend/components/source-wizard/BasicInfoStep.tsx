"use client";

import { useState, useMemo } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { staggerContainer, staggerItem, hoverLift, tapScale } from "@/lib/animations";
import { SourceWizardData } from "@/app/(dashboard)/sources/new/page";
import {
  SOURCE_CONNECTORS,
  CATEGORY_META,
  type ConnectorMeta,
  type ConnectorCategory,
} from "@/lib/connector-icons";
import { Search, Sparkles, CheckCircle2 } from "lucide-react";

interface BasicInfoStepProps {
  data: SourceWizardData;
  onUpdate: (updates: Partial<SourceWizardData>) => void;
}

export default function BasicInfoStep({ data, onUpdate }: BasicInfoStepProps) {
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<ConnectorCategory | null>(null);

  const categories = useMemo(() => {
    const cats = new Set(SOURCE_CONNECTORS.map((c) => c.category));
    return Array.from(cats) as ConnectorCategory[];
  }, []);

  const popular = useMemo(() => {
    return SOURCE_CONNECTORS.filter((c) => c.popular);
  }, []);

  const filtered = useMemo(() => {
    let result = SOURCE_CONNECTORS;

    if (activeCategory) {
      result = result.filter((c) => c.category === activeCategory);
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          c.description.toLowerCase().includes(q) ||
          c.category.includes(q)
      );
    }

    return result;
  }, [activeCategory, search]);

  const selectedMeta = SOURCE_CONNECTORS.find((c) => c.id === data.source_type);
  const showPopular = !search && !activeCategory && popular.length > 0;

  const handleSelect = (connector: ConnectorMeta) => {
    const isDeselecting = data.source_type === connector.id;
    if (isDeselecting) {
      onUpdate({ source_type: "", name: "", config: {} });
    } else {
      // Auto-generate name if empty or was auto-generated
      const previousMeta = SOURCE_CONNECTORS.find((c) => c.id === data.source_type);
      const wasAutoNamed =
        !data.name || (previousMeta && data.name === previousMeta.name);
      onUpdate({
        source_type: connector.id,
        config: {},
        ...(wasAutoNamed ? { name: connector.name } : {}),
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* Connector Picker */}
      <div className="space-y-4">
        {/* Search */}
        <div className="relative max-w-md">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search connectors..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9 h-10 rounded-xl"
          />
        </div>

        {/* Category filters */}
        <div className="flex gap-2 flex-wrap">
          <Badge
            variant={activeCategory === null ? "default" : "outline"}
            className="cursor-pointer px-3 py-1 text-xs"
            onClick={() => setActiveCategory(null)}
          >
            All
          </Badge>
          {categories.map((cat) => (
            <Badge
              key={cat}
              variant={activeCategory === cat ? "default" : "outline"}
              className={`cursor-pointer px-3 py-1 text-xs capitalize ${
                activeCategory === cat ? "" : CATEGORY_META[cat as ConnectorCategory].color
              }`}
              onClick={() => setActiveCategory(cat === activeCategory ? null : cat)}
            >
              {CATEGORY_META[cat as ConnectorCategory].label}
            </Badge>
          ))}
        </div>

        {/* Popular section */}
        {showPopular && (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-amber-500" />
              <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">Popular</span>
            </div>
            <div className="grid gap-2 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
              {popular.map((connector) => {
                const Icon = connector.icon;
                const isSelected = data.source_type === connector.id;
                return (
                  <motion.button
                    key={connector.id}
                    type="button"
                    whileHover={hoverLift}
                    whileTap={tapScale}
                    onClick={() => handleSelect(connector)}
                    className={`group relative flex items-center gap-3 rounded-xl border p-3 text-left transition-all cursor-pointer ${
                      isSelected
                        ? "border-primary ring-2 ring-primary/20 bg-primary/5"
                        : "hover:border-primary/30 hover:bg-accent/50 hover:shadow-sm"
                    }`}
                  >
                    <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${connector.color} shadow-sm`}>
                      <Icon className={`h-4.5 w-4.5 ${connector.textColor}`} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium truncate">{connector.name}</p>
                      <p className="text-[11px] text-muted-foreground truncate">{connector.description}</p>
                    </div>
                    {isSelected && (
                      <CheckCircle2 className="h-4 w-4 shrink-0 text-primary" />
                    )}
                  </motion.button>
                );
              })}
            </div>
          </div>
        )}

        {/* All connectors / filtered results */}
        <div className="space-y-2">
          {showPopular && (
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wide">
              {activeCategory
                ? CATEGORY_META[activeCategory as ConnectorCategory].label.toUpperCase()
                : "ALL CONNECTORS"}
            </span>
          )}
          <motion.div
            variants={staggerContainer}
            initial="initial"
            animate="animate"
            className="grid gap-2 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4"
          >
            {filtered.map((connector) => {
              const Icon = connector.icon;
              const isSelected = data.source_type === connector.id;
              return (
                <motion.button
                  key={connector.id}
                  type="button"
                  variants={staggerItem}
                  whileHover={hoverLift}
                  whileTap={tapScale}
                  onClick={() => handleSelect(connector)}
                  className={`group relative flex items-center gap-3 rounded-xl border p-3 text-left transition-all cursor-pointer ${
                    isSelected
                      ? "border-primary ring-2 ring-primary/20 bg-primary/5"
                      : "hover:border-primary/30 hover:bg-accent/50 hover:shadow-sm"
                  }`}
                >
                  <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${connector.color} shadow-sm`}>
                    <Icon className={`h-4.5 w-4.5 ${connector.textColor}`} />
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm font-medium truncate">{connector.name}</p>
                    <p className="text-[11px] text-muted-foreground truncate">{connector.description}</p>
                  </div>
                  {connector.isNew && !isSelected && (
                    <Badge
                      variant="secondary"
                      className="absolute top-1.5 right-1.5 h-4 px-1 text-[9px] font-semibold bg-emerald-100 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-0"
                    >
                      New
                    </Badge>
                  )}
                  {isSelected && (
                    <CheckCircle2 className="h-4 w-4 shrink-0 text-primary" />
                  )}
                </motion.button>
              );
            })}
          </motion.div>

          {filtered.length === 0 && (
            <div className="flex flex-col items-center justify-center py-8 text-muted-foreground">
              <Search className="h-6 w-6 mb-2 opacity-50" />
              <p className="text-sm">No connectors found</p>
              <p className="text-xs mt-1">Try a different search term</p>
            </div>
          )}
        </div>
      </div>

      {/* Name & Description — shown after selection */}
      <AnimatePresence>
        {data.source_type && selectedMeta && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
            className="space-y-4 border-t pt-5"
          >
            <div className="flex items-center gap-3 mb-1">
              {(() => {
                const Icon = selectedMeta.icon;
                return (
                  <div className={`flex h-8 w-8 items-center justify-center rounded-lg ${selectedMeta.color}`}>
                    <Icon className={`h-4 w-4 ${selectedMeta.textColor}`} />
                  </div>
                );
              })()}
              <div>
                <p className="text-sm font-semibold">{selectedMeta.name} selected</p>
                <p className="text-xs text-muted-foreground">{selectedMeta.description}</p>
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="name">
                Source Name <span className="text-destructive">*</span>
              </Label>
              <Input
                id="name"
                placeholder={`e.g., Production ${selectedMeta.name}`}
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
                rows={2}
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
