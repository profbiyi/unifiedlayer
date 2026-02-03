# Features to Add Before / During Incubator

Prioritized by impact on your application and early users.

---

## PRIORITY 1 — Add Before Applying (Strengthens Application)

### 1.1 Google Sheets as Source + Destination
- **Why:** This is where African SMEs actually live. Many "databases" are Google Sheets.
- **Impact:** Instantly relatable to every SME owner. "Sync your Google Sheet to a real database" is a 10-second pitch.
- **Effort:** Medium — Google Sheets API is well-documented.

### 1.2 Pre-built Sync Templates
- **Why:** "Shopify → Google Sheets in 2 clicks" is more compelling than "create a pipeline."
- **Impact:** Reduces time-to-value from minutes to seconds. Shows you think about UX, not just infrastructure.
- **Templates to build first:**
  - Shopify → Google Sheets
  - Paystack → PostgreSQL
  - M-Pesa → BigQuery
  - REST API → Google Sheets
  - WhatsApp Business → PostgreSQL

### 1.3 Landing Page / Marketing Website
- **Why:** The application asks for a website URL. A clean landing page with your value prop, features, and a waitlist signup shows legitimacy.
- **Recommendation:** Use Carrd ($19/year), Framer, or a simple Next.js page deployed on Vercel.
- **Must include:** One-liner, 3 key features, supported connectors (show logos), waitlist signup form, your story.

---

## PRIORITY 2 — Build During Incubator (First 4 Months)

### 2.1 Local Currency Billing Module
- **What:** Integrate Paystack and/or Flutterwave for payment collection in NGN, KES, GHS, ZAR, XOF/XAF.
- **Why:** Eliminates FX conversion penalty. This is a key differentiator you're pitching — it needs to exist.
- **Implementation:** Paystack has excellent APIs for recurring subscriptions in local currencies.

### 2.2 Paystack Connector (Source)
- **Why:** Paystack is the #1 payment gateway in Nigeria and Ghana. Every e-commerce SME uses it. Syncing transaction data is the most obvious first use case.
- **Data to extract:** Transactions, customers, transfers, refunds, settlements.

### 2.3 Flutterwave Connector (Source)
- **Why:** Pan-African payments. Covers markets Paystack doesn't (Kenya, South Africa, Tanzania, Uganda).

### 2.4 WhatsApp / SMS Pipeline Alerts
- **Why:** You already have the WhatsApp Business connector. Reuse it for notifications. African users check WhatsApp 10x more than email.
- **Example:** "Your Shopify → BigQuery sync failed at 3:00 AM. Reply RETRY to rerun."

### 2.5 MongoDB Connector
- **Why:** You already have the enum defined but it's "coming soon." Many startups in your market use MongoDB. Finishing this shows momentum.

---

## PRIORITY 3 — Build Post-Incubator (6–12 Months)

### 3.1 Embedded Lightweight Dashboards
- Simple charts on top of synced data. Many SMEs don't have a BI tool.
- "Sync + See" > "Sync + go figure out Metabase"

### 3.2 QuickBooks / Xero Connector
- Every SME does accounting. Financial data sync = universal use case.

### 3.3 Offline-Resilient Sync
- Queue operations locally, sync when connectivity returns.
- Critical for African markets with intermittent internet.

### 3.4 Webhook Triggers
- Run pipelines on events (new Paystack transaction) not just cron schedules.
- More real-time, more useful for operational data.

### 3.5 Simple Transformation Layer
- Column renaming, filtering, basic aggregation in the UI.
- Not full dbt — just enough for non-engineers.

### 3.6 MTN MoMo API Connector
- Mobile money beyond M-Pesa — covers West and Central Africa.

### 3.7 Jumia Seller API Connector
- Africa's largest e-commerce marketplace. Seller data sync.

### 3.8 French Language Support
- Localize the UI for Francophone Africa.
- Critical for Senegal, Côte d'Ivoire, Cameroon, DRC market entry.

---

## FEATURES THAT SHOW MATURITY TO THE JURY

Even if not fully built, mentioning these in your roadmap signals sophistication:

- **SOC 2 compliance roadmap** — shows you take security seriously
- **Data residency options** — store data in-region (Africa, EU) for compliance
- **API access** — let power users build on top of your platform
- **Team collaboration features** — shared pipelines, comments, approval workflows
- **Usage analytics dashboard** — show customers their own ROI ("You saved 12 hours this month")
