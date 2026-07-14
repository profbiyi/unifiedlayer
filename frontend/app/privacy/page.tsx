import Link from "next/link";

export default function PrivacyPolicyPage() {
  return (
    <div className="force-light min-h-screen bg-background text-foreground">
      <div className="mx-auto max-w-3xl px-6 py-16">
        <Link
          href="/"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          &larr; Back to home
        </Link>

        <article className="prose prose-neutral dark:prose-invert mt-8 max-w-none">
          <h1>Privacy Policy</h1>
          <p className="lead">
            Last updated: {new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}
          </p>

          <p>
            UnifiedLayer (&quot;we&quot;, &quot;us&quot;, &quot;our&quot;) is committed to protecting your
            privacy. This policy explains what personal data we collect, how we use it, how long we
            keep it, and what rights you have.
          </p>

          <h2>1. What We Collect</h2>
          <ul>
            <li>
              <strong>Account information</strong> &mdash; email address, username, full name, and
              hashed password.
            </li>
            <li>
              <strong>Organisation data</strong> &mdash; organisation name, billing email, and
              subscription details.
            </li>
            <li>
              <strong>Usage data</strong> &mdash; pipeline configurations, run history, data source
              and destination metadata, API request logs, and login timestamps.
            </li>
            <li>
              <strong>Technical data</strong> &mdash; IP address, browser type, and device
              information collected automatically via server logs.
            </li>
            <li>
              <strong>Billing data</strong> &mdash; billing email and subscription plan. Payment
              card details are processed exclusively by Stripe and are never stored on our servers.
            </li>
          </ul>

          <h2>2. How We Use It</h2>
          <ul>
            <li>To provide, operate, and maintain the data integration platform.</li>
            <li>To authenticate users and manage accounts.</li>
            <li>To orchestrate, schedule, and monitor data pipelines.</li>
            <li>To process billing and manage subscriptions.</li>
            <li>To ensure platform security, prevent abuse, and maintain audit trails.</li>
            <li>To improve the service using aggregated, non-personal analytics.</li>
          </ul>

          <h2>3. Data Retention</h2>
          <table>
            <thead>
              <tr>
                <th>Data type</th>
                <th>Retention period</th>
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>Account data</td>
                <td>Retained while your account is active; anonymised upon deletion.</td>
              </tr>
              <tr>
                <td>Pipeline run logs</td>
                <td>90 days after execution.</td>
              </tr>
              <tr>
                <td>Audit logs</td>
                <td>12 months.</td>
              </tr>
              <tr>
                <td>Billing records</td>
                <td>7 years (financial regulations).</td>
              </tr>
              <tr>
                <td>Server logs</td>
                <td>30 days.</td>
              </tr>
            </tbody>
          </table>

          <h2>4. Your Rights</h2>
          <p>
            Under the <strong>General Data Protection Regulation (GDPR)</strong>,{" "}
            <strong>Protection of Personal Information Act (POPIA)</strong>, and the{" "}
            <strong>Nigeria Data Protection Regulation (NDPR)</strong>, you have the following
            rights:
          </p>
          <ul>
            <li>
              <strong>Access</strong> &mdash; request a copy of your personal data.
            </li>
            <li>
              <strong>Rectification</strong> &mdash; correct inaccurate or incomplete data.
            </li>
            <li>
              <strong>Erasure</strong> &mdash; request deletion of your personal data (right to be
              forgotten).
            </li>
            <li>
              <strong>Portability</strong> &mdash; receive your data in a machine-readable format.
            </li>
            <li>
              <strong>Objection</strong> &mdash; object to processing based on legitimate interest.
            </li>
            <li>
              <strong>Withdraw consent</strong> &mdash; where processing is based on consent, you
              may withdraw it at any time.
            </li>
          </ul>
          <p>
            You can exercise your access, portability, and erasure rights directly from your account
            settings under <strong>Privacy &amp; Data</strong>, or by contacting us.
          </p>

          <h2>5. Third Parties</h2>
          <ul>
            <li>
              <strong>Stripe</strong> &mdash; payment processing. We share your billing email and
              subscription events with Stripe.
            </li>
            <li>
              <strong>Cloud infrastructure provider</strong> &mdash; all platform data is stored on
              encrypted infrastructure within the provider&apos;s data centres.
            </li>
          </ul>

          <h2>6. Contact</h2>
          <p>
            For any privacy-related questions or to exercise your rights, please contact our Data
            Protection Officer:
          </p>
          <ul>
            <li>
              Email:{" "}
              <a href="mailto:privacy@unifiedlayer.io">privacy@unifiedlayer.io</a>
            </li>
          </ul>
        </article>
      </div>
    </div>
  );
}
