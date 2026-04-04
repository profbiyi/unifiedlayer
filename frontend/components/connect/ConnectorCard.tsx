"use client";

import { motion } from "framer-motion";
import { Badge } from "@/components/ui/badge";
import { hoverLift, tapScale } from "@/lib/animations";
import { CATEGORY_META, type ConnectorMeta, type DestinationMeta } from "@/lib/connector-icons";
import { Check, Sparkles } from "lucide-react";

interface ConnectorCardProps {
  connector: ConnectorMeta | DestinationMeta;
  selected?: boolean;
  onClick?: () => void;
  compact?: boolean;
}

export default function ConnectorCard({
  connector,
  selected = false,
  onClick,
  compact = false,
}: ConnectorCardProps) {
  const Icon = connector.icon;
  const categoryMeta = "category" in connector
    ? CATEGORY_META[connector.category]
    : null;

  if (compact) {
    return (
      <motion.button
        whileHover={hoverLift}
        whileTap={tapScale}
        onClick={onClick}
        className={`
          relative flex items-center gap-3 rounded-xl border p-3 text-left transition-all
          ${selected
            ? "border-primary bg-primary/5 ring-2 ring-primary/20"
            : "border-border hover:border-primary/30 hover:bg-accent/50"
          }
        `}
      >
        <div className={`flex h-9 w-9 shrink-0 items-center justify-center rounded-lg ${connector.color}`}>
          <Icon className={`h-4 w-4 ${connector.textColor}`} />
        </div>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium truncate">{connector.name}</p>
        </div>
        {selected && (
          <Check className="h-4 w-4 shrink-0 text-primary" />
        )}
      </motion.button>
    );
  }

  return (
    <motion.button
      whileHover={hoverLift}
      whileTap={tapScale}
      onClick={onClick}
      className={`
        group relative flex flex-col items-start gap-3 rounded-xl border p-5 text-left transition-all
        ${selected
          ? "border-primary bg-primary/5 ring-2 ring-primary/20 shadow-md"
          : "border-border hover:border-primary/30 hover:bg-accent/50 hover:shadow-sm"
        }
      `}
    >
      {/* Top row: icon + badges */}
      <div className="flex w-full items-start justify-between">
        <div className={`flex h-12 w-12 items-center justify-center rounded-xl ${connector.color} shadow-sm`}>
          <Icon className={`h-6 w-6 ${connector.textColor}`} />
        </div>
        <div className="flex items-center gap-1.5">
          {"popular" in connector && connector.popular && (
            <Badge variant="secondary" className="text-[10px] px-1.5 py-0 h-5 gap-1">
              <Sparkles className="h-2.5 w-2.5" />
              Popular
            </Badge>
          )}
          {"isNew" in connector && connector.isNew && (
            <Badge className="text-[10px] px-1.5 py-0 h-5 bg-emerald-500 hover:bg-emerald-600">
              New
            </Badge>
          )}
          {selected && (
            <div className="flex h-6 w-6 items-center justify-center rounded-full bg-primary">
              <Check className="h-3.5 w-3.5 text-primary-foreground" />
            </div>
          )}
        </div>
      </div>

      {/* Name + description */}
      <div className="space-y-1">
        <h3 className="font-semibold text-sm">{connector.name}</h3>
        <p className="text-xs text-muted-foreground leading-relaxed line-clamp-2">
          {connector.description}
        </p>
      </div>

      {/* Category badge */}
      {categoryMeta && (
        <Badge variant="outline" className={`text-[10px] px-2 py-0 h-5 ${categoryMeta.color}`}>
          {categoryMeta.label}
        </Badge>
      )}
    </motion.button>
  );
}
