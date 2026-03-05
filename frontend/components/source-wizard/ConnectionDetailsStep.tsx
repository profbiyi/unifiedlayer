"use client";

import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { SourceWizardData } from "@/app/(dashboard)/sources/new/page";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Info, ExternalLink } from "lucide-react";
import HttpFileForm from "@/components/source-wizard/forms/HttpFileForm";
import RestApiDeclarativeForm from "@/components/source-wizard/forms/RestApiDeclarativeForm";

interface ConnectionDetailsStepProps {
  data: SourceWizardData;
  onUpdate: (updates: Partial<SourceWizardData>) => void;
}

export default function ConnectionDetailsStep({
  data,
  onUpdate,
}: ConnectionDetailsStepProps) {
  const updateConfig = (key: string, value: unknown) => {
    onUpdate({
      config: {
        ...data.config,
        [key]: value,
      },
    });
  };

  const renderPostgreSQLForm = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="host">
            Host <span className="text-destructive">*</span>
          </Label>
          <Input
            id="host"
            placeholder="localhost"
            value={data.config.host || ""}
            onChange={(e) => updateConfig("host", e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="port">
            Port <span className="text-destructive">*</span>
          </Label>
          <Input
            id="port"
            type="number"
            placeholder="5432"
            value={data.config.port || ""}
            onChange={(e) => updateConfig("port", parseInt(e.target.value))}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="database">
          Database <span className="text-destructive">*</span>
        </Label>
        <Input
          id="database"
          placeholder="mydatabase"
          value={data.config.database || ""}
          onChange={(e) => updateConfig("database", e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="username">
          Username <span className="text-destructive">*</span>
        </Label>
        <Input
          id="username"
          placeholder="postgres"
          value={data.config.username || ""}
          onChange={(e) => updateConfig("username", e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">
          Password <span className="text-destructive">*</span>
        </Label>
        <Input
          id="password"
          type="password"
          placeholder="••••••••"
          value={data.config.password || ""}
          onChange={(e) => updateConfig("password", e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="schema">Schema (optional)</Label>
        <Input
          id="schema"
          placeholder="public"
          value={data.config.schema || ""}
          onChange={(e) => updateConfig("schema", e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="sslmode">SSL Mode</Label>
        <Select
          value={data.config.sslmode || "prefer"}
          onValueChange={(value) => updateConfig("sslmode", value)}
        >
          <SelectTrigger id="sslmode">
            <SelectValue placeholder="Select SSL mode" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="disable">Disable (no SSL)</SelectItem>
            <SelectItem value="prefer">Prefer (SSL if available)</SelectItem>
            <SelectItem value="require">Require (SSL required)</SelectItem>
            <SelectItem value="verify-ca">Verify CA</SelectItem>
            <SelectItem value="verify-full">Verify Full</SelectItem>
          </SelectContent>
        </Select>
        <p className="text-xs text-muted-foreground">
          Use &quot;require&quot; for cloud providers like Neon, AWS RDS, or DigitalOcean
        </p>
      </div>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Make sure your PostgreSQL server allows connections from this application.
          You may need to configure pg_hba.conf and postgresql.conf.
        </AlertDescription>
      </Alert>
    </div>
  );

  const renderMySQLForm = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-2">
          <Label htmlFor="host">
            Host <span className="text-destructive">*</span>
          </Label>
          <Input
            id="host"
            placeholder="localhost"
            value={data.config.host || ""}
            onChange={(e) => updateConfig("host", e.target.value)}
          />
        </div>
        <div className="space-y-2">
          <Label htmlFor="port">
            Port <span className="text-destructive">*</span>
          </Label>
          <Input
            id="port"
            type="number"
            placeholder="3306"
            value={data.config.port || ""}
            onChange={(e) => updateConfig("port", parseInt(e.target.value))}
          />
        </div>
      </div>

      <div className="space-y-2">
        <Label htmlFor="database">
          Database <span className="text-destructive">*</span>
        </Label>
        <Input
          id="database"
          placeholder="mydatabase"
          value={data.config.database || ""}
          onChange={(e) => updateConfig("database", e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="username">
          Username <span className="text-destructive">*</span>
        </Label>
        <Input
          id="username"
          placeholder="root"
          value={data.config.username || ""}
          onChange={(e) => updateConfig("username", e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="password">
          Password <span className="text-destructive">*</span>
        </Label>
        <Input
          id="password"
          type="password"
          placeholder="••••••••"
          value={data.config.password || ""}
          onChange={(e) => updateConfig("password", e.target.value)}
        />
      </div>
    </div>
  );

  const renderMongoDBForm = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="connection_string">
          Connection String <span className="text-destructive">*</span>
        </Label>
        <Textarea
          id="connection_string"
          placeholder="mongodb://username:password@host:port/database"
          value={data.config.connection_string || ""}
          onChange={(e) => updateConfig("connection_string", e.target.value)}
          rows={3}
        />
        <p className="text-xs text-muted-foreground">
          Full MongoDB connection string including authentication
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="database">
          Database <span className="text-destructive">*</span>
        </Label>
        <Input
          id="database"
          placeholder="mydatabase"
          value={data.config.database || ""}
          onChange={(e) => updateConfig("database", e.target.value)}
        />
      </div>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          MongoDB connection strings can include replica set configuration and SSL options.
        </AlertDescription>
      </Alert>
    </div>
  );

  const renderRESTAPIForm = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="url">
          API URL <span className="text-destructive">*</span>
        </Label>
        <Input
          id="url"
          placeholder="https://rickandmortyapi.com/api/character"
          value={data.config.url || ""}
          onChange={(e) => updateConfig("url", e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          Full URL to the API endpoint that returns JSON data
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="auth_type">Authentication Type</Label>
        <select
          id="auth_type"
          className="flex h-10 w-full rounded-md border border-input bg-background px-3 py-2 text-sm"
          value={data.config.auth_type || "none"}
          onChange={(e) => updateConfig("auth_type", e.target.value)}
        >
          <option value="none">None</option>
          <option value="api_key">API Key</option>
          <option value="bearer">Bearer Token</option>
          <option value="basic">Basic Auth</option>
        </select>
      </div>

      {data.config.auth_type === "api_key" && (
        <>
          <div className="space-y-2">
            <Label htmlFor="auth_key_value">API Key</Label>
            <Input
              id="auth_key_value"
              type="password"
              placeholder="••••••••"
              value={data.config.auth_key_value || ""}
              onChange={(e) => updateConfig("auth_key_value", e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="auth_key_name">API Key Header Name</Label>
            <Input
              id="auth_key_name"
              placeholder="X-API-Key"
              value={data.config.auth_key_name || "X-API-Key"}
              onChange={(e) => updateConfig("auth_key_name", e.target.value)}
            />
          </div>
        </>
      )}

      {data.config.auth_type === "bearer" && (
        <div className="space-y-2">
          <Label htmlFor="auth_token">Bearer Token</Label>
          <Input
            id="auth_token"
            type="password"
            placeholder="••••••••"
            value={data.config.auth_token || ""}
            onChange={(e) => updateConfig("auth_token", e.target.value)}
          />
        </div>
      )}

      {data.config.auth_type === "basic" && (
        <>
          <div className="space-y-2">
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              value={data.config.username || ""}
              onChange={(e) => updateConfig("username", e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              placeholder="••••••••"
              value={data.config.password || ""}
              onChange={(e) => updateConfig("password", e.target.value)}
            />
          </div>
        </>
      )}
    </div>
  );

  const renderCSVForm = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="file_path">
          File Path <span className="text-destructive">*</span>
        </Label>
        <Input
          id="file_path"
          placeholder="/path/to/file.csv"
          value={data.config.file_path || ""}
          onChange={(e) => updateConfig("file_path", e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="delimiter">Delimiter</Label>
        <Input
          id="delimiter"
          placeholder=","
          value={data.config.delimiter || ","}
          onChange={(e) => updateConfig("delimiter", e.target.value)}
          maxLength={1}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="encoding">Encoding</Label>
        <Input
          id="encoding"
          placeholder="utf-8"
          value={data.config.encoding || "utf-8"}
          onChange={(e) => updateConfig("encoding", e.target.value)}
        />
      </div>

      <div className="flex items-center space-x-2">
        <input
          type="checkbox"
          id="has_header"
          checked={data.config.has_header !== false}
          onChange={(e) => updateConfig("has_header", e.target.checked)}
          className="h-4 w-4"
        />
        <Label htmlFor="has_header" className="font-normal">
          First row contains headers
        </Label>
      </div>
    </div>
  );

  const renderLocalForm = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="directory_path">
          Directory Path <span className="text-destructive">*</span>
        </Label>
        <Input
          id="directory_path"
          placeholder="/path/to/data"
          value={data.config.directory_path || ""}
          onChange={(e) => updateConfig("directory_path", e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="file_pattern">File Pattern (optional)</Label>
        <Input
          id="file_pattern"
          placeholder="*.json"
          value={data.config.file_pattern || ""}
          onChange={(e) => updateConfig("file_pattern", e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          Glob pattern to match files (e.g., *.json, data_*.csv)
        </p>
      </div>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          The application must have read permissions for the specified directory.
        </AlertDescription>
      </Alert>
    </div>
  );

  const renderStripeForm = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="api_key">
          Secret Key <span className="text-destructive">*</span>
        </Label>
        <Input
          id="api_key"
          type="password"
          placeholder="sk_live_..."
          value={data.config.api_key || ""}
          onChange={(e) => updateConfig("api_key", e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          Your Stripe secret key. Use sk_test_... for testing.
        </p>
      </div>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Find your API keys in the Stripe Dashboard under Developers &gt; API keys.
          We&apos;ll sync customers, charges, invoices, subscriptions, and more.
        </AlertDescription>
      </Alert>
    </div>
  );

  const renderPaystackForm = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="secret_key">
          Secret Key <span className="text-destructive">*</span>
        </Label>
        <Input
          id="secret_key"
          type="password"
          placeholder="sk_live_..."
          value={data.config.secret_key || ""}
          onChange={(e) => updateConfig("secret_key", e.target.value)}
        />
      </div>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Find your secret key in the Paystack Dashboard under Settings &gt; API Keys &amp; Webhooks.
          Use a test key (sk_test_...) for testing.
        </AlertDescription>
      </Alert>
    </div>
  );

  const renderGoogleSheetsForm = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="credentials_json">
          Service Account JSON <span className="text-destructive">*</span>
        </Label>
        <Textarea
          id="credentials_json"
          placeholder='{"type": "service_account", "project_id": "...", ...}'
          value={data.config.credentials_json || ""}
          onChange={(e) => updateConfig("credentials_json", e.target.value)}
          rows={6}
        />
        <p className="text-xs text-muted-foreground">
          Paste the full JSON contents of your Google service account key file
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="spreadsheet_id">
          Spreadsheet ID <span className="text-destructive">*</span>
        </Label>
        <Input
          id="spreadsheet_id"
          placeholder="1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgVE2upms"
          value={data.config.spreadsheet_id || ""}
          onChange={(e) => updateConfig("spreadsheet_id", e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          The ID from your Google Sheets URL: docs.google.com/spreadsheets/d/<strong>SPREADSHEET_ID</strong>/edit
        </p>
      </div>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Share the spreadsheet with the service account email address
          (found in the JSON under &quot;client_email&quot;) with at least Viewer access.
        </AlertDescription>
      </Alert>
    </div>
  );

  const GOCARDLESS_TABLES = [
    "payments",
    "mandates",
    "customers",
    "payouts",
    "refunds",
    "subscriptions",
    "events",
  ];

  const renderGoCardlessForm = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="access_token">
          Access Token <span className="text-destructive">*</span>
        </Label>
        <Input
          id="access_token"
          type="password"
          placeholder="live_..."
          value={data.config.access_token || ""}
          onChange={(e) => updateConfig("access_token", e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          Find your access token in the GoCardless Dashboard under Developers &gt; API Keys.
        </p>
      </div>

      <div className="space-y-2">
        <Label htmlFor="environment">Environment</Label>
        <Select
          value={data.config.environment || "live"}
          onValueChange={(value) => updateConfig("environment", value)}
        >
          <SelectTrigger id="environment">
            <SelectValue placeholder="Select environment" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="live">Live</SelectItem>
            <SelectItem value="sandbox">Sandbox</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="space-y-2">
        <Label>Tables to Sync</Label>
        <div className="grid grid-cols-2 gap-2">
          {GOCARDLESS_TABLES.map((table) => {
            const selected: string[] = data.config.tables || [];
            const isChecked = selected.includes(table);
            return (
              <div key={table} className="flex items-center space-x-2">
                <input
                  type="checkbox"
                  id={`gc-table-${table}`}
                  checked={isChecked}
                  onChange={(e) => {
                    const newTables = e.target.checked
                      ? [...selected, table]
                      : selected.filter((t: string) => t !== table);
                    updateConfig("tables", newTables);
                  }}
                  className="h-4 w-4"
                />
                <Label htmlFor={`gc-table-${table}`} className="font-normal capitalize">
                  {table}
                </Label>
              </div>
            );
          })}
        </div>
      </div>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Use a sandbox access token for testing. Switch to live when ready for production.
        </AlertDescription>
      </Alert>
    </div>
  );

  const renderOAuthButton = (label: string, redirectUrl: string, description: string) => (
    <div className="space-y-4">
      <div className="flex flex-col items-center gap-4 py-8">
        <p className="text-sm text-muted-foreground text-center max-w-md">
          {description}
        </p>
        <Button
          type="button"
          size="lg"
          onClick={() => {
            // Mark config as oauth-based so canProceed passes
            updateConfig("oauth", true);
            window.location.href = redirectUrl;
          }}
        >
          <ExternalLink className="mr-2 h-4 w-4" />
          {label}
        </Button>
      </div>
      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          You will be redirected to authorise access. Once complete, you will be returned here automatically.
        </AlertDescription>
      </Alert>
    </div>
  );

  const renderXeroForm = () =>
    renderOAuthButton(
      "Connect with Xero",
      "/oauth/xero/authorize",
      "Connect your Xero account to sync invoices, contacts, bank transactions and more."
    );

  const renderOpenBankingForm = () =>
    renderOAuthButton(
      "Connect your Bank",
      "/oauth/truelayer/authorize",
      "Securely connect your UK bank account via Open Banking to sync transactions and balances."
    );

  const renderHMRCForm = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="vrn">
          VAT Registration Number <span className="text-destructive">*</span>
        </Label>
        <Input
          id="vrn"
          placeholder="123456789"
          value={data.config.vrn || ""}
          onChange={(e) => updateConfig("vrn", e.target.value)}
        />
        <p className="text-xs text-muted-foreground">
          Your 9-digit VAT Registration Number used for Making Tax Digital submissions.
        </p>
      </div>

      <div className="flex flex-col items-center gap-4 py-4">
        <p className="text-sm text-muted-foreground text-center max-w-md">
          Authorise access to your HMRC Making Tax Digital account to sync VAT obligations and returns.
        </p>
        <Button
          type="button"
          size="lg"
          onClick={() => {
            updateConfig("oauth", true);
            window.location.href = "/oauth/hmrc/authorize";
          }}
        >
          <ExternalLink className="mr-2 h-4 w-4" />
          Connect HMRC
        </Button>
      </div>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          You will be redirected to HMRC to authorise access. Make sure your VRN is entered before connecting.
        </AlertDescription>
      </Alert>
    </div>
  );

  const renderFlutterwaveForm = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="secret_key">Secret Key</Label>
        <Input
          id="secret_key"
          type="password"
          placeholder="FLWSECK_TEST-..."
          value={data.config.secret_key || ""}
          onChange={(e) => updateConfig("secret_key", e.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="environment">Environment</Label>
        <Select value={data.config.environment || "sandbox"} onValueChange={(v) => updateConfig("environment", v)}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="sandbox">Sandbox</SelectItem>
            <SelectItem value="production">Production</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );

  const renderMTNMoMoForm = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="subscription_key">Subscription Key</Label>
        <Input
          id="subscription_key"
          type="password"
          placeholder="Ocp-Apim-Subscription-Key"
          value={data.config.subscription_key || ""}
          onChange={(e) => updateConfig("subscription_key", e.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="api_user">API User</Label>
        <Input
          id="api_user"
          placeholder="X-Reference-Id"
          value={data.config.api_user || ""}
          onChange={(e) => updateConfig("api_user", e.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="api_key">API Key</Label>
        <Input
          id="api_key"
          type="password"
          value={data.config.api_key || ""}
          onChange={(e) => updateConfig("api_key", e.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="environment">Environment</Label>
        <Select value={data.config.environment || "sandbox"} onValueChange={(v) => updateConfig("environment", v)}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="sandbox">Sandbox</SelectItem>
            <SelectItem value="production">Production</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );

  const renderMPesaForm = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="consumer_key">Consumer Key</Label>
        <Input
          id="consumer_key"
          type="password"
          value={data.config.consumer_key || ""}
          onChange={(e) => updateConfig("consumer_key", e.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="consumer_secret">Consumer Secret</Label>
        <Input
          id="consumer_secret"
          type="password"
          value={data.config.consumer_secret || ""}
          onChange={(e) => updateConfig("consumer_secret", e.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="shortcode">Business Shortcode</Label>
        <Input
          id="shortcode"
          value={data.config.shortcode || ""}
          onChange={(e) => updateConfig("shortcode", e.target.value)}
        />
      </div>
      <div className="space-y-2">
        <Label htmlFor="environment">Environment</Label>
        <Select value={data.config.environment || "sandbox"} onValueChange={(v) => updateConfig("environment", v)}>
          <SelectTrigger><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="sandbox">Sandbox</SelectItem>
            <SelectItem value="production">Production</SelectItem>
          </SelectContent>
        </Select>
      </div>
    </div>
  );

  const renderWhatsAppForm = () => (
    <div className="space-y-4">
      <div className="space-y-2">
        <Label htmlFor="access_token">
          Access Token <span className="text-destructive">*</span>
        </Label>
        <Input
          id="access_token"
          type="password"
          placeholder="••••••••"
          value={data.config.access_token || ""}
          onChange={(e) => updateConfig("access_token", e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="phone_number_id">
          Phone Number ID <span className="text-destructive">*</span>
        </Label>
        <Input
          id="phone_number_id"
          placeholder="123456789012345"
          value={data.config.phone_number_id || ""}
          onChange={(e) => updateConfig("phone_number_id", e.target.value)}
        />
      </div>

      <div className="space-y-2">
        <Label htmlFor="business_account_id">
          Business Account ID <span className="text-destructive">*</span>
        </Label>
        <Input
          id="business_account_id"
          placeholder="123456789012345"
          value={data.config.business_account_id || ""}
          onChange={(e) => updateConfig("business_account_id", e.target.value)}
        />
      </div>

      <Alert>
        <Info className="h-4 w-4" />
        <AlertDescription>
          Find your access token, phone number ID, and business account ID in the
          Meta Developer Portal under your WhatsApp Business app settings.
        </AlertDescription>
      </Alert>
    </div>
  );

  const renderForm = () => {
    switch (data.source_type) {
      case "stripe":
        return renderStripeForm();
      case "paystack":
        return renderPaystackForm();
      case "postgresql":
        return renderPostgreSQLForm();
      case "mysql":
        return renderMySQLForm();
      case "mongodb":
        return renderMongoDBForm();
      case "google_sheets":
        return renderGoogleSheetsForm();
      case "rest_api":
        return renderRESTAPIForm();
      case "csv":
        return renderCSVForm();
      case "local":
        return renderLocalForm();
      case "gocardless":
        return renderGoCardlessForm();
      case "xero":
        return renderXeroForm();
      case "open_banking":
        return renderOpenBankingForm();
      case "hmrc_mtd":
        return renderHMRCForm();
      case "flutterwave":
        return renderFlutterwaveForm();
      case "mtn_momo":
        return renderMTNMoMoForm();
      case "mpesa":
        return renderMPesaForm();
      case "whatsapp":
        return renderWhatsAppForm();
      case "http_file":
        return <HttpFileForm data={data} onUpdate={onUpdate} />;
      case "rest_api_declarative":
        return <RestApiDeclarativeForm data={data} onUpdate={onUpdate} />;
      default:
        return (
          <Alert>
            <Info className="h-4 w-4" />
            <AlertDescription>
              Please select a source type from the previous step.
            </AlertDescription>
          </Alert>
        );
    }
  };

  return <div className="space-y-6">{renderForm()}</div>;
}
