# Pitch Deck Outline — Incubateur HEC Paris

Build this in Google Slides, Canva, or Figma. Export as PDF for the application.
Keep it to **10–12 slides max**. The jury pitch is 8 minutes — aim for ~45 seconds per slide.

---

## Slide 1: Title

**[Company Name]**
The data platform for SMEs and emerging markets.

- Your name & title
- Company logo
- One-liner: "Enterprise-grade data sync. SME-friendly price. Africa-native."

---

## Slide 2: The Problem

**"SMEs are data-rich but insight-poor."**

Tell a story — make it human:

> Maria runs a 12-person e-commerce business in Lagos. She sells on Shopify, collects payments through Paystack, manages inventory in Google Sheets, and handles customer orders via WhatsApp.
>
> Every Monday morning, she spends 3 hours exporting CSVs from each tool, pasting them into a master spreadsheet, and trying to figure out what sold, what's low on stock, and which customers are churning.
>
> She knows Fivetran exists. It costs $2,000/month. Her entire monthly tech budget is $200.
>
> She can't afford a data engineer. She can't afford Fivetran. So she flies blind.

**Visual:** Show a messy flow of disconnected tools with manual CSV arrows between them.

---

## Slide 3: The Market

**Two numbers that matter:**

- **44M+** formal SMEs in Africa (fastest growing segment globally)
- **$12B+** global data integration market, growing 12% CAGR
- **0** data integration tools built for SMEs or African data sources

**Visual:** Map of Africa highlighting key markets (Nigeria, Kenya, Ghana, South Africa, Francophone West Africa). Show the gap — enterprise tools on one side, SMEs with nothing on the other.

---

## Slide 4: The Solution

**[Company Name] connects your data sources to your destinations — no code, no engineers, no $2,000/month bills.**

Three key capabilities:
1. **Connect** — 8+ source connectors including M-Pesa, WhatsApp Business, REST APIs
2. **Sync** — Automated pipelines with scheduling, retries, and real-time CDC
3. **Trust** — Built-in data quality checks and lineage tracking

**Visual:** Clean diagram showing Source → [Your Platform] → Destination with logos of supported tools.

---

## Slide 5: Live Product Screenshots

**Show the actual product.** This is where you win.

Include screenshots of:
- Dashboard overview with pipeline metrics
- Pipeline creation flow
- Source connector setup (show M-Pesa or WhatsApp — the Africa-native ones)
- Data lineage graph visualization
- Quality check results

> **Jury tip:** If possible during the live pitch, do a LIVE DEMO instead of screenshots. Nothing beats watching real data flow from source to destination.

---

## Slide 6: Africa-Native Differentiator

**"We support data sources that no competitor touches."**

| What We Support | Fivetran | Airbyte | Stitch |
|----------------|----------|---------|--------|
| M-Pesa API | No | No | No |
| WhatsApp Business | No | No | No |
| Paystack (planned) | No | No | No |
| Flutterwave (planned) | No | No | No |
| Local currency billing | No | No | No |

**Plus:** Priced in NGN, KES, GHS, ZAR, XOF — no FX conversion penalty.

---

## Slide 7: Business Model

```
Starter (Free)          Professional ($29-49/mo)     Enterprise (Custom)
├── 3 connectors        ├── Unlimited connectors      ├── Unlimited everything
├── 10K rows/month      ├── 500K rows/month           ├── SLA + dedicated support
├── 1 user              ├── 5 users                   ├── SSO / SAML
└── Community support   ├── Scheduling + quality      └── Custom connectors
                        └── Email support
```

**Key:** All prices available in local African currencies via Paystack/Flutterwave. No USD conversion = 5–15% savings for African customers.

**Unit economics target:**
- CAC: <$30 (product-led growth via free tier)
- LTV: $500+ (14+ month average retention for SaaS)
- LTV/CAC: >15x

---

## Slide 8: Traction

**What we've built:**
- Production-ready platform (not a prototype)
- 8 source connectors, 8 destination types
- Full orchestration: scheduling, retries, CDC, auto-scaling (1–10 workers)
- Multi-tenant RBAC with 3 subscription tiers
- Data lineage + quality monitoring
- Kubernetes-ready deployment

**What we're building next:**
- Paystack, Flutterwave, Google Sheets connectors
- Local currency billing module
- Pre-built sync templates (one-click setup)
- WhatsApp/SMS pipeline alerts

[ADD YOUR ACTUAL USER/PILOT/INTERVIEW NUMBERS HERE]

---

## Slide 9: Competitive Landscape

**2x2 Matrix:**

```
                    Engineer-friendly
                         |
              Airbyte    |    Fivetran
              (free,     |    (expensive,
              complex)   |    powerful)
                         |
    Affordable ──────────┼──────────── Expensive
                         |
              [US] ◄─────|─────► [US]
                         |
                    Non-technical

    WE ARE HERE: Affordable + Non-technical + Africa-native
    (Bottom-left quadrant — unoccupied by any competitor)
```

**Why competitors won't copy us:**
- Fivetran: SME ARPU doesn't justify their sales-led model
- Airbyte: Open-source DNA means they build for engineers, not business owners
- Neither will build M-Pesa or Paystack connectors for a market they don't understand

---

## Slide 10: Go-to-Market Strategy

**Phase 1: Nigeria + Kenya (Month 1–6)**
- Direct outreach to SMEs using Shopify, Paystack, M-Pesa
- Content marketing: "How to automate your business data" (English)
- Product-led growth via free tier
- Partnerships with fintech platforms (Paystack, Flutterwave)

**Phase 2: Francophone Africa (Month 6–12)**
- Leverage Paris/HEC network for Francophone market entry
- Localize to French
- Target Senegal, Côte d'Ivoire, Cameroon, DRC
- Partner with Orange Money, Wave

**Phase 3: Global SMEs (Year 2+)**
- Southeast Asia, Latin America
- Expand connector library
- Enterprise tier for larger organizations

---

## Slide 11: The Team

**[Your Name] — Founder & CEO**
- Built the entire platform solo: backend, frontend, infrastructure, deployment
- [Your background — technical skills, domain expertise, Africa market knowledge]
- [Any relevant previous experience]

> **Jury note:** A solo technical founder who built a production-grade platform is the strongest possible signal of execution ability. Lead with this.

[Add co-founders here if applicable]

---

## Slide 12: The Ask

**What we need from Incubateur HEC Paris:**

1. **Mentorship** — SaaS pricing strategy, go-to-market for B2B in Africa
2. **Network** — Introductions to pre-seed/seed investors focused on Africa tech
3. **Market access** — Francophone Africa connections via HEC alumni
4. **Community** — Peer founders to learn from and grow with

**Our next milestones:**
- 50 paying customers in 6 months
- Pre-seed round of €200–500K
- Hire first two team members (growth + customer success)

---

## DESIGN TIPS

- Use a clean, modern template (dark mode works well for tech products)
- Maximum 20 words per slide — the slide supports your speech, it doesn't replace it
- Use product screenshots liberally — you have a real product, show it
- Include the logos of tools you integrate with — visual recognition is powerful
- End with your contact info and a clear CTA
