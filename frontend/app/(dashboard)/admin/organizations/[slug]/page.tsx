"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ArrowLeft,
  Building2,
  Users,
  Workflow,
  Activity,
  Database,
  HardDrive,
  PlayCircle,
  PauseCircle,
  CheckCircle,
  XCircle,
  Clock,
  Eye,
  AlertTriangle,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import api from "@/lib/api-client";

interface OrganizationDetails {
  id: number;
  public_id: string;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  can_sync_data: boolean;
  subscription_plan: string;
  max_users: number;
  current_user_count: number;
  logo_url: string | null;
  created_at: string;
  pipelines_count: number;
  sources_count: number;
  destinations_count: number;
  recent_runs_count: number;
}

interface Pipeline {
  id: number;
  public_id: string;
  name: string;
  description: string | null;
  is_active: boolean;
  schedule: string | null;
  last_run_status: string | null;
  last_run_at: string | null;
  created_at: string;
}

interface Run {
  id: number;
  public_id: string;
  pipeline_id: number;
  pipeline_name: string;
  status: string;
  started_at: string | null;
  completed_at: string | null;
  duration_seconds: number | null;
  rows_written: number | null;
  error_message: string | null;
  created_at: string;
}

interface Source {
  id: number;
  public_id: string;
  name: string;
  description: string | null;
  source_type: string;
  is_active: boolean;
  created_at: string;
}

interface Destination {
  id: number;
  public_id: string;
  name: string;
  description: string | null;
  destination_type: string;
  is_active: boolean;
  created_at: string;
}

interface TeamMember {
  id: number;
  public_id: string;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  email_verified: boolean;
  roles: string[];
  last_login: string | null;
  created_at: string;
}

export default function OrganizationDetailPage() {
  const params = useParams();
  const router = useRouter();
  const { toast } = useToast();
  const slug = params.slug as string;

  const [organization, setOrganization] = useState<OrganizationDetails | null>(null);
  const [pipelines, setPipelines] = useState<Pipeline[]>([]);
  const [runs, setRuns] = useState<Run[]>([]);
  const [sources, setSources] = useState<Source[]>([]);
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [team, setTeam] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState("overview");

  // First, find the org by slug to get the ID
  useEffect(() => {
    const fetchOrganization = async () => {
      try {
        // Get all organizations and find by slug
        const orgsResponse = await api.get("/admin/organizations");
        const org = orgsResponse.data.find((o: any) => o.slug === slug);

        if (!org) {
          toast({
            title: "Error",
            description: "Organization not found",
            variant: "destructive",
          });
          router.push("/admin");
          return;
        }

        // Get detailed info
        const detailsResponse = await api.get(`/admin/organizations/${org.id}/details`);
        setOrganization(detailsResponse.data);

        // Fetch related data
        const [pipelinesRes, runsRes, sourcesRes, destinationsRes, teamRes] = await Promise.all([
          api.get(`/admin/organizations/${org.id}/pipelines`),
          api.get(`/admin/organizations/${org.id}/runs`),
          api.get(`/admin/organizations/${org.id}/sources`),
          api.get(`/admin/organizations/${org.id}/destinations`),
          api.get(`/admin/organizations/${org.id}/team`),
        ]);

        setPipelines(pipelinesRes.data.pipelines || []);
        setRuns(runsRes.data.runs || []);
        setSources(sourcesRes.data.sources || []);
        setDestinations(destinationsRes.data.destinations || []);
        setTeam(teamRes.data.team || []);
      } catch (error: any) {
        toast({
          title: "Error",
          description: error.response?.data?.detail || "Failed to fetch organization details",
          variant: "destructive",
        });
      } finally {
        setLoading(false);
      }
    };

    fetchOrganization();
  }, [slug, router, toast]);

  const handleStartImpersonation = async () => {
    if (!organization) return;

    try {
      const response = await api.post(`/admin/impersonate/${organization.id}`);
      toast({
        title: "Impersonation Started",
        description: response.data.message,
      });
      // Refresh page to show impersonation banner
      window.location.reload();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to start impersonation",
        variant: "destructive",
      });
    }
  };

  const getStatusBadge = (status: string) => {
    const variants: Record<string, { color: string; icon: any }> = {
      completed: { color: "bg-green-100 text-green-800", icon: CheckCircle },
      running: { color: "bg-blue-100 text-blue-800", icon: PlayCircle },
      pending: { color: "bg-yellow-100 text-yellow-800", icon: Clock },
      failed: { color: "bg-red-100 text-red-800", icon: XCircle },
      cancelled: { color: "bg-gray-100 text-gray-800", icon: PauseCircle },
    };

    const config = variants[status] || variants.pending;
    const Icon = config.icon;

    return (
      <Badge variant="outline" className={`${config.color} gap-1`}>
        <Icon className="h-3 w-3" />
        {status}
      </Badge>
    );
  };

  const getPlanBadge = (plan: string) => {
    const variants: Record<string, string> = {
      starter: "bg-gray-100 text-gray-800",
      professional: "bg-blue-100 text-blue-800",
      enterprise: "bg-purple-100 text-purple-800",
    };

    return (
      <Badge variant="outline" className={variants[plan] || variants.starter}>
        {plan.charAt(0).toUpperCase() + plan.slice(1)}
      </Badge>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Loading organization details...</div>
      </div>
    );
  }

  if (!organization) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground">Organization not found</div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Button variant="ghost" size="sm" onClick={() => router.push("/admin")}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Admin
          </Button>
          <div>
            <div className="flex items-center gap-3">
              {organization.logo_url ? (
                <img
                  src={organization.logo_url}
                  alt={organization.name}
                  className="h-10 w-10 rounded-lg"
                />
              ) : (
                <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                  <Building2 className="h-6 w-6 text-primary" />
                </div>
              )}
              <div>
                <h1 className="text-2xl font-bold">{organization.name}</h1>
                <p className="text-sm text-muted-foreground">{organization.slug}</p>
              </div>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className="bg-amber-100 text-amber-800 gap-1">
            <Eye className="h-3 w-3" />
            READ-ONLY
          </Badge>
          <Button variant="outline" onClick={handleStartImpersonation}>
            <Eye className="h-4 w-4 mr-2" />
            Impersonate
          </Button>
        </div>
      </div>

      {/* Organization Info Card */}
      <Card>
        <CardHeader>
          <CardTitle>Organization Details</CardTitle>
          <CardDescription>
            {organization.description || "No description provided"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
            <div>
              <p className="text-sm text-muted-foreground">Status</p>
              <div className="flex items-center gap-2 mt-1">
                {organization.is_active ? (
                  <Badge variant="outline" className="bg-green-100 text-green-800 gap-1">
                    <PlayCircle className="h-3 w-3" />
                    Active
                  </Badge>
                ) : (
                  <Badge variant="outline" className="bg-red-100 text-red-800 gap-1">
                    <PauseCircle className="h-3 w-3" />
                    Inactive
                  </Badge>
                )}
              </div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Sync Status</p>
              <div className="flex items-center gap-2 mt-1">
                {organization.can_sync_data ? (
                  <Badge variant="outline" className="bg-blue-100 text-blue-800">
                    Enabled
                  </Badge>
                ) : (
                  <Badge variant="outline" className="bg-orange-100 text-orange-800 gap-1">
                    <AlertTriangle className="h-3 w-3" />
                    Disabled
                  </Badge>
                )}
              </div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Plan</p>
              <div className="mt-1">{getPlanBadge(organization.subscription_plan)}</div>
            </div>
            <div>
              <p className="text-sm text-muted-foreground">Users</p>
              <p className="font-medium mt-1">
                {organization.current_user_count} / {organization.max_users}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-4 mt-6 pt-6 border-t">
            <div className="text-center">
              <div className="flex items-center justify-center gap-2">
                <Workflow className="h-5 w-5 text-muted-foreground" />
                <span className="text-2xl font-bold">{organization.pipelines_count}</span>
              </div>
              <p className="text-sm text-muted-foreground">Pipelines</p>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-2">
                <Database className="h-5 w-5 text-muted-foreground" />
                <span className="text-2xl font-bold">{organization.sources_count}</span>
              </div>
              <p className="text-sm text-muted-foreground">Sources</p>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-2">
                <HardDrive className="h-5 w-5 text-muted-foreground" />
                <span className="text-2xl font-bold">{organization.destinations_count}</span>
              </div>
              <p className="text-sm text-muted-foreground">Destinations</p>
            </div>
            <div className="text-center">
              <div className="flex items-center justify-center gap-2">
                <Activity className="h-5 w-5 text-muted-foreground" />
                <span className="text-2xl font-bold">{organization.recent_runs_count}</span>
              </div>
              <p className="text-sm text-muted-foreground">Runs (7d)</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Tabs for different views */}
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="pipelines">Pipelines ({pipelines.length})</TabsTrigger>
          <TabsTrigger value="runs">Runs ({runs.length})</TabsTrigger>
          <TabsTrigger value="sources">Sources ({sources.length})</TabsTrigger>
          <TabsTrigger value="destinations">Destinations ({destinations.length})</TabsTrigger>
          <TabsTrigger value="team">Team ({team.length})</TabsTrigger>
        </TabsList>

        {/* Overview Tab */}
        <TabsContent value="overview" className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Recent Pipelines */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Recent Pipelines</CardTitle>
              </CardHeader>
              <CardContent>
                {pipelines.length === 0 ? (
                  <p className="text-muted-foreground text-sm">No pipelines</p>
                ) : (
                  <div className="space-y-2">
                    {pipelines.slice(0, 5).map((pipeline) => (
                      <div
                        key={pipeline.id}
                        className="flex items-center justify-between p-2 rounded-lg bg-muted/50"
                      >
                        <div>
                          <p className="font-medium text-sm">{pipeline.name}</p>
                          <p className="text-xs text-muted-foreground">
                            {pipeline.schedule || "No schedule"}
                          </p>
                        </div>
                        {pipeline.last_run_status && getStatusBadge(pipeline.last_run_status)}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Recent Runs */}
            <Card>
              <CardHeader>
                <CardTitle className="text-lg">Recent Runs</CardTitle>
              </CardHeader>
              <CardContent>
                {runs.length === 0 ? (
                  <p className="text-muted-foreground text-sm">No runs</p>
                ) : (
                  <div className="space-y-2">
                    {runs.slice(0, 5).map((run) => (
                      <div
                        key={run.id}
                        className="flex items-center justify-between p-2 rounded-lg bg-muted/50"
                      >
                        <div>
                          <p className="font-medium text-sm">{run.pipeline_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {new Date(run.created_at).toLocaleString()}
                          </p>
                        </div>
                        {getStatusBadge(run.status)}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
        </TabsContent>

        {/* Pipelines Tab */}
        <TabsContent value="pipelines">
          <Card>
            <CardContent className="pt-6">
              {pipelines.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No pipelines</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Schedule</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Last Run</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {pipelines.map((pipeline) => (
                      <TableRow key={pipeline.id}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{pipeline.name}</p>
                            {pipeline.description && (
                              <p className="text-xs text-muted-foreground">
                                {pipeline.description}
                              </p>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>{pipeline.schedule || "-"}</TableCell>
                        <TableCell>
                          {pipeline.is_active ? (
                            <Badge variant="outline" className="bg-green-100 text-green-800">
                              Active
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="bg-gray-100 text-gray-800">
                              Inactive
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          {pipeline.last_run_status ? (
                            <div>
                              {getStatusBadge(pipeline.last_run_status)}
                              <p className="text-xs text-muted-foreground mt-1">
                                {pipeline.last_run_at &&
                                  new Date(pipeline.last_run_at).toLocaleString()}
                              </p>
                            </div>
                          ) : (
                            "-"
                          )}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {new Date(pipeline.created_at).toLocaleDateString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Runs Tab */}
        <TabsContent value="runs">
          <Card>
            <CardContent className="pt-6">
              {runs.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No runs</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Pipeline</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Duration</TableHead>
                      <TableHead>Rows</TableHead>
                      <TableHead>Started</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {runs.map((run) => (
                      <TableRow key={run.id}>
                        <TableCell className="font-medium">{run.pipeline_name}</TableCell>
                        <TableCell>{getStatusBadge(run.status)}</TableCell>
                        <TableCell>
                          {run.duration_seconds
                            ? `${Math.round(run.duration_seconds)}s`
                            : "-"}
                        </TableCell>
                        <TableCell>
                          {run.rows_written?.toLocaleString() || "-"}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {run.started_at
                            ? new Date(run.started_at).toLocaleString()
                            : new Date(run.created_at).toLocaleString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Sources Tab */}
        <TabsContent value="sources">
          <Card>
            <CardContent className="pt-6">
              {sources.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No sources</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {sources.map((source) => (
                      <TableRow key={source.id}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{source.name}</p>
                            {source.description && (
                              <p className="text-xs text-muted-foreground">
                                {source.description}
                              </p>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{source.source_type}</Badge>
                        </TableCell>
                        <TableCell>
                          {source.is_active ? (
                            <Badge variant="outline" className="bg-green-100 text-green-800">
                              Active
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="bg-gray-100 text-gray-800">
                              Inactive
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {new Date(source.created_at).toLocaleDateString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Destinations Tab */}
        <TabsContent value="destinations">
          <Card>
            <CardContent className="pt-6">
              {destinations.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No destinations</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>Name</TableHead>
                      <TableHead>Type</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Created</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {destinations.map((dest) => (
                      <TableRow key={dest.id}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{dest.name}</p>
                            {dest.description && (
                              <p className="text-xs text-muted-foreground">
                                {dest.description}
                              </p>
                            )}
                          </div>
                        </TableCell>
                        <TableCell>
                          <Badge variant="secondary">{dest.destination_type}</Badge>
                        </TableCell>
                        <TableCell>
                          {dest.is_active ? (
                            <Badge variant="outline" className="bg-green-100 text-green-800">
                              Active
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="bg-gray-100 text-gray-800">
                              Inactive
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {new Date(dest.created_at).toLocaleDateString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Team Tab */}
        <TabsContent value="team">
          <Card>
            <CardContent className="pt-6">
              {team.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">No team members</p>
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>User</TableHead>
                      <TableHead>Roles</TableHead>
                      <TableHead>Status</TableHead>
                      <TableHead>Last Login</TableHead>
                      <TableHead>Joined</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {team.map((member) => (
                      <TableRow key={member.id}>
                        <TableCell>
                          <div>
                            <p className="font-medium">{member.full_name || member.username}</p>
                            <p className="text-xs text-muted-foreground">{member.email}</p>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="flex gap-1 flex-wrap">
                            {member.roles.map((role) => (
                              <Badge key={role} variant="secondary" className="text-xs">
                                {role}
                              </Badge>
                            ))}
                          </div>
                        </TableCell>
                        <TableCell>
                          {member.is_active ? (
                            <Badge variant="outline" className="bg-green-100 text-green-800">
                              Active
                            </Badge>
                          ) : (
                            <Badge variant="outline" className="bg-gray-100 text-gray-800">
                              Inactive
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {member.last_login
                            ? new Date(member.last_login).toLocaleString()
                            : "Never"}
                        </TableCell>
                        <TableCell className="text-muted-foreground text-sm">
                          {new Date(member.created_at).toLocaleDateString()}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
