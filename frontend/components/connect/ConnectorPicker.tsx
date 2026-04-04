"use client";

import { useState, useMemo } from "react";
import { motion } from "framer-motion";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import ConnectorCard from "./ConnectorCard";
import { staggerContainer, staggerItem } from "@/lib/animations";
import {
  SOURCE_CONNECTORS,
  DESTINATION_CONNECTORS,
  CATEGORY_META,
  type ConnectorMeta,
  type DestinationMeta,
  type ConnectorCategory,
} from "@/lib/connector-icons";
import { Search, Sparkles } from "lucide-react";

interface ConnectorPickerProps {
  mode: "source" | "destination";
  selected?: string;
  onSelect: (id: string) => void;
}

export default function ConnectorPicker({ mode, selected, onSelect }: ConnectorPickerProps) {
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<ConnectorCategory | null>(null);

  const connectors = mode === "source" ? SOURCE_CONNECTORS : DESTINATION_CONNECTORS;

  const categories = useMemo(() => {
    if (mode === "destination") return [];
    const cats = new Set(SOURCE_CONNECTORS.map((c) => c.category));
    return Array.from(cats) as ConnectorCategory[];
  }, [mode]);

  const popular = useMemo(() => {
    return connectors.filter((c) => "popular" in c && c.popular);
  }, [connectors]);

  const filtered = useMemo(() => {
    let result = connectors;

    if (activeCategory && mode === "source") {
      result = result.filter((c) => "category" in c && c.category === activeCategory);
    }

    if (search.trim()) {
      const q = search.toLowerCase();
      result = result.filter(
        (c) =>
          c.name.toLowerCase().includes(q) ||
          c.description.toLowerCase().includes(q) ||
          ("category" in c && (c as ConnectorMeta).category.includes(q))
      );
    }

    return result;
  }, [connectors, activeCategory, search, mode]);

  const showPopular = !search && !activeCategory && popular.length > 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center space-y-2">
        <h2 className="text-2xl font-bold tracking-tight">
          {mode === "source" ? "Where is your data?" : "Where should it go?"}
        </h2>
        <p className="text-muted-foreground">
          {mode === "source"
            ? "Pick the service or database you want to connect"
            : "Choose a destination for your data"}
        </p>
      </div>

      {/* Search */}
      <div className="relative max-w-md mx-auto">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
        <Input
          placeholder={`Search ${mode === "source" ? "sources" : "destinations"}...`}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-9 h-11 rounded-xl"
        />
      </div>

      {/* Category filters (sources only) */}
      {mode === "source" && categories.length > 0 && (
        <div className="flex gap-2 flex-wrap justify-center">
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
                activeCategory === cat ? "" : CATEGORY_META[cat].color
              }`}
              onClick={() => setActiveCategory(cat === activeCategory ? null : cat)}
            >
              {CATEGORY_META[cat].label}
            </Badge>
          ))}
        </div>
      )}

      {/* Popular section */}
      {showPopular && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Sparkles className="h-4 w-4 text-amber-500" />
            <h3 className="text-sm font-semibold text-muted-foreground">POPULAR</h3>
          </div>
          <div className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4">
            {popular.map((connector) => (
              <ConnectorCard
                key={connector.id}
                connector={connector}
                selected={selected === connector.id}
                onClick={() => onSelect(connector.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* All connectors */}
      <div className="space-y-3">
        {showPopular && (
          <h3 className="text-sm font-semibold text-muted-foreground">
            {activeCategory ? CATEGORY_META[activeCategory].label.toUpperCase() : "ALL CONNECTORS"}
          </h3>
        )}
        <motion.div
          variants={staggerContainer}
          initial="initial"
          animate="animate"
          className="grid gap-3 grid-cols-2 sm:grid-cols-3 lg:grid-cols-4"
        >
          {filtered.map((connector) => (
            <motion.div key={connector.id} variants={staggerItem}>
              <ConnectorCard
                connector={connector}
                selected={selected === connector.id}
                onClick={() => onSelect(connector.id)}
              />
            </motion.div>
          ))}
        </motion.div>

        {filtered.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-muted-foreground">
            <Search className="h-8 w-8 mb-3 opacity-50" />
            <p className="text-sm">No {mode === "source" ? "sources" : "destinations"} found</p>
            <p className="text-xs mt-1">Try a different search term</p>
          </div>
        )}
      </div>
    </div>
  );
}
