# Innovator Founder Endorsement — Criteria Mapping

How our platform maps to each assessment criterion.

---

## 1. INNOVATION

**Requirement:** The business must be a genuine, original business idea that is different from anything else on the market.

### Evidence:

**a) UK-Specific Data Connectors (No Competitor Offers These)**
- GoCardless connector — Direct Debit powers 80%+ of UK recurring payments. Zero data platforms connect to it.
- Open Banking as a data source — Using PSD2/Open Banking infrastructure for data integration, not just payments. Novel application.
- HMRC Making Tax Digital — UK regulatory data as a pipeline source. No data platform connects to it.
- FreeAgent — 150,000+ UK users, no data platform offers a connector.

**b) Africa-Native Connectors**
- M-Pesa, Paystack, Flutterwave, WhatsApp Business — connectors for Africa's dominant payment and communication platforms. Fivetran, Airbyte, and Stitch offer none of these.

**c) No-Code for Non-Engineers**
- Enterprise data platforms (Fivetran, Airbyte) target data engineers. We target business owners.
- 5-step pipeline wizard: select source → configure → discover schema → select destination → schedule. No SQL, no Docker, no YAML.

**d) Built-In Quality + Lineage at SME Price**
- Data lineage: Fivetran charges enterprise pricing. Airbyte doesn't offer it.
- Quality checks: 7 types included in every plan (row count, null checks, uniqueness, freshness, custom SQL, range validation, referential integrity).

---

## 2. VIABILITY

**Requirement:** The applicant must have, or be actively developing, the necessary skills, knowledge, experience and market awareness to successfully run the business.

### Evidence:

**a) Working Product**
- Production-grade platform — not a prototype. Full backend (FastAPI, PostgreSQL, Prefect), full frontend (Next.js 14), full infrastructure (Docker, Kubernetes, monitoring).
- 8 source connectors, 8 destination types, multi-tenant RBAC, data lineage, quality checks, auto-scaling workers.
- Stripe billing integration with usage metering.

**b) Solo Technical Founder**
- Entire platform built by a single founder — backend, frontend, infrastructure, DevOps.
- Demonstrates exceptional technical execution ability.
- Reduces early-stage risk: no dependency on outsourced development.

**c) Clear Revenue Model**
- SaaS subscription: Free → £25-45/month → Enterprise custom pricing.
- Usage-based component (rows synced/month) ensures revenue scales with customer value.
- Stripe for UK/global billing, Paystack for African markets.

**d) Market Validation**
- [ADD: Customer interviews conducted — aim for 10-20 before applying]
- [ADD: Waitlist signups from landing page]
- [ADD: Any pilot users or beta testers]

**e) Financial Planning**
- [ADD: Personal runway / savings]
- [ADD: Funding strategy — SEIS angel round during visa period]
- Clear cost structure: cloud hosting (£200-500/month), no office needed initially.

---

## 3. SCALABILITY

**Requirement:** The applicant must show evidence of structured planning demonstrating a credible path to growth.

### Evidence:

**a) Structured Growth Path**
```
Year 1: UK launch → 100 paying customers → £42K ARR
Year 2: UK growth + Africa → 500 customers → £228K ARR
Year 3: International expansion → 2,000 customers → £1M+ ARR
```

**b) Job Creation**
| Timeline | Hires | Roles |
|----------|-------|-------|
| Month 6 | 1 | Backend Engineer (London) |
| Month 9 | 1 | Frontend Engineer (London/Remote UK) |
| Month 12 | 1 | Customer Success (London) |
| Month 15 | 1 | Sales & Partnerships (London) |
| Year 2 | 3 | Engineers + Marketing |
| Year 3 | 4+ | Scaling all functions |

All UK-based roles at £40-70K salary range. Skilled positions contributing to UK economy.

**c) National and International Market Growth**
- **National:** 5.5M UK SMEs, 1.2M VAT-registered businesses. Focus on Shopify/Xero/Stripe users.
- **International:** 44M+ African SMEs, growing fintech adoption. Expansion to Southeast Asia and Latin America by Year 3.

**d) Technical Scalability**
- Auto-scaling workers: 1-10 Prefect workers, up to 50 concurrent pipelines
- Kubernetes deployment with HPA (3-10 API replicas)
- Connector SDK: third-party developers extend the platform without internal engineering cost
- Multi-tenant architecture isolates customer data at database level

**e) Credible Research**
- UK SME count: ONS Business Population Estimates 2024 — 5.5M SMEs
- Open Banking adoption: OBIE — 50% of UK SMEs use open banking services
- Data integration market: Gartner — $12.3B (2023), $23B+ by 2028 (13% CAGR)
- African fintech: McKinsey — Africa's fintech revenues projected to reach $30B+ by 2025
- UK-Africa trade: UK Government — £40B+ bilateral trade

---

## Key Documents to Prepare for Endorsement Meeting

- [ ] This business plan
- [ ] Live product demo (running platform with sample data)
- [ ] Landing page / website URL
- [ ] Financial projections spreadsheet (3 years)
- [ ] Evidence of customer interviews / market research
- [ ] Competitor analysis with specific pricing data
- [ ] Personal CV highlighting technical skills and relevant experience
- [ ] Funding strategy (SEIS angel round plan)
- [ ] Job creation timeline with salary ranges
- [ ] Evidence of UK market knowledge (UK-specific connectors, MTD, Open Banking)
