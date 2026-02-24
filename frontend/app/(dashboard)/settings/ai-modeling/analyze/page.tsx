"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Progress } from "@/components/ui/progress";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible";
import {
  useAvailableSources,
  useAnalyzeSources,
  useGenerateUnifiedModels,
  SuggestedJoin,
} from "@/hooks/queries/useCrossSource";
import {
  Brain,
  Link2,
  Database,
  ArrowRight,
  ArrowLeftRight,
  CheckCircle2,
  Loader2,
  ChevronDown,
  ChevronUp,
  Sparkles,
  AlertCircle,
  Layers,
} from "lucide-react";

export default function CrossSourceAnalyzePage() {
  const router = useRouter();
  const { data: sourcesData, isLoading: sourcesLoading } = useAvailableSources();
  const analyzeMutation = useAnalyzeSources();
  const generateMutation = useGenerateUnifiedModels();

  const [selectedJoins, setSelectedJoins] = useState<Set<string>>(new Set());
  const [primarySource, setPrimarySource] = useState<string>("");
  const [expandedJoin, setExpandedJoin] = useState<string | null>(null);
  const [analysisProgress, setAnalysisProgress] = useState(0);

  // Simulate progress during analysis
  useEffect(() => {
    if (analyzeMutation.isPending) {
      setAnalysisProgress(0);
      const interval = setInterval(() => {
        setAnalysisProgress((prev) => Math.min(prev + Math.random() * 15, 90));
      }, 500);
      return () => clearInterval(interval);
    } else if (analyzeMutation.isSuccess) {
      setAnalysisProgress(100);
    }
  }, [analyzeMutation.isPending, analyzeMutation.isSuccess]);

  // Auto-select high-confidence joins
  useEffect(() => {
    if (analyzeMutation.data?.suggested_joins) {
      const highConfidence = analyzeMutation.data.suggested_joins
        .filter((j) => j.confidence >= 0.8)
        .map((j) => j.id);
      setSelectedJoins(new Set(highConfidence));
    }
  }, [analyzeMutation.data]);

  // Auto-set primary source
  useEffect(() => {
    if (sourcesData?.sources.length && !primarySource) {
      setPrimarySource(sourcesData.sources[0].name);
    }
  }, [sourcesData, primarySource]);

  const handleAnalyze = () => {
    analyzeMutation.mutate(undefined);
  };

  const handleJoinToggle = (joinId: string) => {
    setSelectedJoins((prev) => {
      const next = new Set(prev);
      if (next.has(joinId)) {
        next.delete(joinId);
      } else {
        next.add(joinId);
      }
      return next;
    });
  };

  const handleGenerateModels = () => {
    if (selectedJoins.size === 0) return;
    generateMutation.mutate(
      {
        confirmed_join_ids: Array.from(selectedJoins),
        primary_source: primarySource,
      },
      {
        onSuccess: () => {
          router.push("/models");
        },
      }
    );
  };

  const getConfidenceBadge = (confidence: number) => {
    if (confidence >= 0.9) {
      return <Badge className="bg-green-500">High ({Math.round(confidence * 100)}%)</Badge>;
    } else if (confidence >= 0.7) {
      return <Badge className="bg-yellow-500">Medium ({Math.round(confidence * 100)}%)</Badge>;
    } else {
      return <Badge variant="secondary">Low ({Math.round(confidence * 100)}%)</Badge>;
    }
  };

  const breadcrumbs = [
    { label: "Settings", href: "/settings" },
    { label: "AI Modeling", href: "/settings/ai-modeling" },
    { label: "Analyze Sources" },
  ];

  return (
    <div className="space-y-6">
      <Breadcrumb items={breadcrumbs} />

      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Link2 className="h-7 w-7 text-primary" />
          Cross-Source Analysis
        </h1>
        <p className="text-muted-foreground mt-1">
          AI analyzes your sources to find relationships and suggest joins
        </p>
      </div>

      {/* Step 1: Sources Overview */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Database className="h-5 w-5" />
            Your Data Sources
          </CardTitle>
          <CardDescription>
            {sourcesData?.total || 0} sources will be analyzed for cross-source relationships
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sourcesLoading ? (
            <div className="flex gap-2">
              <Skeleton className="h-8 w-24" />
              <Skeleton className="h-8 w-24" />
            </div>
          ) : sourcesData && sourcesData.sources.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {sourcesData.sources.map((source) => (
                <Badge key={source.id} variant="outline" className="py-2 px-3">
                  <Database className="h-4 w-4 mr-2" />
                  {source.name}
                  <span className="ml-2 text-muted-foreground">({source.type})</span>
                </Badge>
              ))}
            </div>
          ) : (
            <Alert variant="destructive">
              <AlertCircle className="h-4 w-4" />
              <AlertTitle>No Sources Found</AlertTitle>
              <AlertDescription>
                You need at least 2 connected sources with synced data to use cross-source modeling.
              </AlertDescription>
            </Alert>
          )}

          {!analyzeMutation.data && sourcesData && sourcesData.sources.length >= 2 && (
            <div className="mt-4">
              <Button
                onClick={handleAnalyze}
                disabled={analyzeMutation.isPending}
                className="gap-2"
              >
                {analyzeMutation.isPending ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Analyzing...
                  </>
                ) : (
                  <>
                    <Brain className="h-4 w-4" />
                    Start Analysis
                  </>
                )}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Analysis Progress */}
      <AnimatePresence>
        {analyzeMutation.isPending && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -10 }}
          >
            <Card>
              <CardContent className="pt-6">
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <Loader2 className="h-5 w-5 animate-spin text-primary" />
                    <span className="font-medium">Analyzing your data sources...</span>
                  </div>
                  <Progress value={analysisProgress} className="h-2" />
                  <p className="text-sm text-muted-foreground">
                    AI is detecting column patterns, comparing data types, and finding relationships
                  </p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Step 2: Suggested Joins */}
      <AnimatePresence>
        {analyzeMutation.data && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Summary */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card>
                <CardContent className="pt-6 text-center">
                  <p className="text-3xl font-bold text-primary">
                    {analyzeMutation.data.sources_analyzed}
                  </p>
                  <p className="text-sm text-muted-foreground">Sources Analyzed</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6 text-center">
                  <p className="text-3xl font-bold text-blue-500">
                    {analyzeMutation.data.tables_found}
                  </p>
                  <p className="text-sm text-muted-foreground">Tables Found</p>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6 text-center">
                  <p className="text-3xl font-bold text-green-500">
                    {analyzeMutation.data.suggested_joins.length}
                  </p>
                  <p className="text-sm text-muted-foreground">Relationships Detected</p>
                </CardContent>
              </Card>
            </div>

            {/* Suggested Joins */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <ArrowLeftRight className="h-5 w-5" />
                  Suggested Joins
                </CardTitle>
                <CardDescription>
                  Select the relationships you want to use for your unified models.
                  High-confidence matches are pre-selected.
                </CardDescription>
              </CardHeader>
              <CardContent>
                {analyzeMutation.data.suggested_joins.length === 0 ? (
                  <Alert>
                    <AlertCircle className="h-4 w-4" />
                    <AlertTitle>No Relationships Found</AlertTitle>
                    <AlertDescription>
                      AI couldn&apos;t find any matching columns between your sources.
                      This might happen if your data uses different naming conventions or IDs.
                    </AlertDescription>
                  </Alert>
                ) : (
                  <div className="space-y-3">
                    {analyzeMutation.data.suggested_joins.map((join) => (
                      <JoinCard
                        key={join.id}
                        join={join}
                        isSelected={selectedJoins.has(join.id)}
                        isExpanded={expandedJoin === join.id}
                        onToggle={() => handleJoinToggle(join.id)}
                        onExpand={() =>
                          setExpandedJoin(expandedJoin === join.id ? null : join.id)
                        }
                        getConfidenceBadge={getConfidenceBadge}
                      />
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Step 3: Generate Models */}
            {analyzeMutation.data.suggested_joins.length > 0 && selectedJoins.size > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Sparkles className="h-5 w-5 text-yellow-500" />
                    Generate Unified Models
                  </CardTitle>
                  <CardDescription>
                    Choose your primary source and generate AI-powered dimensional models
                  </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-sm font-medium">Primary Source</label>
                    <Select value={primarySource} onValueChange={setPrimarySource}>
                      <SelectTrigger className="w-64">
                        <SelectValue placeholder="Select primary source" />
                      </SelectTrigger>
                      <SelectContent>
                        {sourcesData?.sources.map((source) => (
                          <SelectItem key={source.id} value={source.name}>
                            {source.name}
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground">
                      The primary source will be used as the base for fact tables
                    </p>
                  </div>

                  <div className="flex items-center gap-4 pt-2">
                    <Button
                      onClick={handleGenerateModels}
                      disabled={generateMutation.isPending || !primarySource}
                      className="gap-2"
                    >
                      {generateMutation.isPending ? (
                        <>
                          <Loader2 className="h-4 w-4 animate-spin" />
                          Generating...
                        </>
                      ) : (
                        <>
                          <Layers className="h-4 w-4" />
                          Generate {selectedJoins.size} Unified Model
                          {selectedJoins.size !== 1 ? "s" : ""}
                        </>
                      )}
                    </Button>
                    <span className="text-sm text-muted-foreground">
                      {selectedJoins.size} join{selectedJoins.size !== 1 ? "s" : ""} selected
                    </span>
                  </div>
                </CardContent>
              </Card>
            )}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}

function JoinCard({
  join,
  isSelected,
  isExpanded,
  onToggle,
  onExpand,
  getConfidenceBadge,
}: {
  join: SuggestedJoin;
  isSelected: boolean;
  isExpanded: boolean;
  onToggle: () => void;
  onExpand: () => void;
  getConfidenceBadge: (confidence: number) => React.ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`border rounded-lg p-4 transition-colors ${
        isSelected ? "border-primary bg-primary/5" : "hover:border-muted-foreground/30"
      }`}
    >
      <div className="flex items-start gap-4">
        <Checkbox
          checked={isSelected}
          onCheckedChange={onToggle}
          className="mt-1"
        />
        <div className="flex-1 space-y-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="outline">{join.left_source}</Badge>
              <span className="text-muted-foreground text-sm">{join.left_table}</span>
              <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                {join.left_column}
              </code>
              <ArrowLeftRight className="h-4 w-4 text-muted-foreground" />
              <Badge variant="outline">{join.right_source}</Badge>
              <span className="text-muted-foreground text-sm">{join.right_table}</span>
              <code className="text-xs bg-muted px-1.5 py-0.5 rounded">
                {join.right_column}
              </code>
            </div>
            {getConfidenceBadge(join.confidence)}
          </div>

          <p className="text-sm text-muted-foreground">{join.reasoning}</p>

          <Collapsible open={isExpanded} onOpenChange={onExpand}>
            <CollapsibleTrigger asChild>
              <Button variant="ghost" size="sm" className="gap-1 h-7">
                {isExpanded ? (
                  <>
                    <ChevronUp className="h-3 w-3" />
                    Hide samples
                  </>
                ) : (
                  <>
                    <ChevronDown className="h-3 w-3" />
                    Show sample matches
                  </>
                )}
              </Button>
            </CollapsibleTrigger>
            <CollapsibleContent>
              {join.sample_matches.length > 0 ? (
                <Table className="mt-2">
                  <TableHeader>
                    <TableRow>
                      <TableHead>{join.left_source}.{join.left_column}</TableHead>
                      <TableHead>{join.right_source}.{join.right_column}</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {join.sample_matches.map((match, idx) => (
                      <TableRow key={idx}>
                        <TableCell className="font-mono text-sm">{match[0]}</TableCell>
                        <TableCell className="font-mono text-sm">{match[1]}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              ) : (
                <p className="text-sm text-muted-foreground mt-2">
                  No sample matches available (pattern-based detection)
                </p>
              )}
            </CollapsibleContent>
          </Collapsible>
        </div>
      </div>
    </motion.div>
  );
}
