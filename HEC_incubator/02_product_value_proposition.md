# Product Value Proposition — Detailed Reference

Use this document when answering follow-up questions from the jury or elaborating on any form field.

---

## THE PROBLEM (Use this language everywhere)

### For Global SMEs:
Small and medium businesses generate data across dozens of tools — Shopify, Stripe, QuickBooks, Google Sheets, CRMs, payment gateways. But they can't connect it. The result:
- Manual CSV exports pasted into spreadsheets
- Decisions made on stale, incomplete data
- Hours wasted weekly on data busywork instead of growing the business

The tools that solve this (Fivetran, Stitch, Airbyte) are built for enterprises:
- **Fivetran:** Starts at ~$2,000/month for meaningful usage
- **Airbyte (self-hosted):** Free but requires a DevOps engineer to deploy, maintain, and debug
- **Stitch:** Acquired by Talend, now part of Qlik — enterprise pricing, enterprise complexity

No one is building for the 400M+ SMEs worldwide that need data infrastructure but can't afford a data team.

### For African Businesses (The Unique Angle):
Everything above, plus:
- **Unconventional data sources:** M-Pesa, MTN MoMo, Paystack, Flutterwave, WhatsApp Business, USSD flows — none of which Fivetran or Airbyte support
- **FX penalty:** African businesses pay 5–15% more for any USD-priced SaaS tool due to currency conversion and bank fees
- **Connectivity challenges:** Unreliable internet means sync jobs fail silently on tools not designed for it
- **No local support:** Enterprise tools have zero presence or support in African markets

---

## THE SOLUTION

A managed, no-code data sync platform that:

1. **Connects to the tools SMEs actually use** — including Africa-native sources (M-Pesa, WhatsApp Business, Paystack) that no competitor supports
2. **Syncs automatically** on schedule or on trigger — with retries, error handling, and quality checks built in
3. **Costs 10–20x less** than Fivetran — and prices in local currencies to eliminate FX markup
4. **Requires zero engineering knowledge** — a business owner sets up their first pipeline in under 10 minutes
5. **Monitors data quality** — so you know when something breaks before it affects your decisions
6. **Tracks data lineage** — see exactly where your data comes from and how it flows

---

## WHY NOW

1. **African digital adoption is accelerating** — 44M+ formal SMEs, fintech penetration growing 30%+ YoY
2. **Data tools are commoditizing** — open-source frameworks (DLT, Prefect) make it possible to build enterprise-grade infrastructure at a fraction of the cost
3. **Francophone Africa is underserved** — 400M people across 29 countries, growing tech ecosystem, direct access from Paris
4. **SMEs are the fastest-growing segment** globally but the least served by data tooling

---

## COMPETITIVE LANDSCAPE

| Feature | Our Platform | Fivetran | Airbyte (OSS) | Stitch |
|---------|-------------|----------|---------------|--------|
| Price for SME | $29–49/mo | $2,000+/mo | Free (but needs DevOps) | $100+/mo |
| Africa-native connectors | M-Pesa, WhatsApp, Paystack | None | None | None |
| Local currency billing | Yes (NGN, KES, GHS, ZAR, XOF) | USD only | N/A | USD only |
| No-code setup | Yes | Yes | No (Docker/K8s required) | Yes |
| Data quality checks | Built-in (7 types) | Add-on | Community plugins | None |
| Data lineage | Built-in | Enterprise only | None | None |
| Offline resilience | Planned | No | No | No |
| Target user | Business owner | Data engineer | Data engineer | Data engineer |

**Our moat:** Africa-native connectors + local currency pricing + designed for non-engineers. This combination does not exist anywhere.

---

## TRACTION TALKING POINTS

Adapt these based on your actual numbers:

- "Production-ready platform with 8 source connectors and 8 destination types"
- "Full pipeline orchestration — scheduling, retries, CDC, auto-scaling"
- "Multi-tenant architecture serving multiple organizations with role-based access"
- "[X] customer interviews conducted with SME owners in [countries]"
- "[X] pilot users / waitlist signups" (add if applicable)
- "Built by a solo technical founder — entire platform from backend to frontend to deployment"

> **Jury tip:** "Built by a solo technical founder" is EXTREMELY powerful at HEC. It demonstrates the "Executor" trait they prize above all else. Do not undersell this.

---

## MARKET SIZING

### TAM (Total Addressable Market)
- Global data integration market: $12.3B (2023), projected $23B+ by 2028
- 400M+ SMEs worldwide

### SAM (Serviceable Addressable Market)
- African SMEs with digital tools: ~5M businesses
- Global SMEs paying for SaaS tools: ~50M businesses

### SOM (Serviceable Obtainable Market — 3-year target)
- 10,000 paying SMEs across Africa and emerging markets
- At $40/month average: $4.8M ARR

### Expansion Path
Africa (Year 1–2) → Southeast Asia, Latin America (Year 3–4) → Global SME market (Year 5+)

---

## REVENUE MODEL

```
Free Tier (Starter)
├── 3 connectors
├── 10,000 rows/month
├── 1 user
├── Community support
└── Purpose: acquisition funnel, product-led growth

Professional ($29–49/month in local currency)
├── Unlimited connectors
├── 500,000 rows/month
├── 5 users
├── Scheduling + quality checks
├── Email support
└── Purpose: core revenue driver

Enterprise (Custom pricing)
├── Unlimited everything
├── SLA guarantees
├── Dedicated support
├── SSO / SAML
├── Custom connectors
└── Purpose: large organizations, high ARPU
```

---

## KEY METRICS TO TRACK (Show the jury you think like an operator)

- **MRR / ARR** — Monthly/Annual Recurring Revenue
- **Pipeline success rate** — % of syncs completing without error
- **Time to first pipeline** — How fast a new user creates their first sync
- **Rows synced/month** — Platform throughput
- **Net Revenue Retention** — Expansion vs. churn
- **CAC / LTV ratio** — Unit economics
