"use client";

import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { NotificationChannels } from "@/components/alerts/NotificationChannels";
import { AlertRules } from "@/components/alerts/AlertRules";
import { AlertHistory } from "@/components/alerts/AlertHistory";
import { Breadcrumb } from "@/components/ui/breadcrumb";
import { Bell, Settings, History } from "lucide-react";

export default function AlertsSettingsPage() {
  return (
    <div className="space-y-6">
      {/* Breadcrumb */}
      <Breadcrumb
        items={[
          { label: "Settings", href: "/settings" },
          { label: "Alerts" },
        ]}
      />

      <div>
        <h1 className="text-2xl font-bold tracking-tight">Alerts & Notifications</h1>
        <p className="text-muted-foreground">
          Configure how you get notified about pipeline events and issues
        </p>
      </div>

      <Tabs defaultValue="channels" className="space-y-4">
        <TabsList>
          <TabsTrigger value="channels" className="flex items-center gap-2">
            <Bell className="h-4 w-4" />
            Notification Channels
          </TabsTrigger>
          <TabsTrigger value="rules" className="flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Alert Rules
          </TabsTrigger>
          <TabsTrigger value="history" className="flex items-center gap-2">
            <History className="h-4 w-4" />
            Alert History
          </TabsTrigger>
        </TabsList>

        <TabsContent value="channels" className="space-y-4">
          <NotificationChannels />
        </TabsContent>

        <TabsContent value="rules" className="space-y-4">
          <AlertRules />
        </TabsContent>

        <TabsContent value="history" className="space-y-4">
          <AlertHistory />
        </TabsContent>
      </Tabs>
    </div>
  );
}
