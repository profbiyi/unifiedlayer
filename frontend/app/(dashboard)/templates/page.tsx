"use client";

import { useState, useMemo } from "react";
import { Input } from "@/components/ui/input";
import { Loader2, Search } from "lucide-react";
import { useTemplates } from "@/hooks/queries/useTemplates";
import TemplateCard from "@/components/templates/TemplateCard";
import { Badge } from "@/components/ui/badge";

export default function TemplatesPage() {
  const { data: templates, isLoading } = useTemplates();
  const [search, setSearch] = useState("");
  const [activeCategory, setActiveCategory] = useState<string | null>(null);

  const categories = useMemo(() => {
    if (!templates) return [];
    return Array.from(new Set(templates.map((t) => t.category)));
  }, [templates]);

  const filtered = useMemo(() => {
    if (!templates) return [];
    let result = templates;
    if (activeCategory) {
      result = result.filter((t) => t.category === activeCategory);
    }
    if (search) {
      const q = search.toLowerCase();
      result = result.filter(
        (t) =>
          t.name.toLowerCase().includes(q) ||
          t.description.toLowerCase().includes(q) ||
          t.tags.some((tag) => tag.toLowerCase().includes(q))
      );
    }
    return result;
  }, [templates, activeCategory, search]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Sync Templates</h1>
        <p className="text-muted-foreground">
          Deploy a pre-built pipeline in one click
        </p>
      </div>

      <div className="flex flex-col sm:flex-row gap-4">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search templates..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="pl-9"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          <Badge
            variant={activeCategory === null ? "default" : "outline"}
            className="cursor-pointer"
            onClick={() => setActiveCategory(null)}
          >
            All
          </Badge>
          {categories.map((cat) => (
            <Badge
              key={cat}
              variant={activeCategory === cat ? "default" : "outline"}
              className="cursor-pointer capitalize"
              onClick={() => setActiveCategory(cat === activeCategory ? null : cat)}
            >
              {cat}
            </Badge>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center h-64">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : filtered.length === 0 ? (
        <div className="flex items-center justify-center h-64">
          <p className="text-muted-foreground">No templates found</p>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {filtered.map((template) => (
            <TemplateCard key={template.id} template={template} />
          ))}
        </div>
      )}
    </div>
  );
}
