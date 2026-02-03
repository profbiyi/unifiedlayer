import Link from "next/link";

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="mx-auto max-w-3xl px-6 py-16">
        <Link
          href="/"
          className="text-sm text-muted-foreground hover:text-foreground transition-colors"
        >
          &larr; Back to home
        </Link>

        <article className="prose prose-neutral dark:prose-invert mt-8 max-w-none">
          <h1>Terms of Service</h1>
          <p className="lead">
            Last updated: {new Date().toLocaleDateString("en-GB", { day: "numeric", month: "long", year: "numeric" })}
          </p>

          <h2>1. Acceptance of Terms</h2>
          <p>
            By accessing or using the UnifiedLayer platform (&quot;Service&quot;), you agree to be bound
            by these Terms of Service (&quot;Terms&quot;). If you do not agree, you may not use the
            Service. These Terms constitute a legally binding agreement between you and UnifiedLayer Ltd
            (&quot;Company&quot;, &quot;we&quot;, &quot;us&quot;).
          </p>

          <h2>2. Service Description</h2>
          <p>
            UnifiedLayer provides a cloud-based data integration platform that enables organisations to
            connect data sources, configure pipelines, and synchronise data to destinations. The
            Service includes pipeline orchestration, scheduling, monitoring, data quality checks,
            and related tooling.
          </p>

          <h2>3. User Obligations</h2>
          <ul>
            <li>You must provide accurate and complete registration information.</li>
            <li>You are responsible for maintaining the confidentiality of your credentials.</li>
            <li>
              You must not use the Service for any unlawful purpose or in violation of any
              applicable law or regulation.
            </li>
            <li>
              You must not attempt to gain unauthorised access to the Service, other accounts, or
              underlying systems.
            </li>
            <li>
              You are solely responsible for the data you process through the platform and must
              ensure you have the necessary rights and consents.
            </li>
          </ul>

          <h2>4. Billing and Payment</h2>
          <ul>
            <li>
              Subscriptions are billed in advance on a monthly or annual basis depending on the plan
              selected.
            </li>
            <li>
              All fees are non-refundable except where required by applicable law or as otherwise
              stated in your plan terms.
            </li>
            <li>
              We reserve the right to change pricing with 30 days&apos; written notice. Continued
              use after the notice period constitutes acceptance of the new pricing.
            </li>
            <li>
              If payment fails, we may suspend access to the Service until the outstanding balance
              is settled.
            </li>
          </ul>

          <h2>5. Intellectual Property</h2>
          <p>
            The Service, including all software, designs, and documentation, is the intellectual
            property of UnifiedLayer Ltd. You retain ownership of your data. By using the Service you
            grant us a limited licence to process your data solely for the purpose of providing the
            Service.
          </p>

          <h2>6. Limitation of Liability</h2>
          <p>
            To the maximum extent permitted by law, the Company shall not be liable for any
            indirect, incidental, special, consequential, or punitive damages, or any loss of
            profits or revenue, whether incurred directly or indirectly, or any loss of data, use,
            goodwill, or other intangible losses resulting from your use of the Service.
          </p>
          <p>
            Our total aggregate liability for all claims arising out of or relating to these Terms
            or the Service shall not exceed the amount you paid us in the twelve (12) months
            preceding the claim.
          </p>

          <h2>7. Termination</h2>
          <p>
            Either party may terminate the agreement at any time. You may delete your account via
            the Privacy &amp; Data settings page. We may suspend or terminate your access if you
            breach these Terms, with reasonable notice where practicable.
          </p>

          <h2>8. Governing Law</h2>
          <p>
            These Terms shall be governed by and construed in accordance with the laws of England
            and Wales. Any disputes arising under these Terms shall be subject to the exclusive
            jurisdiction of the courts of England and Wales.
          </p>

          <h2>9. Changes to These Terms</h2>
          <p>
            We may update these Terms from time to time. We will notify you of material changes by
            email or via an in-app notice at least 30 days before the changes take effect. Your
            continued use of the Service after that date constitutes acceptance of the revised
            Terms.
          </p>

          <h2>10. Contact</h2>
          <p>
            If you have questions about these Terms, please contact us:
          </p>
          <ul>
            <li>
              Email:{" "}
              <a href="mailto:legal@unifiedlayer.io">legal@unifiedlayer.io</a>
            </li>
          </ul>
        </article>
      </div>
    </div>
  );
}
