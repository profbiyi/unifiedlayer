"use client";

import { motion } from "framer-motion";
import { Button } from "@/components/ui/button";
import {
  Database,
  GitBranch,
  Play,
  Plus,
  Inbox,
  BarChart3,
  FileSearch,
  Zap,
  ArrowRight,
  Boxes,
} from "lucide-react";
import Link from "next/link";
import { cn } from "@/lib/utils";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: React.ReactNode;
  action?: {
    label: string;
    href?: string;
    onClick?: () => void;
  };
  secondaryAction?: {
    label: string;
    href?: string;
    onClick?: () => void;
  };
  className?: string;
}

// Animation variants for the container
const containerVariants = {
  initial: { opacity: 0, y: 20 },
  animate: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.4,
      ease: [0.25, 0.1, 0.25, 1],
      staggerChildren: 0.1,
    },
  },
};

const itemVariants = {
  initial: { opacity: 0, y: 10 },
  animate: {
    opacity: 1,
    y: 0,
    transition: { duration: 0.3 },
  },
};

// Floating animation for icons
const floatVariants = {
  initial: { y: 0 },
  animate: {
    y: [-5, 5, -5],
    transition: {
      duration: 4,
      repeat: Infinity,
      ease: "easeInOut",
    },
  },
};

export function EmptyState({
  title,
  description,
  icon,
  action,
  secondaryAction,
  className,
}: EmptyStateProps) {
  return (
    <motion.div
      variants={containerVariants}
      initial="initial"
      animate="animate"
      className={cn(
        "flex flex-col items-center justify-center py-16 px-6 text-center",
        className
      )}
    >
      {icon && (
        <motion.div
          variants={floatVariants}
          initial="initial"
          animate="animate"
          className="mb-6 relative"
        >
          <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-primary/20 to-primary/5 flex items-center justify-center">
            <div className="text-primary">{icon}</div>
          </div>
          {/* Decorative dots */}
          <div className="absolute -top-2 -right-2 w-3 h-3 rounded-full bg-primary/30" />
          <div className="absolute -bottom-1 -left-1 w-2 h-2 rounded-full bg-primary/20" />
        </motion.div>
      )}

      <motion.h3
        variants={itemVariants}
        className="text-xl font-semibold mb-2"
      >
        {title}
      </motion.h3>

      <motion.p
        variants={itemVariants}
        className="text-muted-foreground max-w-md mb-6"
      >
        {description}
      </motion.p>

      <motion.div variants={itemVariants} className="flex gap-3">
        {action && (
          action.href ? (
            <Link href={action.href}>
              <Button size="lg" className="gap-2">
                <Plus className="h-4 w-4" />
                {action.label}
              </Button>
            </Link>
          ) : (
            <Button size="lg" onClick={action.onClick} className="gap-2">
              <Plus className="h-4 w-4" />
              {action.label}
            </Button>
          )
        )}

        {secondaryAction && (
          secondaryAction.href ? (
            <Link href={secondaryAction.href}>
              <Button variant="outline" size="lg" className="gap-2">
                {secondaryAction.label}
                <ArrowRight className="h-4 w-4" />
              </Button>
            </Link>
          ) : (
            <Button
              variant="outline"
              size="lg"
              onClick={secondaryAction.onClick}
              className="gap-2"
            >
              {secondaryAction.label}
              <ArrowRight className="h-4 w-4" />
            </Button>
          )
        )}
      </motion.div>
    </motion.div>
  );
}

// Pre-configured empty states for common use cases

export function EmptyPipelines() {
  return (
    <EmptyState
      icon={<GitBranch className="h-10 w-10" />}
      title="No pipelines yet"
      description="Pipelines connect your data sources to destinations and keep them in sync. Create your first pipeline to start moving data automatically."
      action={{
        label: "Create Pipeline",
        href: "/pipelines/new",
      }}
      secondaryAction={{
        label: "View Templates",
        href: "/templates",
      }}
    />
  );
}

export function EmptySources() {
  return (
    <EmptyState
      icon={<Database className="h-10 w-10" />}
      title="No data sources connected"
      description="Connect to your payment processors, accounting software, databases, or upload CSV files. Your data will be synced securely to your warehouse."
      action={{
        label: "Add Data Source",
        href: "/sources/new",
      }}
      secondaryAction={{
        label: "Browse Connectors",
        href: "/developers/connectors",
      }}
    />
  );
}

export function EmptyDestinations() {
  return (
    <EmptyState
      icon={<Inbox className="h-10 w-10" />}
      title="No destinations configured"
      description="Add a data warehouse or database destination where your synced data will be stored. We support PostgreSQL, BigQuery, Snowflake, and more."
      action={{
        label: "Add Destination",
        href: "/destinations/new",
      }}
    />
  );
}

export function EmptyRuns() {
  return (
    <EmptyState
      icon={<Play className="h-10 w-10" />}
      title="No pipeline runs yet"
      description="Pipeline runs appear here when you trigger a sync manually or when scheduled syncs execute. Create and run a pipeline to see activity."
      action={{
        label: "Go to Pipelines",
        href: "/pipelines",
      }}
    />
  );
}

export function EmptyDashboard() {
  return (
    <EmptyState
      icon={<BarChart3 className="h-10 w-10" />}
      title="Welcome to your dashboard"
      description="Start by connecting your first data source. Once you have data flowing, you'll see insights and analytics here."
      action={{
        label: "Get Started",
        href: "/onboarding",
      }}
    />
  );
}

export function NoSearchResults({ query }: { query?: string }) {
  return (
    <EmptyState
      icon={<FileSearch className="h-10 w-10" />}
      title="No results found"
      description={
        query
          ? `We couldn't find anything matching "${query}". Try a different search term or check your filters.`
          : "No items match your current filters. Try adjusting your search criteria."
      }
    />
  );
}

export function EmptyInsights() {
  return (
    <EmptyState
      icon={<Zap className="h-10 w-10" />}
      title="No insights available yet"
      description="Once you have data flowing through your pipelines, we'll generate actionable insights about your business metrics, trends, and anomalies."
      action={{
        label: "Set Up Pipeline",
        href: "/pipelines/new",
      }}
    />
  );
}

export function EmptyModels() {
  return (
    <EmptyState
      icon={<Boxes className="h-10 w-10" />}
      title="No models generated yet"
      description="Use AI to automatically generate dimensional models (star schema) from your synced data. These models help you analyze your data more effectively."
      action={{
        label: "Generate Models",
        href: "/models",
      }}
      secondaryAction={{
        label: "Learn More",
        href: "/developers/connectors",
      }}
    />
  );
}

// Compact empty state for inline use
interface CompactEmptyStateProps {
  icon?: React.ReactNode;
  message: string;
  action?: {
    label: string;
    onClick?: () => void;
    href?: string;
  };
  className?: string;
}

export function CompactEmptyState({
  icon,
  message,
  action,
  className,
}: CompactEmptyStateProps) {
  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      className={cn(
        "flex items-center justify-center gap-3 py-8 px-4 text-muted-foreground",
        className
      )}
    >
      {icon && <div className="text-muted-foreground/50">{icon}</div>}
      <span className="text-sm">{message}</span>
      {action && (
        action.href ? (
          <Link href={action.href}>
            <Button variant="link" size="sm" className="p-0 h-auto">
              {action.label}
            </Button>
          </Link>
        ) : (
          <Button
            variant="link"
            size="sm"
            onClick={action.onClick}
            className="p-0 h-auto"
          >
            {action.label}
          </Button>
        )
      )}
    </motion.div>
  );
}

export default EmptyState;
