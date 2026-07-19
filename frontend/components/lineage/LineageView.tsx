"use client";

import { useEffect, useState, useCallback, useMemo } from "react";
import ReactFlow, {
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  Node,
  Edge,
  BackgroundVariant,
  MarkerType,
  Panel,
  NodeMouseHandler,
} from "reactflow";
import dagre from "dagre";
import "reactflow/dist/style.css";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  Loader2,
  Database,
  Workflow,
  HardDrive,
  RefreshCw,
  Search,
  AlertTriangle,
  CheckCircle,
  XCircle,
  Clock,
  ExternalLink,
  Table,
  Zap,
} from "lucide-react";
import api from "@/lib/api-client";
import { useRouter } from "next/navigation";
import toast from "react-hot-toast";

// Dagre layout configuration
const dagreGraph = new dagre.graphlib.Graph();
dagreGraph.setDefaultEdgeLabel(() => ({}));

const nodeWidth = 220;
const nodeHeight = 100;

const getLayoutedElements = (nodes: Node[], edges: Edge[], direction = "LR") => {
  const isHorizontal = direction === "LR";
  dagreGraph.setGraph({ rankdir: direction, nodesep: 80, ranksep: 150 });

  nodes.forEach((node) => {
    dagreGraph.setNode(node.id, { width: nodeWidth, height: nodeHeight });
  });

  edges.forEach((edge) => {
    dagreGraph.setEdge(edge.source, edge.target);
  });

  dagre.layout(dagreGraph);

  const layoutedNodes = nodes.map((node) => {
    const nodeWithPosition = dagreGraph.node(node.id);
    return {
      ...node,
      position: {
        x: nodeWithPosition.x - nodeWidth / 2,
        y: nodeWithPosition.y - nodeHeight / 2,
      },
    };
  });

  return { nodes: layoutedNodes, edges };
};

// Custom node components
function SourceNode({ data, selected }: { data: any; selected?: boolean }) {
  return (
    <div
      className={`px-4 py-3 shadow-lg rounded-lg bg-gradient-to-br from-blue-50 to-blue-100 border-2 min-w-[200px] transition-all ${
        selected ? "border-blue-600 ring-2 ring-blue-300" : "border-blue-400"
      }`}
    >
      <div className="flex items-center gap-2 mb-2">
        <div className="p-1.5 bg-blue-500 rounded">
          <Database className="h-4 w-4 text-white" />
        </div>
        <div className="font-bold text-blue-900 truncate">{data.name}</div>
      </div>
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="text-xs border-blue-300 text-blue-700">
          {data.sourceType}
        </Badge>
        <span className="text-xs text-blue-600">{data.pipelineCount} pipelines</span>
      </div>
    </div>
  );
}

function PipelineNode({ data, selected }: { data: any; selected?: boolean }) {
  const statusConfig: Record<string, { icon: any; color: string; bg: string }> = {
    completed: { icon: CheckCircle, color: "text-green-600", bg: "bg-green-100" },
    running: { icon: Zap, color: "text-purple-600", bg: "bg-purple-100" },
    failed: { icon: XCircle, color: "text-red-600", bg: "bg-red-100" },
    pending: { icon: Clock, color: "text-yellow-600", bg: "bg-yellow-100" },
  };

  const status = data.latestStatus?.toLowerCase() || "pending";
  const StatusIcon = statusConfig[status]?.icon || Clock;

  return (
    <div
      className={`px-4 py-3 shadow-lg rounded-lg bg-gradient-to-br from-purple-50 to-purple-100 border-2 min-w-[200px] transition-all ${
        selected ? "border-purple-600 ring-2 ring-purple-300" : "border-purple-400"
      }`}
    >
      <div className="flex items-center gap-2 mb-2">
        <div className="p-1.5 bg-purple-500 rounded">
          <Workflow className="h-4 w-4 text-white" />
        </div>
        <div className="font-bold text-purple-900 truncate flex-1">{data.name}</div>
        <StatusIcon className={`h-4 w-4 ${statusConfig[status]?.color || "text-gray-500"}`} />
      </div>
      <div className="flex items-center gap-2">
        {data.isActive ? (
          <Badge className="text-xs bg-green-600 hover:bg-green-600">Active</Badge>
        ) : (
          <Badge variant="secondary" className="text-xs">Inactive</Badge>
        )}
        {data.schedule && (
          <span className="text-xs text-purple-600 truncate">{data.schedule}</span>
        )}
      </div>
    </div>
  );
}

function DestinationNode({ data, selected }: { data: any; selected?: boolean }) {
  return (
    <div
      className={`px-4 py-3 shadow-lg rounded-lg bg-gradient-to-br from-emerald-50 to-emerald-100 border-2 min-w-[200px] transition-all ${
        selected ? "border-emerald-600 ring-2 ring-emerald-300" : "border-emerald-400"
      }`}
    >
      <div className="flex items-center gap-2 mb-2">
        <div className="p-1.5 bg-emerald-500 rounded">
          <HardDrive className="h-4 w-4 text-white" />
        </div>
        <div className="font-bold text-emerald-900 truncate">{data.name}</div>
      </div>
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="text-xs border-emerald-300 text-emerald-700">
          {data.destinationType}
        </Badge>
        <span className="text-xs text-emerald-600">{data.pipelineCount} pipelines</span>
      </div>
    </div>
  );
}

function TableNode({ data, selected }: { data: any; selected?: boolean }) {
  return (
    <div
      className={`px-4 py-3 shadow-lg rounded-lg bg-gradient-to-br from-gray-50 to-gray-100 border-2 min-w-[180px] transition-all ${
        selected ? "border-gray-600 ring-2 ring-gray-300" : "border-gray-400"
      }`}
    >
      <div className="flex items-center gap-2">
        <Table className="h-4 w-4 text-gray-600" />
        <div className="font-medium text-gray-900 truncate">{data.name}</div>
      </div>
      {data.schema && (
        <div className="text-xs text-gray-500 mt-1">{data.schema}</div>
      )}
    </div>
  );
}

const nodeTypes = {
  source: SourceNode,
  pipeline: PipelineNode,
  destination: DestinationNode,
  table: TableNode,
};

const defaultEdgeOptions = {
  type: "smoothstep",
  markerEnd: {
    type: MarkerType.ArrowClosed,
    width: 20,
    height: 20,
  },
  style: {
    strokeWidth: 2,
  },
};

export default function LineageView() {
  const router = useRouter();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [stats, setStats] = useState({
    sources: 0,
    pipelines: 0,
    destinations: 0,
    activePipelines: 0,
  });
  const [selectedNode, setSelectedNode] = useState<any>(null);
  const [sheetOpen, setSheetOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [impactAnalysis, setImpactAnalysis] = useState<any>(null);

  useEffect(() => {
    fetchLineage();
  }, []);

  const fetchLineage = async () => {
    try {
      const response = await api.get("/lineage/pipeline-graph");
      const { nodes: apiNodes, edges: apiEdges, stats: apiStats } = response.data;

      // Apply dagre layout
      const { nodes: layoutedNodes, edges: layoutedEdges } = getLayoutedElements(
        apiNodes.map((n: any) => ({
          ...n,
          position: { x: 0, y: 0 },
        })),
        apiEdges.map((e: any) => ({
          ...e,
          // React Flow requires a unique edge id or the edge (the arrow) is
          // silently dropped — the API doesn't send one, so derive it.
          id: e.id || `e-${e.source}-${e.target}`,
          ...defaultEdgeOptions,
          animated: e.animated,
          style: {
            ...defaultEdgeOptions.style,
            stroke: e.animated ? "#8b5cf6" : "#94a3b8",
          },
        }))
      );

      setNodes(layoutedNodes);
      setEdges(layoutedEdges);
      setStats(apiStats);
    } catch (error) {
      toast.error("Failed to load lineage data");
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      await api.post("/lineage/refresh");
      toast.success("Lineage refreshed successfully");
      await fetchLineage();
    } catch (error) {
      toast.error("Failed to refresh lineage");
    } finally {
      setRefreshing(false);
    }
  };

  const handleNodeClick: NodeMouseHandler = useCallback(async (event, node) => {
    setSelectedNode(node);
    setSheetOpen(true);

    // Fetch impact analysis for the node
    if (node.data.id) {
      try {
        const response = await api.get(`/lineage/impact/${node.data.id}`);
        setImpactAnalysis(response.data);
      } catch (error) {
        setImpactAnalysis(null);
      }
    }
  }, []);

  const handleNavigate = (type: string, publicId: string) => {
    switch (type) {
      case "source":
        router.push(`/sources/${publicId}`);
        break;
      case "pipeline":
        router.push(`/pipelines/${publicId}`);
        break;
      case "destination":
        router.push(`/destinations`);
        break;
    }
  };

  // Filter nodes based on search query
  const filteredNodes = useMemo(() => {
    if (!searchQuery) return nodes;
    const query = searchQuery.toLowerCase();
    return nodes.filter((node) =>
      node.data.name?.toLowerCase().includes(query) ||
      node.type?.toLowerCase().includes(query)
    );
  }, [nodes, searchQuery]);

  // Highlight matching nodes
  const highlightedNodes = useMemo(() => {
    if (!searchQuery) return filteredNodes;
    return filteredNodes.map((node) => ({
      ...node,
      style: {
        ...node.style,
        opacity: node.data.name?.toLowerCase().includes(searchQuery.toLowerCase()) ? 1 : 0.3,
      },
    }));
  }, [filteredNodes, searchQuery]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Data Lineage</h1>
          <p className="text-muted-foreground">
            Visualize data flow and dependencies across your organization
          </p>
        </div>
        <Button
          variant="outline"
          onClick={handleRefresh}
          disabled={refreshing}
        >
          {refreshing ? (
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
          ) : (
            <RefreshCw className="h-4 w-4 mr-2" />
          )}
          Refresh Lineage
        </Button>
      </div>

      {/* Stats */}
      <div className="grid gap-4 md:grid-cols-4">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Database className="h-4 w-4" />
              Sources
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.sources}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Workflow className="h-4 w-4" />
              Pipelines
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.pipelines}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <HardDrive className="h-4 w-4" />
              Destinations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.destinations}</div>
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-muted-foreground flex items-center gap-2">
              <Zap className="h-4 w-4" />
              Active Pipelines
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">{stats.activePipelines}</div>
          </CardContent>
        </Card>
      </div>

      {/* Lineage Graph */}
      <Card className="p-0 overflow-hidden">
        <div style={{ height: "70vh" }}>
          <ReactFlow
            nodes={searchQuery ? highlightedNodes : nodes}
            edges={edges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={handleNodeClick}
            nodeTypes={nodeTypes}
            defaultEdgeOptions={defaultEdgeOptions}
            fitView
            attributionPosition="bottom-left"
            minZoom={0.2}
            maxZoom={2}
          >
            <Panel position="top-left" className="bg-background/80 backdrop-blur-sm p-2 rounded-lg border shadow-sm">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search nodes..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 w-64"
                />
              </div>
            </Panel>
            <Controls />
            <MiniMap
              nodeColor={(node) => {
                switch (node.type) {
                  case "source":
                    return "#3b82f6";
                  case "pipeline":
                    return "#8b5cf6";
                  case "destination":
                    return "#10b981";
                  default:
                    return "#94a3b8";
                }
              }}
            />
            <Background variant={BackgroundVariant.Dots} gap={12} size={1} />
          </ReactFlow>
        </div>
      </Card>

      {/* Node Details Sheet */}
      <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
        <SheetContent className="w-[400px] sm:w-[540px] overflow-y-auto">
          {selectedNode && (
            <>
              <SheetHeader>
                <SheetTitle className="flex items-center gap-2">
                  {selectedNode.type === "source" && <Database className="h-5 w-5 text-blue-600" />}
                  {selectedNode.type === "pipeline" && <Workflow className="h-5 w-5 text-purple-600" />}
                  {selectedNode.type === "destination" && <HardDrive className="h-5 w-5 text-emerald-600" />}
                  {selectedNode.data.name}
                </SheetTitle>
                <SheetDescription>
                  {selectedNode.type === "source" && "Data Source"}
                  {selectedNode.type === "pipeline" && "Data Pipeline"}
                  {selectedNode.type === "destination" && "Data Destination"}
                </SheetDescription>
              </SheetHeader>

              <div className="mt-6 space-y-6">
                {/* Node Details */}
                <div>
                  <h3 className="text-sm font-semibold mb-3">Details</h3>
                  <div className="space-y-2 text-sm">
                    {selectedNode.type === "source" && (
                      <>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Type</span>
                          <Badge variant="outline">{selectedNode.data.sourceType}</Badge>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Pipelines</span>
                          <span>{selectedNode.data.pipelineCount}</span>
                        </div>
                      </>
                    )}
                    {selectedNode.type === "pipeline" && (
                      <>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Status</span>
                          <Badge
                            variant={selectedNode.data.isActive ? "default" : "secondary"}
                          >
                            {selectedNode.data.isActive ? "Active" : "Inactive"}
                          </Badge>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Last Run</span>
                          <Badge
                            variant={
                              selectedNode.data.latestStatus === "completed"
                                ? "default"
                                : selectedNode.data.latestStatus === "failed"
                                ? "destructive"
                                : "secondary"
                            }
                          >
                            {selectedNode.data.latestStatus || "Never"}
                          </Badge>
                        </div>
                        {selectedNode.data.schedule && (
                          <div className="flex justify-between">
                            <span className="text-muted-foreground">Schedule</span>
                            <span className="font-mono text-xs">{selectedNode.data.schedule}</span>
                          </div>
                        )}
                      </>
                    )}
                    {selectedNode.type === "destination" && (
                      <>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Type</span>
                          <Badge variant="outline">{selectedNode.data.destinationType}</Badge>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-muted-foreground">Pipelines</span>
                          <span>{selectedNode.data.pipelineCount}</span>
                        </div>
                      </>
                    )}
                  </div>
                </div>

                {/* Impact Analysis */}
                {impactAnalysis && impactAnalysis.total_impacted > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                      <AlertTriangle className="h-4 w-4 text-yellow-500" />
                      Impact Analysis
                    </h3>
                    <div className="p-3 bg-yellow-50 dark:bg-yellow-900/20 rounded-lg text-sm">
                      <p className="text-yellow-800 dark:text-yellow-200 mb-2">
                        Changes to this node will affect:
                      </p>
                      <ul className="space-y-1 text-yellow-700 dark:text-yellow-300">
                        {impactAnalysis.impacted_tables > 0 && (
                          <li className="flex items-center gap-2">
                            <Table className="h-3 w-3" />
                            {impactAnalysis.impacted_tables} tables
                          </li>
                        )}
                        {impactAnalysis.impacted_destinations > 0 && (
                          <li className="flex items-center gap-2">
                            <HardDrive className="h-3 w-3" />
                            {impactAnalysis.impacted_destinations} destinations
                          </li>
                        )}
                        {impactAnalysis.affected_pipelines?.length > 0 && (
                          <li className="flex items-center gap-2">
                            <Workflow className="h-3 w-3" />
                            {impactAnalysis.affected_pipelines.length} pipelines
                          </li>
                        )}
                      </ul>
                    </div>
                  </div>
                )}

                {/* Navigation Button */}
                <Button
                  className="w-full"
                  onClick={() =>
                    handleNavigate(selectedNode.type, selectedNode.data.public_id)
                  }
                >
                  <ExternalLink className="h-4 w-4 mr-2" />
                  View {selectedNode.type === "source" ? "Source" : selectedNode.type === "pipeline" ? "Pipeline" : "Destination"}
                </Button>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
