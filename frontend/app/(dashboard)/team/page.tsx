"use client";

import { useEffect, useState } from "react";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useToast } from "@/hooks/use-toast";
import { UserPlus, MoreVertical, Shield, User as UserIcon, Mail } from "lucide-react";
import api from "@/lib/api-client";
import Link from "next/link";

interface TeamMember {
  id: number;
  public_id: string;
  email: string;
  username: string;
  full_name: string | null;
  is_active: boolean;
  roles: string[];
  last_login: string | null;
  created_at: string;
}

export default function TeamPage() {
  const [teamMembers, setTeamMembers] = useState<TeamMember[]>([]);
  const [loading, setLoading] = useState(true);
  const [inviteDialogOpen, setInviteDialogOpen] = useState(false);
  const [inviteEmail, setInviteEmail] = useState("");
  const [inviteRole, setInviteRole] = useState("org_user");
  const [inviting, setInviting] = useState(false);
  const { toast } = useToast();

  const fetchTeamMembers = async () => {
    try {
      const response = await api.get("/organizations/me/users");
      setTeamMembers(response.data);
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to fetch team members",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTeamMembers();
  }, []);

  const handleInvite = async () => {
    if (!inviteEmail) {
      toast({
        title: "Error",
        description: "Please enter an email address",
        variant: "destructive",
      });
      return;
    }

    setInviting(true);
    try {
      await api.post("/invitations/invite", {
        email: inviteEmail,
        role_slug: inviteRole,
      });

      toast({
        title: "Success",
        description: `Invitation sent to ${inviteEmail}`,
      });

      setInviteDialogOpen(false);
      setInviteEmail("");
      setInviteRole("org_user");
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to send invitation",
        variant: "destructive",
      });
    } finally {
      setInviting(false);
    }
  };

  const handleChangeRole = async (userId: number, newRole: string) => {
    try {
      await api.put(`/organizations/me/users/${userId}/role`, {
        role_slug: newRole,
      });

      toast({
        title: "Success",
        description: "Role updated successfully",
      });

      fetchTeamMembers();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to update role",
        variant: "destructive",
      });
    }
  };

  const handleDeactivate = async (userId: number) => {
    try {
      await api.patch(`/organizations/me/users/${userId}/deactivate`);

      toast({
        title: "Success",
        description: "User deactivated successfully",
      });

      fetchTeamMembers();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to deactivate user",
        variant: "destructive",
      });
    }
  };

  const handleActivate = async (userId: number) => {
    try {
      await api.patch(`/organizations/me/users/${userId}/activate`);

      toast({
        title: "Success",
        description: "User activated successfully",
      });

      fetchTeamMembers();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to activate user",
        variant: "destructive",
      });
    }
  };

  const handleRemove = async (userId: number, email: string) => {
    if (!confirm(`Are you sure you want to remove ${email} from your organization?`)) {
      return;
    }

    try {
      await api.delete(`/organizations/me/users/${userId}`);

      toast({
        title: "Success",
        description: "User removed successfully",
      });

      fetchTeamMembers();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to remove user",
        variant: "destructive",
      });
    }
  };

  const getRoleBadgeVariant = (roles: string[]) => {
    if (roles.includes("ORG_ADMIN")) return "default";
    return "secondary";
  };

  const getRoleIcon = (roles: string[]) => {
    if (roles.includes("ORG_ADMIN")) return <Shield className="h-3 w-3" />;
    return <UserIcon className="h-3 w-3" />;
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Team Members</h1>
          <p className="text-muted-foreground">
            Manage your organization&apos;s users and their roles
          </p>
        </div>

        <div className="flex gap-2">
          <Link href="/team/invitations">
            <Button variant="outline">
              <Mail className="mr-2 h-4 w-4" />
              Pending Invitations
            </Button>
          </Link>

          <Dialog open={inviteDialogOpen} onOpenChange={setInviteDialogOpen}>
            <DialogTrigger asChild>
              <Button>
                <UserPlus className="mr-2 h-4 w-4" />
                Invite User
              </Button>
            </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Invite Team Member</DialogTitle>
              <DialogDescription>
                Send an invitation to join your organization. They&apos;ll receive an email with a link to create their account.
              </DialogDescription>
            </DialogHeader>

            <div className="space-y-4 py-4">
              <div className="space-y-2">
                <Label htmlFor="email">Email Address</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="user@company.com"
                  value={inviteEmail}
                  onChange={(e) => setInviteEmail(e.target.value)}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="role">Role</Label>
                <Select value={inviteRole} onValueChange={setInviteRole}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="org_user">
                      <div className="flex items-center gap-2">
                        <UserIcon className="h-4 w-4" />
                        <div>
                          <div className="font-medium">User</div>
                          <div className="text-xs text-muted-foreground">
                            Read-only access to pipelines and data
                          </div>
                        </div>
                      </div>
                    </SelectItem>
                    <SelectItem value="org_admin">
                      <div className="flex items-center gap-2">
                        <Shield className="h-4 w-4" />
                        <div>
                          <div className="font-medium">Admin</div>
                          <div className="text-xs text-muted-foreground">
                            Full access to manage organization
                          </div>
                        </div>
                      </div>
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setInviteDialogOpen(false)}>
                Cancel
              </Button>
              <Button onClick={handleInvite} disabled={inviting}>
                {inviting ? "Sending..." : "Send Invitation"}
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>
    </div>

      <Card>
        <CardHeader>
          <CardTitle>Organization Members</CardTitle>
          <CardDescription>
            {teamMembers.length} {teamMembers.length === 1 ? "member" : "members"} in your organization
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">Loading...</div>
          ) : teamMembers.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No team members yet. Invite your first user to get started!
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Last Login</TableHead>
                  <TableHead>Joined</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {teamMembers.map((member) => (
                  <TableRow key={member.id}>
                    <TableCell>
                      <div>
                        <div className="font-medium">{member.full_name || member.username}</div>
                        <div className="text-sm text-muted-foreground">{member.email}</div>
                      </div>
                    </TableCell>
                    <TableCell>
                      <Badge variant={getRoleBadgeVariant(member.roles)} className="gap-1">
                        {getRoleIcon(member.roles)}
                        {member.roles.join(", ")}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {member.is_active ? (
                        <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">
                          Active
                        </Badge>
                      ) : (
                        <Badge variant="outline" className="bg-gray-50 text-gray-700 border-gray-200">
                          Inactive
                        </Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {member.last_login
                        ? new Date(member.last_login).toLocaleDateString()
                        : "Never"}
                    </TableCell>
                    <TableCell className="text-sm text-muted-foreground">
                      {new Date(member.created_at).toLocaleDateString()}
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuLabel>Actions</DropdownMenuLabel>
                          <DropdownMenuSeparator />

                          {member.roles.includes("ORG_ADMIN") ? (
                            <DropdownMenuItem
                              onClick={() => handleChangeRole(member.id, "org_user")}
                            >
                              Change to User
                            </DropdownMenuItem>
                          ) : (
                            <DropdownMenuItem
                              onClick={() => handleChangeRole(member.id, "org_admin")}
                            >
                              Promote to Admin
                            </DropdownMenuItem>
                          )}

                          <DropdownMenuSeparator />

                          {member.is_active ? (
                            <DropdownMenuItem
                              onClick={() => handleDeactivate(member.id)}
                            >
                              Deactivate
                            </DropdownMenuItem>
                          ) : (
                            <DropdownMenuItem
                              onClick={() => handleActivate(member.id)}
                            >
                              Activate
                            </DropdownMenuItem>
                          )}

                          <DropdownMenuSeparator />

                          <DropdownMenuItem
                            onClick={() => handleRemove(member.id, member.email)}
                            className="text-destructive"
                          >
                            Remove from Organization
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
