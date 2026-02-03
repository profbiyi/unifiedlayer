"use client";

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
  ArrowRight,
  Book,
  Code2,
  Database,
  FileJson,
  Key,
  Plug,
  Terminal,
  Webhook,
} from "lucide-react";

const apiSections = [
  {
    icon: Key,
    title: "Authentication",
    description: "JWT-based authentication with access tokens. Login, register, and manage sessions.",
    endpoints: ["POST /auth/login", "POST /auth/register", "GET /auth/me"],
  },
  {
    icon: Database,
    title: "Pipelines",
    description: "Create, schedule, and manage data pipelines from any source to any destination.",
    endpoints: [
      "GET /pipelines/",
      "POST /pipelines/",
      "POST /pipelines/{id}/run",
      "GET /pipelines/{id}/runs",
    ],
  },
  {
    icon: Plug,
    title: "Connectors",
    description: "List available connectors, their capabilities, and configuration schemas.",
    endpoints: [
      "GET /connectors/",
      "GET /connectors/{name}",
      "GET /connectors/categories",
    ],
  },
  {
    icon: Webhook,
    title: "Billing & Usage",
    description: "Manage subscriptions, check usage limits, and handle Stripe webhooks.",
    endpoints: [
      "GET /billing/plans",
      "GET /billing/subscription",
      "GET /billing/usage",
      "POST /billing/checkout",
    ],
  },
];

const codeExamples = {
  python: `import requests

# Authenticate
resp = requests.post("https://api.yourdomain.com/auth/login", data={
    "username": "your@email.com",
    "password": "your_password",
})
token = resp.json()["access_token"]
headers = {"Authorization": f"Bearer {token}"}

# List pipelines
pipelines = requests.get(
    "https://api.yourdomain.com/pipelines/",
    headers=headers,
).json()

# Trigger a pipeline run
run = requests.post(
    f"https://api.yourdomain.com/pipelines/{pipelines[0]['public_id']}/run",
    headers=headers,
).json()

print(f"Pipeline run started: {run['public_id']}")`,

  javascript: `const API_URL = "https://api.yourdomain.com";

// Authenticate
const loginResp = await fetch(\`\${API_URL}/auth/login\`, {
  method: "POST",
  headers: { "Content-Type": "application/x-www-form-urlencoded" },
  body: new URLSearchParams({
    username: "your@email.com",
    password: "your_password",
  }),
});
const { access_token } = await loginResp.json();

// List pipelines
const pipelines = await fetch(\`\${API_URL}/pipelines/\`, {
  headers: { Authorization: \`Bearer \${access_token}\` },
}).then(r => r.json());

// Trigger a pipeline run
const run = await fetch(
  \`\${API_URL}/pipelines/\${pipelines[0].public_id}/run\`,
  {
    method: "POST",
    headers: { Authorization: \`Bearer \${access_token}\` },
  }
).then(r => r.json());

console.log("Pipeline run started:", run.public_id);`,

  curl: `# Authenticate
TOKEN=$(curl -s -X POST https://api.yourdomain.com/auth/login \\
  -d "username=your@email.com&password=your_password" | jq -r '.access_token')

# List pipelines
curl -s https://api.yourdomain.com/pipelines/ \\
  -H "Authorization: Bearer $TOKEN" | jq

# Check usage
curl -s https://api.yourdomain.com/billing/usage \\
  -H "Authorization: Bearer $TOKEN" | jq

# List available connectors
curl -s https://api.yourdomain.com/connectors/ | jq`,
};

export default function DevelopersPage() {
  return (
    <div className="flex min-h-screen flex-col">
      {/* Navigation */}
      <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur">
        <div className="container flex h-16 items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-6 w-6 text-primary" />
            <Link href="/" className="text-xl font-bold">
              UnifiedLayer
            </Link>
          </div>
          <nav className="flex items-center gap-4">
            <Link href="/developers" className="text-sm font-medium text-primary">
              Developers
            </Link>
            <Link href="/login">
              <Button variant="ghost">Sign In</Button>
            </Link>
            <Link href="/login">
              <Button>Get Started</Button>
            </Link>
          </nav>
        </div>
      </header>

      {/* Hero */}
      <section className="border-b bg-gradient-to-b from-primary/5 to-background py-16">
        <div className="container">
          <div className="mx-auto max-w-3xl text-center">
            <Badge variant="secondary" className="mb-4">
              <Code2 className="mr-1 h-3 w-3" />
              Developer Portal
            </Badge>
            <h1 className="mb-4 text-4xl font-bold tracking-tight sm:text-5xl">
              Build with the UnifiedLayer API
            </h1>
            <p className="mb-8 text-lg text-muted-foreground">
              Full REST API access to pipelines, connectors, billing, and more.
              Build custom integrations or extend the platform with the Connector SDK.
            </p>
            <div className="flex flex-col gap-3 sm:flex-row sm:justify-center">
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || ""}/docs`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button size="lg">
                  <FileJson className="mr-2 h-4 w-4" />
                  Interactive API Docs (Swagger)
                </Button>
              </a>
              <a
                href={`${process.env.NEXT_PUBLIC_API_URL || ""}/redoc`}
                target="_blank"
                rel="noopener noreferrer"
              >
                <Button size="lg" variant="outline">
                  <Book className="mr-2 h-4 w-4" />
                  API Reference (ReDoc)
                </Button>
              </a>
            </div>
          </div>
        </div>
      </section>

      {/* API Sections */}
      <section className="py-16">
        <div className="container">
          <h2 className="mb-8 text-2xl font-bold">API Overview</h2>
          <div className="grid gap-6 md:grid-cols-2">
            {apiSections.map((section) => {
              const Icon = section.icon;
              return (
                <Card key={section.title}>
                  <CardHeader>
                    <div className="flex items-center gap-3">
                      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                        <Icon className="h-5 w-5 text-primary" />
                      </div>
                      <CardTitle className="text-lg">{section.title}</CardTitle>
                    </div>
                    <CardDescription>{section.description}</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      {section.endpoints.map((endpoint) => (
                        <code
                          key={endpoint}
                          className="block rounded bg-muted px-3 py-1.5 text-sm font-mono"
                        >
                          {endpoint}
                        </code>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </section>

      {/* Code Examples */}
      <section className="border-t bg-muted/30 py-16">
        <div className="container">
          <h2 className="mb-8 text-2xl font-bold">Quick Start</h2>
          <div className="grid gap-6 lg:grid-cols-3">
            {Object.entries(codeExamples).map(([lang, code]) => (
              <Card key={lang}>
                <CardHeader className="pb-3">
                  <div className="flex items-center gap-2">
                    <Terminal className="h-4 w-4 text-muted-foreground" />
                    <CardTitle className="text-sm font-medium uppercase tracking-wider">
                      {lang}
                    </CardTitle>
                  </div>
                </CardHeader>
                <CardContent>
                  <pre className="overflow-x-auto rounded-lg bg-zinc-950 p-4 text-xs text-zinc-100">
                    <code>{code}</code>
                  </pre>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </section>

      {/* Connector SDK */}
      <section className="border-t py-16">
        <div className="container">
          <div className="mx-auto max-w-2xl text-center">
            <Plug className="mx-auto mb-4 h-12 w-12 text-primary" />
            <h2 className="mb-4 text-2xl font-bold">Connector SDK</h2>
            <p className="mb-6 text-muted-foreground">
              Build custom data source connectors with our Python SDK.
              Your connector automatically gets schema discovery, incremental loading,
              and integration with the platform&apos;s pipeline engine.
            </p>
            <pre className="mb-6 overflow-x-auto rounded-lg bg-zinc-950 p-4 text-left text-xs text-zinc-100">
              <code>{`from backend.connectors.sdk import BaseConnector, register_connector

@register_connector
class MyConnector(BaseConnector):
    metadata = ConnectorMetadata(
        name="my_source",
        display_name="My Data Source",
        category="api",
    )

    def extract(self, tables=None, **kwargs):
        yield {"id": 1, "name": "Alice"}
        yield {"id": 2, "name": "Bob"}`}</code>
            </pre>
            <a
              href={`${process.env.NEXT_PUBLIC_API_URL || ""}/connectors/`}
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button>
                View Available Connectors
                <ArrowRight className="ml-2 h-4 w-4" />
              </Button>
            </a>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8">
        <div className="container flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Database className="h-5 w-5 text-primary" />
            <span className="font-semibold">UnifiedLayer</span>
          </div>
          <p className="text-sm text-muted-foreground">
            &copy; 2026 UnifiedLayer. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
