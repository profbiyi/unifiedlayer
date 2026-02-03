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
import { useToast } from "@/hooks/use-toast";
import { Copy, X, Clock } from "lucide-react";
import api from "@/lib/api-client";
import Link from "next/link";

interface Invitation {
  id: number;
  public_id: string;
  email: string;
  role_name: string;
  invited_by_name: string;
  token: string;
  expires_at: string;
  created_at: string;
  is_expired: boolean;
  is_valid: boolean;
}

export default function InvitationsPage() {
  const [invitations, setInvitations] = useState<Invitation[]>([]);
  const [loading, setLoading] = useState(true);
  const { toast } = useToast();

  const fetchInvitations = async () => {
    try {
      const response = await api.get("/invitations/pending");
      setInvitations(response.data);
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to fetch invitations",
        variant: "destructive",
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvitations();
  }, []);

  const handleCancelInvitation = async (invitationId: number, email: string) => {
    if (!confirm(`Are you sure you want to cancel the invitation for ${email}?`)) {
      return;
    }

    try {
      await api.delete(`/invitations/${invitationId}`);

      toast({
        title: "Success",
        description: "Invitation cancelled successfully",
      });

      fetchInvitations();
    } catch (error: any) {
      toast({
        title: "Error",
        description: error.response?.data?.detail || "Failed to cancel invitation",
        variant: "destructive",
      });
    }
  };

  const copyInvitationLink = (token: string) => {
    const link = `${window.location.origin}/accept-invitation?token=${token}`;
    navigator.clipboard.writeText(link);

    toast({
      title: "Copied!",
      description: "Invitation link copied to clipboard",
    });
  };

  const getDaysUntilExpiry = (expiresAt: string) => {
    const now = new Date();
    const expiry = new Date(expiresAt);
    const diffTime = expiry.getTime() - now.getTime();
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    return diffDays;
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Pending Invitations</h1>
          <p className="text-muted-foreground">
            Manage invitations you've sent to join your organization
          </p>
        </div>

        <Link href="/team">
          <Button variant="outline">Back to Team</Button>
        </Link>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Sent Invitations</CardTitle>
          <CardDescription>
            {invitations.length} pending {invitations.length === 1 ? "invitation" : "invitations"}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="text-center py-8 text-muted-foreground">Loading...</div>
          ) : invitations.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground">
              No pending invitations. All invitations have been accepted or expired.
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Email</TableHead>
                  <TableHead>Role</TableHead>
                  <TableHead>Invited By</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead>Sent</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {invitations.map((invitation) => {
                  const daysLeft = getDaysUntilExpiry(invitation.expires_at);

                  return (
                    <TableRow key={invitation.id}>
                      <TableCell>
                        <div className="font-medium">{invitation.email}</div>
                      </TableCell>
                      <TableCell>
                        <Badge variant="outline">{invitation.role_name}</Badge>
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {invitation.invited_by_name}
                      </TableCell>
                      <TableCell>
                        {invitation.is_expired ? (
                          <Badge variant="destructive" className="gap-1">
                            <Clock className="h-3 w-3" />
                            Expired
                          </Badge>
                        ) : (
                          <Badge
                            variant="outline"
                            className={
                              daysLeft <= 1
                                ? "bg-orange-50 text-orange-700 border-orange-200"
                                : "bg-blue-50 text-blue-700 border-blue-200"
                            }
                          >
                            {daysLeft <= 1 ? `Expires in ${daysLeft} day` : `${daysLeft} days left`}
                          </Badge>
                        )}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {new Date(invitation.created_at).toLocaleDateString()}
                      </TableCell>
                      <TableCell className="text-right">
                        <div className="flex items-center justify-end gap-2">
                          {!invitation.is_expired && (
                            <Button
                              variant="ghost"
                              size="sm"
                              onClick={() => copyInvitationLink(invitation.token)}
                            >
                              <Copy className="h-4 w-4" />
                            </Button>
                          )}
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() =>
                              handleCancelInvitation(invitation.id, invitation.email)
                            }
                          >
                            <X className="h-4 w-4" />
                          </Button>
                        </div>
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
