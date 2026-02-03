# UK Innovator Founder — Business Plan

## Company Overview

**[Company Name]** is a managed, no-code data integration platform purpose-built for small and medium enterprises. We give every SME the data infrastructure that was previously only available to companies with dedicated engineering teams — at a fraction of the cost.

We extract data from the tools businesses already use (payment processors, accounting software, ecommerce platforms, bank accounts), sync it automatically to a central data store, and provide built-in analytics so business owners can make decisions based on complete, real-time data — not stale spreadsheets.

---

## Why the UK?

### 1. UK is the Global Leader in Open Banking
The UK's Open Banking ecosystem (born from PSD2 and the CMA's 2016 ruling) is the most mature in the world. Over 294 registered third-party providers, nearly 6 billion API calls annually, and 50% of UK SMEs now use open banking services. Our platform is built to leverage this infrastructure — aggregating bank transaction data alongside payment, accounting, and ecommerce data into a single view.

### 2. UK-Africa Trade Corridor
The UK is the largest foreign investor in Africa. UK-Africa trade exceeded £40B in 2023. London is home to the highest concentration of Africa-focused fintechs outside the continent. Our platform serves both UK SMEs and African businesses, making London the natural headquarters for a company bridging both markets.

### 3. Access to World-Class Talent
London's tech ecosystem provides access to data engineers, product designers, and go-to-market talent. The UK's Global Talent and Scale-up visas make it possible to recruit internationally as we grow.

### 4. SME Density
The UK has 5.5 million SMEs, accounting for 99.9% of all businesses. 60% of UK private sector employment is in SMEs. This is our core market.

### 5. Making Tax Digital (MTD)
The UK government's MTD mandate requires all VAT-registered businesses to file digitally. This creates a unique data integration need: businesses must connect their accounting software, payment processors, and bank accounts into compliant digital workflows. Our platform enables this.

---

## The Problem

### For UK SMEs:
Small businesses generate data across dozens of tools — Shopify, Stripe, Xero, GoCardless, Amazon Seller, bank accounts — but can't connect it. The result:
- Manual CSV exports pasted into spreadsheets
- Decisions made on stale, incomplete data
- Hours wasted weekly on data busywork instead of growing the business
- MTD compliance complexity across disconnected systems

The tools that solve this are built for enterprises:
- **Fivetran:** Starts at ~$2,000/month for meaningful usage
- **Airbyte (self-hosted):** Free but requires a DevOps engineer
- **Stitch:** Enterprise pricing, enterprise complexity

No one is building data infrastructure for the 5.5M UK SMEs that need it but can't afford a data team.

### For African Businesses (Expansion Market):
Everything above, plus:
- Unconventional data sources (M-Pesa, Paystack, Flutterwave, WhatsApp Business) that no competitor supports
- FX penalty: 5-15% markup on USD-priced SaaS
- No local support from enterprise vendors

---

## The Solution

A managed, no-code data sync platform that:

1. **Connects to UK-native data sources** — GoCardless (Direct Debit), Open Banking (Plaid/TrueLayer), Xero, FreeAgent, HMRC MTD, Stripe UK, Square, Shopify
2. **Connects to Africa-native sources** — M-Pesa, Paystack, Flutterwave, WhatsApp Business (no competitor offers these)
3. **Syncs automatically** on schedule or trigger — with retries, error handling, and quality checks
4. **Costs 10-20x less** than Fivetran — with local currency pricing
5. **Requires zero engineering knowledge** — first pipeline in under 10 minutes
6. **Monitors data quality** — know when something breaks before it affects decisions
7. **Tracks data lineage** — see exactly where data comes from and how it flows
8. **Provides built-in analytics** — dashboards and reports on synced data without needing a separate BI tool

---

## Innovation

### What makes this genuinely new:

1. **UK-Specific Connectors No One Else Offers:**
   - **GoCardless connector** — Direct Debit is the backbone of UK recurring payments (80%+ of subscriptions). No data integration platform offers a native GoCardless connector.
   - **Open Banking aggregation** — Pull bank transaction data from all UK banks via a single connector using TrueLayer/Plaid APIs. No competitor offers this as a data source.
   - **HMRC Making Tax Digital** — Sync VAT returns and tax data. This is a UK-specific regulatory requirement affecting every VAT-registered business. No data platform connects to it.
   - **FreeAgent** — Used by 150,000+ UK businesses (free for NatWest/RBS customers). No competitor offers a connector.

2. **Africa-Native Connectors (Market Expansion):**
   - M-Pesa, Paystack, Flutterwave, WhatsApp Business API — connectors that Fivetran, Airbyte, and Stitch do not support

3. **No-Code for Non-Engineers:**
   - Enterprise data platforms target data engineers. We target the business owner. 5-step wizard, plain-English configuration, built-in quality checks and lineage — no SQL, no Docker, no YAML.

4. **Built-In Data Quality + Lineage at SME Price:**
   - Fivetran charges enterprise pricing for lineage. Airbyte doesn't offer it at all. We include 7 quality check types and full lineage tracking in every plan.

5. **Open Banking as a Data Source (not just payments):**
   - Most Open Banking use cases are payments. We use it as a **data source** — pulling transaction history, categorization, and cash flow data into a unified data layer alongside payment, accounting, and ecommerce data. This is novel.

---

## Viability

### Revenue Model

```
Free Tier (Starter)
├── 3 connectors, 10,000 rows/month, 1 user
├── Purpose: acquisition funnel, product-led growth
└── No credit card required

Professional (£25-45/month)
├── Unlimited connectors, 500,000 rows/month, 5 users
├── Scheduling, quality checks, lineage, analytics
├── Email support
└── Purpose: core revenue driver

Enterprise (Custom pricing)
├── Unlimited everything, SLA guarantees
├── Dedicated support, SSO/SAML, custom connectors
├── On-premise deployment option
└── Purpose: large organizations, high ARPU
```

### Pricing in local currencies:
- UK: GBP (Stripe)
- Nigeria: NGN (Paystack)
- Kenya: KES (M-Pesa/Paystack)
- Ghana: GHS (Paystack)
- South Africa: ZAR (Paystack)
- Francophone Africa: XOF/XAF (Flutterwave)

### Unit Economics (Target)
- CAC: £30-50 (content marketing + product-led growth)
- ARPU: £35/month
- LTV: £1,260 (36-month avg lifetime)
- LTV:CAC ratio: 25:1+

### Current Product Status
Production-grade platform with:
- 8 source connectors, 8 destination types
- Full pipeline orchestration (Prefect) with scheduling, retries, CDC
- Multi-tenant architecture with RBAC (3-tier roles)
- Data lineage at table and column level
- 7 data quality check types
- Auto-scaling worker pool (1-10 workers)
- Prometheus + Grafana monitoring
- Complete Next.js 14 frontend
- Stripe billing integration with usage metering
- Kubernetes deployment ready

### Go-to-Market Strategy (UK)
**Phase 1 (Months 1-6): UK Launch**
- Direct outreach to UK SMEs using Xero/Shopify/Stripe
- Content marketing: "How to connect your Xero data to BigQuery without an engineer"
- Partnership with UK accounting firms and bookkeepers
- Launch on Product Hunt, Hacker News
- Target: 100 free users, 20 paying customers

**Phase 2 (Months 7-12): UK Growth + Africa Soft Launch**
- Integration partnerships with GoCardless, Xero, FreeAgent
- Attend UK SME events (The Business Show, SME XPO)
- Launch Africa-native connectors for Nigerian and Kenyan markets
- Target: 500 free users, 100 paying customers

**Phase 3 (Year 2): Scale**
- Expand connector marketplace (SDK for third-party connectors)
- Launch embedded analytics features
- Enter Southeast Asian and Latin American markets
- Target: 2,000 free users, 500 paying customers, £200K ARR

---

## Scalability

### Technical Scalability
- **Auto-scaling architecture:** 1-10 Prefect workers scale dynamically based on queue depth. Kubernetes HPA extends to 3-10 API replicas.
- **Multi-tenant isolation:** Each organization's data is fully isolated at the database level with row-level security
- **Connector SDK:** Third-party developers can build and publish connectors, scaling the connector count from 8 to hundreds without internal engineering effort
- **Infrastructure:** Designed for cloud-native deployment on AWS/GCP/Azure with horizontal scaling

### Market Scalability
- **TAM:** Global data integration market: $12.3B (2023), projected $23B+ by 2028
- **SAM:** UK SMEs with digital tools (~1.5M) + African SMEs with digital tools (~5M)
- **SOM (3-year):** 5,000 paying SMEs at £35/month average = £2.1M ARR

### Expansion Path
```
Year 1: UK (core market) + Nigeria/Kenya (soft launch)
Year 2: UK growth + Pan-African expansion (Ghana, South Africa, Francophone Africa)
Year 3: Southeast Asia (Indonesia, Philippines) + Latin America (Brazil, Mexico)
Year 5: Global SME market
```

### Job Creation Plan

| Timeline | Role | Location | Purpose |
|----------|------|----------|---------|
| Month 1-3 | Founder (full-time) | London, UK | Product, engineering, sales |
| Month 6 | Backend Engineer | London / Remote UK | Connector development, infrastructure |
| Month 9 | Frontend Engineer | London / Remote UK | Dashboard, analytics, UX |
| Month 12 | Customer Success | London | Onboarding, support, retention |
| Month 15 | Sales / Partnerships | London | UK SME outreach, accounting firm partnerships |
| Year 2 | 2x Engineers | London / Lagos | Scale engineering team |
| Year 2 | Marketing | London | Content, SEO, events |
| Year 3 | 10+ employees | London HQ | Full team across engineering, sales, support |

All UK roles will be skilled positions (£40-70K salary range) contributing to the UK economy. Engineering roles require degree-level qualifications or equivalent experience.

### Credible Research Backing

- UK SME data: [Federation of Small Businesses](https://www.fsb.org.uk/) — 5.5M SMEs in UK
- Open Banking: [Open Banking Implementation Entity](https://www.openbanking.org.uk/) — 294 TPPs, 6B+ API calls
- Market sizing: Mordor Intelligence — UK payment market $523B (2025), growing 12.4% CAGR
- African SME data: IFC — 44M+ formal SMEs in Africa
- Data integration market: Gartner — $12.3B (2023), $23B+ by 2028
- MTD compliance: HMRC — all VAT-registered businesses must file digitally

---

## Competitive Landscape

| Feature | Our Platform | Fivetran | Airbyte (OSS) | Stitch |
|---------|-------------|----------|---------------|--------|
| Price for SME | £25-45/mo | £1,500+/mo | Free (needs DevOps) | £80+/mo |
| GoCardless connector | Yes | No | Community (unstable) | No |
| Open Banking connector | Yes | No | No | No |
| HMRC MTD connector | Yes | No | No | No |
| Africa-native connectors | M-Pesa, Paystack, WhatsApp | None | None | None |
| Local currency billing | GBP, NGN, KES, GHS, ZAR | USD only | N/A | USD only |
| No-code setup | Yes | Yes | No (Docker/K8s) | Yes |
| Data quality checks | Built-in (7 types) | Enterprise add-on | Community plugins | None |
| Data lineage | Built-in | Enterprise only | None | None |
| Target user | Business owner | Data engineer | Data engineer | Data engineer |

**Our moat:** UK-native connectors (GoCardless, Open Banking, HMRC MTD) + Africa-native connectors + local currency pricing + designed for non-engineers. This combination does not exist anywhere.

---

## Risk Assessment

| Risk | Mitigation |
|------|------------|
| Competition from Fivetran/Airbyte moving downmarket | They are moving upmarket toward enterprise. SME market is unattractive to them at their cost structure. Our cost base is 100x lower. |
| Open Banking API changes | We abstract the API layer. Switching providers (Plaid ↔ TrueLayer ↔ Tink) takes days, not months. |
| Low SME willingness to pay | Freemium model reduces friction. Product-led growth proven by Stripe, Xero, and Shopify in the SME segment. |
| Technical execution risk | Platform already built and production-ready. Solo technical founder has delivered full-stack platform. |
| Currency/FX risk on African revenue | Local currency billing via Paystack/Flutterwave with daily settlement to GBP. |

---

## Founder Background

[YOU FILL]

Key points to emphasize:
- Solo technical founder who built the entire platform (backend, frontend, infrastructure, deployment)
- This demonstrates exceptional execution ability
- Technical depth across data engineering, cloud infrastructure, and product design
- Understanding of both UK and African markets
- [Add relevant work experience, education, domain expertise]

---

## Financial Projections (3 Years)

| Metric | Year 1 | Year 2 | Year 3 |
|--------|--------|--------|--------|
| Free users | 500 | 2,000 | 8,000 |
| Paying customers | 100 | 500 | 2,000 |
| ARPU (monthly) | £35 | £38 | £42 |
| MRR (end of year) | £3,500 | £19,000 | £84,000 |
| ARR (end of year) | £42,000 | £228,000 | £1,008,000 |
| Employees | 2 | 5 | 12 |
| Monthly burn | £8,000 | £25,000 | £60,000 |

### Funding Strategy
- **Pre-seed (during visa period):** £100-150K from UK angel investors / SEIS-eligible round
- **Seed (Year 2):** £500K-1M for team scaling and market expansion
- **SEIS/EIS eligibility:** UK tax incentives make early-stage investment highly attractive to UK angels (50-78% tax relief)

---

## Summary: Why This Meets Innovator Founder Criteria

### Innovation
- UK-first connectors (GoCardless, Open Banking, HMRC MTD) that no competitor offers
- Africa-native connectors bridging UK-Africa trade
- No-code approach democratizing enterprise data tools for SMEs
- Built-in lineage + quality at price points where competitors don't offer them

### Viability
- Production-ready platform with working product
- Clear revenue model with proven SaaS unit economics
- Go-to-market strategy leveraging UK SME density and partnerships
- Stripe billing integration with usage metering already built

### Scalability
- Multi-tenant, auto-scaling architecture ready for thousands of customers
- Connector SDK enables community-driven growth (8 → hundreds of connectors)
- Clear international expansion path: UK → Africa → Southeast Asia → Global
- Job creation plan: 2 employees Year 1, 12+ by Year 3
- £1M+ ARR target by Year 3 backed by credible market research
