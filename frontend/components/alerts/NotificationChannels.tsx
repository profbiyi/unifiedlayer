"use client";

import { useState, useEffect } from "react";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  useNotificationChannels,
  useUpdateNotificationChannels,
  useTestSlackWebhook,
} from "@/hooks/queries/useAlerts";
import {
  Slack,
  Mail,
  Plus,
  X,
  Loader2,
  Send,
  Check,
  AlertCircle,
} from "lucide-react";

export function NotificationChannels() {
  const { data: config, isLoading } = useNotificationChannels();
  const updateMutation = useUpdateNotificationChannels();
  const testSlackMutation = useTestSlackWebhook();

  // Slack state
  const [slackEnabled, setSlackEnabled] = useState(false);
  const [webhookUrl, setWebhookUrl] = useState("");

  // Email state
  const [emailEnabled, setEmailEnabled] = useState(false);
  const [emailRecipients, setEmailRecipients] = useState<string[]>([]);
  const [newEmail, setNewEmail] = useState("");
  const [emailError, setEmailError] = useState("");

  // Initialize state from config
  useEffect(() => {
    if (config) {
      setSlackEnabled(config.slack.enabled);
      setWebhookUrl(config.slack.webhook_url || "");
      setEmailEnabled(config.email.enabled);
      setEmailRecipients(config.email.recipients);
    }
  }, [config]);

  const handleSave = () => {
    updateMutation.mutate({
      slack: {
        enabled: slackEnabled,
        webhook_url: webhookUrl || null,
      },
      email: {
        enabled: emailEnabled,
        recipients: emailRecipients,
      },
    });
  };

  const handleTestSlack = () => {
    if (webhookUrl) {
      testSlackMutation.mutate(webhookUrl);
    }
  };

  const validateEmail = (email: string): boolean => {
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    return emailRegex.test(email);
  };

  const handleAddEmail = () => {
    if (!newEmail.trim()) {
      setEmailError("Email is required");
      return;
    }

    if (!validateEmail(newEmail)) {
      setEmailError("Invalid email format");
      return;
    }

    if (emailRecipients.includes(newEmail.toLowerCase())) {
      setEmailError("Email already added");
      return;
    }

    setEmailRecipients([...emailRecipients, newEmail.toLowerCase()]);
    setNewEmail("");
    setEmailError("");
  };

  const handleRemoveEmail = (email: string) => {
    setEmailRecipients(emailRecipients.filter((e) => e !== email));
  };

  const hasChanges = () => {
    if (!config) return false;
    return (
      slackEnabled !== config.slack.enabled ||
      webhookUrl !== (config.slack.webhook_url || "") ||
      emailEnabled !== config.email.enabled ||
      JSON.stringify(emailRecipients) !== JSON.stringify(config.email.recipients)
    );
  };

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle>Notification Channels</CardTitle>
        <CardDescription>
          Configure how you want to receive alert notifications
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Slack Channel */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#4A154B]">
                <Slack className="h-5 w-5 text-white" />
              </div>
              <div>
                <h3 className="font-medium">Slack</h3>
                <p className="text-sm text-muted-foreground">
                  Send alerts to a Slack channel
                </p>
              </div>
            </div>
            <Switch
              checked={slackEnabled}
              onCheckedChange={setSlackEnabled}
            />
          </div>

          {slackEnabled && (
            <div className="ml-13 space-y-3 pl-[52px]">
              <div className="space-y-2">
                <Label htmlFor="webhook-url">Webhook URL</Label>
                <div className="flex gap-2">
                  <Input
                    id="webhook-url"
                    type="url"
                    placeholder="https://hooks.slack.com/services/..."
                    value={webhookUrl}
                    onChange={(e) => setWebhookUrl(e.target.value)}
                    className="flex-1"
                  />
                  <Button
                    variant="outline"
                    size="default"
                    onClick={handleTestSlack}
                    disabled={!webhookUrl || testSlackMutation.isPending}
                  >
                    {testSlackMutation.isPending ? (
                      <Loader2 className="h-4 w-4 animate-spin" />
                    ) : (
                      <>
                        <Send className="mr-2 h-4 w-4" />
                        Test
                      </>
                    )}
                  </Button>
                </div>
                <p className="text-xs text-muted-foreground">
                  Create an incoming webhook in your Slack workspace settings
                </p>
              </div>
            </div>
          )}
        </div>

        <Separator />

        {/* Email Channel */}
        <div className="space-y-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-blue-600">
                <Mail className="h-5 w-5 text-white" />
              </div>
              <div>
                <h3 className="font-medium">Email</h3>
                <p className="text-sm text-muted-foreground">
                  Send alerts via email
                </p>
              </div>
            </div>
            <Switch
              checked={emailEnabled}
              onCheckedChange={setEmailEnabled}
            />
          </div>

          {emailEnabled && (
            <div className="ml-13 space-y-3 pl-[52px]">
              <div className="space-y-2">
                <Label>Recipients</Label>
                <div className="flex gap-2">
                  <Input
                    type="email"
                    placeholder="email@example.com"
                    value={newEmail}
                    onChange={(e) => {
                      setNewEmail(e.target.value);
                      setEmailError("");
                    }}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        handleAddEmail();
                      }
                    }}
                    className="flex-1"
                  />
                  <Button
                    variant="outline"
                    size="default"
                    onClick={handleAddEmail}
                  >
                    <Plus className="h-4 w-4" />
                  </Button>
                </div>
                {emailError && (
                  <p className="text-xs text-destructive flex items-center gap-1">
                    <AlertCircle className="h-3 w-3" />
                    {emailError}
                  </p>
                )}
              </div>

              {emailRecipients.length > 0 && (
                <div className="flex flex-wrap gap-2">
                  {emailRecipients.map((email) => (
                    <Badge
                      key={email}
                      variant="secondary"
                      className="flex items-center gap-1 py-1"
                    >
                      {email}
                      <button
                        onClick={() => handleRemoveEmail(email)}
                        className="ml-1 hover:text-destructive"
                      >
                        <X className="h-3 w-3" />
                      </button>
                    </Badge>
                  ))}
                </div>
              )}

              {emailRecipients.length === 0 && (
                <p className="text-sm text-muted-foreground">
                  No recipients added yet
                </p>
              )}
            </div>
          )}
        </div>

        <Separator />

        {/* Save Button */}
        <div className="flex justify-end">
          <Button
            onClick={handleSave}
            disabled={!hasChanges() || updateMutation.isPending}
          >
            {updateMutation.isPending ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Saving...
              </>
            ) : (
              <>
                <Check className="mr-2 h-4 w-4" />
                Save Changes
              </>
            )}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
