"use client";

import { useState } from "react";
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import {
  Check,
  Crown,
  Users,
  Workflow,
  Mail,
  Shield,
  Zap,
  TrendingUp,
} from "lucide-react";
import { useToast } from "@/hooks/use-toast";
import CurrencySelector from "@/components/CurrencySelector";
import { formatPrice } from "@/lib/currency";

// This would come from your backend/API in production
const PLAN_FEATURES = {
  starter: [
    "Up to 3 team members",
    "Unlimited pipelines",
    "Basic data sources & destinations",
    "Email support",
    "Data lineage tracking",
    "Pipeline scheduling",
  ],
  professional: [
    "Up to 5 team members",
    "Everything in Starter",
    "Advanced data sources",
    "Priority support",
    "Advanced monitoring & alerts",
    "Custom integrations",
    "Audit logs & compliance",
  ],
  enterprise: [
    "Unlimited team members",
    "Everything in Professional",
    "Dedicated support",
    "Custom SLA",
    "SSO & advanced security",
    "Custom deployment options",
    "Training & onboarding",
  ],
};

export default function BillingPage() {
  const { toast } = useToast();
  const [contactingRequested, setContactingRequested] = useState(false);
  const [currency, setCurrency] = useState("USD");

  // In production, fetch this from your API
  const currentPlan = "professional" as "starter" | "professional" | "enterprise";
  const currentUsers = 3;
  const maxUsers = 5;
  const currentPipelines = 12;

  const handleContactSales = () => {
    setContactingRequested(true);
    toast({
      title: "Request Received",
      description: "Our sales team will contact you within 24 hours.",
    });
  };

  const handleUpgrade = (plan: string) => {
    toast({
      title: "Upgrade Request",
      description: `Request to upgrade to ${plan} plan received. Our team will contact you.`,
    });
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold tracking-tight">Billing & Subscription</h1>
        <p className="text-muted-foreground">
          Manage your subscription plan and billing details
        </p>
      </div>

      {/* Currency Selector */}
      <div className="flex items-center justify-end gap-3">
        <span className="text-sm text-muted-foreground">Display prices in:</span>
        <CurrencySelector onChange={setCurrency} />
      </div>

      {/* Current Plan Overview */}
      <Card className="border-primary">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-2xl">Current Plan</CardTitle>
              <CardDescription>Your active subscription</CardDescription>
            </div>
            <Badge variant="default" className="gap-1">
              <Crown className="h-3 w-3" />
              {currentPlan.charAt(0).toUpperCase() + currentPlan.slice(1)}
            </Badge>
          </div>
        </CardHeader>
        <CardContent className="space-y-6">
          {/* Usage Stats */}
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  <Users className="h-4 w-4 text-muted-foreground" />
                  Team Members
                </span>
                <span className="font-medium">
                  {currentUsers} / {maxUsers}
                </span>
              </div>
              <Progress value={(currentUsers / maxUsers) * 100} />
            </div>

            <div className="space-y-2">
              <div className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2">
                  <Workflow className="h-4 w-4 text-muted-foreground" />
                  Active Pipelines
                </span>
                <span className="font-medium">{currentPipelines}</span>
              </div>
              <Progress value={50} className="bg-secondary" />
              <p className="text-xs text-muted-foreground">Unlimited pipelines</p>
            </div>
          </div>

          {/* Plan Features */}
          <div>
            <h3 className="font-semibold mb-3">Plan Features</h3>
            <div className="grid gap-2">
              {PLAN_FEATURES[currentPlan as keyof typeof PLAN_FEATURES].map((feature) => (
                <div key={feature} className="flex items-center gap-2 text-sm">
                  <Check className="h-4 w-4 text-green-600 shrink-0" />
                  <span>{feature}</span>
                </div>
              ))}
            </div>
          </div>
        </CardContent>
        <CardFooter>
          <Button
            variant="outline"
            className="w-full"
            onClick={handleContactSales}
            disabled={contactingRequested}
          >
            <Mail className="mr-2 h-4 w-4" />
            {contactingRequested ? "Request Sent" : "Contact Sales for Custom Plan"}
          </Button>
        </CardFooter>
      </Card>

      {/* Available Plans */}
      <div>
        <h2 className="text-2xl font-bold mb-4">Explore Other Plans</h2>
        <div className="grid gap-6 md:grid-cols-3">
          {/* Starter Plan */}
          <Card className={currentPlan === "starter" ? "border-primary" : ""}>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Starter
                {currentPlan === "starter" && <Badge>Current</Badge>}
              </CardTitle>
              <CardDescription>Perfect for small teams getting started</CardDescription>
              <div className="mt-2">
                <span className="text-2xl font-bold">$0</span>
                <span className="text-muted-foreground text-sm">/month</span>
                {currency !== "USD" && (
                  <p className="text-xs text-muted-foreground">{formatPrice(0, currency)}/month</p>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                {PLAN_FEATURES.starter.slice(0, 4).map((feature) => (
                  <div key={feature} className="flex items-center gap-2 text-sm">
                    <Check className="h-4 w-4 text-green-600 shrink-0" />
                    <span>{feature}</span>
                  </div>
                ))}
                {PLAN_FEATURES.starter.length > 4 && (
                  <p className="text-xs text-muted-foreground">
                    +{PLAN_FEATURES.starter.length - 4} more features
                  </p>
                )}
              </div>
            </CardContent>
            <CardFooter>
              {currentPlan === "starter" ? (
                <Button className="w-full" disabled>
                  Current Plan
                </Button>
              ) : (
                <Button
                  variant="outline"
                  className="w-full"
                  onClick={() => handleUpgrade("Starter")}
                >
                  Contact Sales
                </Button>
              )}
            </CardFooter>
          </Card>

          {/* Professional Plan */}
          <Card className={currentPlan === "professional" ? "border-primary shadow-lg scale-105" : "border-2"}>
            <CardHeader>
              <div className="absolute -top-4 left-0 right-0 mx-auto w-fit">
                <Badge className="bg-primary">Recommended</Badge>
              </div>
              <CardTitle className="flex items-center justify-between pt-2">
                Professional
                {currentPlan === "professional" && <Badge>Current</Badge>}
              </CardTitle>
              <CardDescription>For growing teams that need more power</CardDescription>
              <div className="mt-2">
                <span className="text-2xl font-bold">$49</span>
                <span className="text-muted-foreground text-sm">/month</span>
                {currency !== "USD" && (
                  <p className="text-xs text-muted-foreground">{formatPrice(49, currency)}/month</p>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                {PLAN_FEATURES.professional.slice(0, 5).map((feature) => (
                  <div key={feature} className="flex items-center gap-2 text-sm">
                    <Check className="h-4 w-4 text-green-600 shrink-0" />
                    <span>{feature}</span>
                  </div>
                ))}
                {PLAN_FEATURES.professional.length > 5 && (
                  <p className="text-xs text-muted-foreground">
                    +{PLAN_FEATURES.professional.length - 5} more features
                  </p>
                )}
              </div>
            </CardContent>
            <CardFooter>
              {currentPlan === "professional" ? (
                <Button className="w-full" disabled>
                  Current Plan
                </Button>
              ) : (
                <Button className="w-full" onClick={() => handleUpgrade("Professional")}>
                  Upgrade Now
                </Button>
              )}
            </CardFooter>
          </Card>

          {/* Enterprise Plan */}
          <Card className={currentPlan === "enterprise" ? "border-primary" : ""}>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Enterprise
                {currentPlan === "enterprise" && <Badge>Current</Badge>}
              </CardTitle>
              <CardDescription>For large organizations with complex needs</CardDescription>
              <div className="mt-2">
                <span className="text-2xl font-bold">$199</span>
                <span className="text-muted-foreground text-sm">/month</span>
                {currency !== "USD" && (
                  <p className="text-xs text-muted-foreground">{formatPrice(199, currency)}/month</p>
                )}
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                {PLAN_FEATURES.enterprise.slice(0, 4).map((feature) => (
                  <div key={feature} className="flex items-center gap-2 text-sm">
                    <Check className="h-4 w-4 text-green-600 shrink-0" />
                    <span>{feature}</span>
                  </div>
                ))}
                {PLAN_FEATURES.enterprise.length > 4 && (
                  <p className="text-xs text-muted-foreground">
                    +{PLAN_FEATURES.enterprise.length - 4} more features
                  </p>
                )}
              </div>
            </CardContent>
            <CardFooter>
              {currentPlan === "enterprise" ? (
                <Button className="w-full" disabled>
                  Current Plan
                </Button>
              ) : (
                <Button className="w-full" onClick={() => handleUpgrade("Enterprise")}>
                  Contact Sales
                </Button>
              )}
            </CardFooter>
          </Card>
        </div>
      </div>

      {/* Benefits Section */}
      <Card>
        <CardHeader>
          <CardTitle>Why Upgrade?</CardTitle>
          <CardDescription>Unlock more features and capabilities</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 md:grid-cols-3">
            <div className="flex gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 shrink-0">
                <Shield className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h4 className="font-semibold text-sm">Enhanced Security</h4>
                <p className="text-xs text-muted-foreground">
                  Advanced security features and compliance tools
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 shrink-0">
                <Zap className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h4 className="font-semibold text-sm">Priority Support</h4>
                <p className="text-xs text-muted-foreground">
                  Get help when you need it with dedicated support
                </p>
              </div>
            </div>

            <div className="flex gap-3">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 shrink-0">
                <TrendingUp className="h-5 w-5 text-primary" />
              </div>
              <div>
                <h4 className="font-semibold text-sm">Scale with Confidence</h4>
                <p className="text-xs text-muted-foreground">
                  Grow your team and pipelines without limitations
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
