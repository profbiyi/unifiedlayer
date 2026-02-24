"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import {
  useAutoModelSettings,
  useUpdateAutoModelSettings,
  useAvailableSources,
} from "@/hooks/queries/useCrossSource";
import {
  Brain,
  Sparkles,
  Database,
  Link2,
  ArrowRight,
  CheckCircle2,
  Info,
  Zap,
  Layers,
  GitMerge,
} from "lucide-react";
import Link from "next/link";

export default function AIModelingSettingsPage() {
  const { data: settings, isLoading: settingsLoading } = useAutoModelSettings();
  const { data: sourcesData, isLoading: sourcesLoading } = useAvailableSources();
  const updateSettings = useUpdateAutoModelSettings();

  const [autoModelEnabled, setAutoModelEnabled] = useState<boolean | null>(null);
  const [crossSourceEnabled, setCrossSourceEnabled] = useState<boolean | null>(null);

  // Use local state if set, otherwise use server state
  const isAutoModelEnabled = autoModelEnabled ?? settings?.auto_model_enabled ?? false;
  const isCrossSourceEnabled = crossSourceEnabled ?? settings?.cross_source_enabled ?? false;

  const handleAutoModelToggle = (enabled: boolean) => {
    setAutoModelEnabled(enabled);
    // If disabling auto-model, also disable cross-source
    if (!enabled) {
      setCrossSourceEnabled(false);
    }
    updateSettings.mutate({
      enabled,
      cross_source_enabled: enabled ? isCrossSourceEnabled : false,
    });
  };

  const handleCrossSourceToggle = (enabled: boolean) => {
    setCrossSourceEnabled(enabled);
    updateSettings.mutate({
      enabled: isAutoModelEnabled,
      cross_source_enabled: enabled,
    });
  };

  const breadcrumbs = [
    { label: "Settings", href: "/settings" },
    { label: "AI Modeling" },
  ];

  if (settingsLoading) {
    return (
      <div className="space-y-6">
        <Breadcrumb items={breadcrumbs} />
        <div className="space-y-4">
          <Skeleton className="h-8 w-64" />
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <Breadcrumb items={breadcrumbs} />

      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Brain className="h-7 w-7 text-primary" />
          AI Auto-Modeling
        </h1>
        <p className="text-muted-foreground mt-1">
          Let AI automatically generate dimensional models from your data
        </p>
      </div>

      {/* Status Summary */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-primary/10 rounded-lg">
                <Layers className="h-5 w-5 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{settings?.models_generated || 0}</p>
                <p className="text-sm text-muted-foreground">Models Generated</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-green-500/10 rounded-lg">
                <Database className="h-5 w-5 text-green-500" />
              </div>
              <div>
                <p className="text-2xl font-bold">{sourcesData?.total || 0}</p>
                <p className="text-sm text-muted-foreground">Connected Sources</p>
              </div>
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3">
              <div className="p-2 bg-blue-500/10 rounded-lg">
                <Zap className="h-5 w-5 text-blue-500" />
              </div>
              <div>
                <p className="text-sm font-medium">
                  {settings?.last_model_generation
                    ? new Date(settings.last_model_generation).toLocaleDateString()
                    : "Never"}
                </p>
                <p className="text-sm text-muted-foreground">Last Generation</p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Auto-Modeling Toggle */}
      <Card>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2">
                <Sparkles className="h-5 w-5 text-yellow-500" />
                Auto-Model After Sync
              </CardTitle>
              <CardDescription>
                Automatically generate dimensional models (fact and dimension tables) when pipelines sync new data
              </CardDescription>
            </div>
            <Switch
              checked={isAutoModelEnabled}
              onCheckedChange={handleAutoModelToggle}
              disabled={updateSettings.isPending}
            />
          </div>
        </CardHeader>
        <CardContent>
          <AnimatePresence>
            {isAutoModelEnabled && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-4"
              >
                <div className="bg-muted/50 rounded-lg p-4 space-y-3">
                  <h4 className="font-medium flex items-center gap-2">
                    <CheckCircle2 className="h-4 w-4 text-green-500" />
                    What AI will do:
                  </h4>
                  <ul className="space-y-2 text-sm text-muted-foreground ml-6">
                    <li className="flex items-start gap-2">
                      <ArrowRight className="h-4 w-4 mt-0.5 text-primary" />
                      <span>Analyze your table schemas and column types</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <ArrowRight className="h-4 w-4 mt-0.5 text-primary" />
                      <span>Identify fact tables (transactions, events, orders)</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <ArrowRight className="h-4 w-4 mt-0.5 text-primary" />
                      <span>Create dimension tables (customers, products, time)</span>
                    </li>
                    <li className="flex items-start gap-2">
                      <ArrowRight className="h-4 w-4 mt-0.5 text-primary" />
                      <span>Generate SQL views ready for analytics</span>
                    </li>
                  </ul>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </CardContent>
      </Card>

      {/* Cross-Source Enrichment Toggle */}
      <Card className={!isAutoModelEnabled ? "opacity-60" : ""}>
        <CardHeader>
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2">
                <GitMerge className="h-5 w-5 text-purple-500" />
                Cross-Source Enrichment
                <Badge variant="secondary" className="ml-2">Advanced</Badge>
              </CardTitle>
              <CardDescription>
                Analyze all your sources together to find relationships and create unified models
              </CardDescription>
            </div>
            <Switch
              checked={isCrossSourceEnabled}
              onCheckedChange={handleCrossSourceToggle}
              disabled={!isAutoModelEnabled || updateSettings.isPending}
            />
          </div>
        </CardHeader>
        <CardContent>
          <AnimatePresence>
            {isCrossSourceEnabled && isAutoModelEnabled && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                className="space-y-4"
              >
                <Alert>
                  <Info className="h-4 w-4" />
                  <AlertTitle>How Cross-Source Works</AlertTitle>
                  <AlertDescription>
                    AI detects relationships between your sources (e.g., customer emails in Stripe matching those in your CRM)
                    and suggests joins to create unified customer profiles and enriched analytics.
                  </AlertDescription>
                </Alert>

                {/* Connected Sources Preview */}
                {sourcesLoading ? (
                  <div className="space-y-2">
                    <Skeleton className="h-10 w-full" />
                    <Skeleton className="h-10 w-full" />
                  </div>
                ) : sourcesData && sourcesData.sources.length > 0 ? (
                  <div className="space-y-2">
                    <h4 className="text-sm font-medium">Sources to Analyze:</h4>
                    <div className="flex flex-wrap gap-2">
                      {sourcesData.sources.map((source) => (
                        <Badge key={source.id} variant="outline" className="py-1.5">
                          <Database className="h-3 w-3 mr-1.5" />
                          {source.name}
                          <span className="ml-1.5 text-muted-foreground">({source.type})</span>
                        </Badge>
                      ))}
                    </div>
                  </div>
                ) : (
                  <Alert variant="destructive">
                    <AlertDescription>
                      No sources connected yet. Connect at least 2 sources to use cross-source modeling.
                    </AlertDescription>
                  </Alert>
                )}

                {/* Analyze Now Button */}
                {sourcesData && sourcesData.sources.length >= 2 && (
                  <div className="pt-2">
                    <Link href="/settings/ai-modeling/analyze">
                      <Button className="gap-2">
                        <Link2 className="h-4 w-4" />
                        Analyze Sources Now
                        <ArrowRight className="h-4 w-4" />
                      </Button>
                    </Link>
                  </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

          {!isAutoModelEnabled && (
            <p className="text-sm text-muted-foreground">
              Enable auto-modeling first to use cross-source enrichment.
            </p>
          )}
        </CardContent>
      </Card>

      {/* View Generated Models */}
      {settings && settings.models_generated > 0 && (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-medium">View Generated Models</h3>
                <p className="text-sm text-muted-foreground">
                  {settings.models_generated} model{settings.models_generated !== 1 ? "s" : ""} have been generated by AI
                </p>
              </div>
              <Link href="/models">
                <Button variant="outline" className="gap-2">
                  <Layers className="h-4 w-4" />
                  View Models
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
