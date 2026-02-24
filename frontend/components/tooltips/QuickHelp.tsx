"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { HelpCircle, X, ExternalLink } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import Link from "next/link";

interface QuickHelpProps {
  title: string;
  content: string | React.ReactNode;
  learnMoreUrl?: string;
  position?: "top" | "bottom" | "left" | "right";
  size?: "sm" | "md";
  className?: string;
}

const positionStyles = {
  top: "bottom-full left-1/2 -translate-x-1/2 mb-2",
  bottom: "top-full left-1/2 -translate-x-1/2 mt-2",
  left: "right-full top-1/2 -translate-y-1/2 mr-2",
  right: "left-full top-1/2 -translate-y-1/2 ml-2",
};

const arrowStyles = {
  top: "top-full left-1/2 -translate-x-1/2 border-t-border border-x-transparent border-b-transparent",
  bottom: "bottom-full left-1/2 -translate-x-1/2 border-b-border border-x-transparent border-t-transparent",
  left: "left-full top-1/2 -translate-y-1/2 border-l-border border-y-transparent border-r-transparent",
  right: "right-full top-1/2 -translate-y-1/2 border-r-border border-y-transparent border-l-transparent",
};

const animationOrigin = {
  top: { initial: { opacity: 0, y: 5 }, animate: { opacity: 1, y: 0 } },
  bottom: { initial: { opacity: 0, y: -5 }, animate: { opacity: 1, y: 0 } },
  left: { initial: { opacity: 0, x: 5 }, animate: { opacity: 1, x: 0 } },
  right: { initial: { opacity: 0, x: -5 }, animate: { opacity: 1, x: 0 } },
};

export function QuickHelp({
  title,
  content,
  learnMoreUrl,
  position = "top",
  size = "sm",
  className,
}: QuickHelpProps) {
  const [isOpen, setIsOpen] = useState(false);

  const sizeClasses = {
    sm: "w-64",
    md: "w-80",
  };

  return (
    <div className={cn("relative inline-flex", className)}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
        className="text-muted-foreground hover:text-foreground transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-primary focus-visible:ring-offset-2 rounded-full"
        aria-label={`Help: ${title}`}
      >
        <HelpCircle className="h-4 w-4" />
      </button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={animationOrigin[position].initial}
            animate={animationOrigin[position].animate}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className={cn(
              "absolute z-50 p-3 rounded-lg border bg-popover text-popover-foreground shadow-lg",
              positionStyles[position],
              sizeClasses[size]
            )}
            onMouseEnter={() => setIsOpen(true)}
            onMouseLeave={() => setIsOpen(false)}
          >
            {/* Arrow */}
            <div
              className={cn(
                "absolute w-0 h-0 border-[6px]",
                arrowStyles[position]
              )}
            />

            <div className="space-y-2">
              <h4 className="font-medium text-sm">{title}</h4>
              <div className="text-xs text-muted-foreground leading-relaxed">
                {content}
              </div>
              {learnMoreUrl && (
                <Link
                  href={learnMoreUrl}
                  className="inline-flex items-center gap-1 text-xs text-primary hover:underline"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  Learn more
                  <ExternalLink className="h-3 w-3" />
                </Link>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

// Pre-configured help tooltips for common concepts

export function PipelineHelp() {
  return (
    <QuickHelp
      title="What is a Pipeline?"
      content="A pipeline connects your data source to a destination and keeps them in sync. It defines what data to extract, how to transform it, and where to load it."
      learnMoreUrl="/docs/pipelines"
    />
  );
}

export function SyncHelp() {
  return (
    <QuickHelp
      title="What happens during a sync?"
      content="During a sync, data is extracted from your source, optionally transformed using SQL, and loaded into your destination. Incremental syncs only process new or changed data."
      learnMoreUrl="/docs/syncs"
    />
  );
}

export function SourceHelp() {
  return (
    <QuickHelp
      title="What is a Data Source?"
      content="A data source is where your data originates. This could be a payment processor like Stripe, accounting software like Xero, a database, or even a CSV file."
      learnMoreUrl="/docs/sources"
    />
  );
}

export function DestinationHelp() {
  return (
    <QuickHelp
      title="What is a Destination?"
      content="A destination is where your synced data is stored. Typically this is a data warehouse like BigQuery, Snowflake, or PostgreSQL where you can query and analyze your data."
      learnMoreUrl="/docs/destinations"
    />
  );
}

export function IncrementalSyncHelp() {
  return (
    <QuickHelp
      title="Incremental vs Full Sync"
      content="Incremental sync only processes records that have changed since the last sync, making it faster and more efficient. Full sync reloads all data from scratch."
    />
  );
}

export function TransformationHelp() {
  return (
    <QuickHelp
      title="SQL Transformations"
      content="Transformations let you modify data using SQL before it reaches your destination. Clean, filter, join, or aggregate data to match your analysis needs."
      learnMoreUrl="/docs/transformations"
    />
  );
}

export function DbtHelp() {
  return (
    <QuickHelp
      title="What is dbt?"
      content="dbt (data build tool) lets you transform data in your warehouse using SQL. Connect your dbt project to run models automatically after pipeline syncs complete."
      learnMoreUrl="/docs/dbt"
    />
  );
}

// Inline help label component
interface HelpLabelProps {
  children: React.ReactNode;
  helpTitle: string;
  helpContent: string | React.ReactNode;
  learnMoreUrl?: string;
  className?: string;
}

export function HelpLabel({
  children,
  helpTitle,
  helpContent,
  learnMoreUrl,
  className,
}: HelpLabelProps) {
  return (
    <div className={cn("inline-flex items-center gap-1.5", className)}>
      <span>{children}</span>
      <QuickHelp
        title={helpTitle}
        content={helpContent}
        learnMoreUrl={learnMoreUrl}
        position="right"
      />
    </div>
  );
}

// Contextual help panel (larger, closeable)
interface HelpPanelProps {
  title: string;
  content: string | React.ReactNode;
  isOpen: boolean;
  onClose: () => void;
  learnMoreUrl?: string;
  className?: string;
}

export function HelpPanel({
  title,
  content,
  isOpen,
  onClose,
  learnMoreUrl,
  className,
}: HelpPanelProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <motion.div
          initial={{ opacity: 0, y: -10, height: 0 }}
          animate={{ opacity: 1, y: 0, height: "auto" }}
          exit={{ opacity: 0, y: -10, height: 0 }}
          transition={{ duration: 0.2 }}
          className={cn(
            "overflow-hidden rounded-lg border bg-muted/50 mb-6",
            className
          )}
        >
          <div className="p-4">
            <div className="flex items-start justify-between gap-4">
              <div className="flex items-start gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <HelpCircle className="h-4 w-4 text-primary" />
                </div>
                <div className="space-y-1">
                  <h4 className="font-medium text-sm">{title}</h4>
                  <div className="text-sm text-muted-foreground leading-relaxed">
                    {content}
                  </div>
                  {learnMoreUrl && (
                    <Link
                      href={learnMoreUrl}
                      className="inline-flex items-center gap-1 text-sm text-primary hover:underline mt-2"
                    >
                      Learn more
                      <ExternalLink className="h-3 w-3" />
                    </Link>
                  )}
                </div>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="flex-shrink-0"
              >
                <X className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

export default QuickHelp;
