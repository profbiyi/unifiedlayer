# Jury Pitch Script — 8 Minutes

Format: 8-minute pitch + 12-minute Q&A
Submit your deck as PDF the Friday before jury day.
Bring a valid ID + QR code invitation. Do NOT bring a laptop — they provide the tech.

---

## [0:00–1:30] THE PROBLEM (90 seconds)

> "Let me tell you about Maria.
>
> Maria runs a 12-person e-commerce business in Lagos, Nigeria. She sells on Shopify, collects payments through Paystack, manages inventory in Google Sheets, and handles customer orders through WhatsApp.
>
> Every Monday morning, she spends three hours exporting CSVs from each of these tools, copying them into a master spreadsheet, and trying to answer basic questions: What sold last week? What's running low? Which customers are churning?
>
> She knows tools like Fivetran exist — they automate all of this. But Fivetran costs two thousand dollars a month. Maria's entire tech budget is two hundred dollars.
>
> She can't afford a data engineer. She can't afford enterprise tools. So she makes decisions on stale, incomplete data.
>
> Maria is not alone. There are 44 million formal SMEs in Africa alone. Hundreds of millions globally. They are generating more data than ever — but they can't use it.
>
> The data integration tools that exist today — Fivetran, Airbyte, Stitch — they were built for companies with data teams. Nobody is building for Maria."

---

## [1:30–3:30] THE SOLUTION + DEMO (2 minutes)

> "[Company Name] is a managed data sync platform that gives SMEs the power of a full data team — without needing one.
>
> Let me show you how it works."

**[LIVE DEMO or SCREENSHOTS — walk through these steps:]**

1. **Connect a source** — "Here I'm connecting a Paystack account. I enter my API key, test the connection, and the platform automatically discovers all available data — transactions, customers, transfers."

2. **Connect a destination** — "I'll sync this to a PostgreSQL database — but it could be BigQuery, Snowflake, Google Sheets, or DuckDB."

3. **Create a pipeline** — "I name my pipeline, select which tables to sync, set a schedule — every hour — and enable quality checks to alert me if data looks wrong."

4. **Show it running** — "The pipeline is now running. You can see rows being extracted and loaded in real-time. When it completes, I can see the lineage — exactly where each piece of data came from and where it went."

> "That's it. Maria just went from three hours of CSV exports every Monday to fully automated data sync — in under ten minutes of setup.
>
> And here's what makes us different from everything else on the market:"

---

## [3:30–4:30] DIFFERENTIATOR (1 minute)

> "Three things no competitor offers:
>
> **First — Africa-native connectors.** We support M-Pesa, WhatsApp Business API, and we're adding Paystack and Flutterwave. Fivetran doesn't. Airbyte doesn't. Nobody does. These are the tools African businesses actually use every day.
>
> **Second — local currency pricing.** We price in Nigerian Naira, Kenyan Shillings, Ghanaian Cedis, CFA Francs. Our customers don't pay a 5 to 15 percent FX premium just to use a data tool. This sounds small, but for an SME spending two hundred dollars a month on software, that's real money.
>
> **Third — built for business owners, not engineers.** Airbyte is free but requires Docker and Kubernetes to run. Our platform requires nothing but a web browser."

---

## [4:30–5:30] MARKET (1 minute)

> "The global data integration market is worth over 12 billion dollars and growing at 12 percent per year. But almost all of that revenue comes from enterprises.
>
> Meanwhile, there are over 400 million SMEs worldwide. In Africa alone, 44 million formal SMEs — the fastest-growing segment on the continent, with digital adoption accelerating every year.
>
> We start in Africa — specifically Nigeria and Kenya — because that's where the pain is sharpest and the competition is zero. From Paris, we expand into Francophone Africa — Senegal, Côte d'Ivoire, Cameroon — 400 million people across 29 countries.
>
> Then Southeast Asia, Latin America, and the global SME market.
>
> This is not a niche. This is the next billion businesses coming online — and nobody is building data infrastructure for them."

---

## [5:30–6:30] TRACTION + BUSINESS MODEL (1 minute)

> "Let me tell you where we are today.
>
> I have built a production-ready platform — not a prototype, not an MVP. Eight source connectors including M-Pesa and WhatsApp Business. Eight destination types including BigQuery, Snowflake, and DuckDB. Full pipeline orchestration with scheduling, automatic retries, and auto-scaling workers. Multi-tenant architecture with role-based access control. Data quality monitoring. Data lineage tracking. The full stack.
>
> I built all of this as a solo technical founder.
>
> [ADD: customer interviews, pilots, waitlist numbers]
>
> Our business model is SaaS subscription. Free tier to acquire users. Professional tier at 29 to 49 dollars per month in local currency. Enterprise tier with custom pricing. Our target unit economics: customer acquisition cost under 30 dollars, lifetime value over 500 dollars."

---

## [6:30–7:15] TEAM (45 seconds)

> "I'm [Your Name]. I'm a software engineer and I built this entire platform — backend, frontend, infrastructure, deployment — from the ground up.
>
> [ADD: Your relevant background — previous companies, Africa market experience, technical expertise]
>
> I know this market because [personal connection to the problem — e.g., I've seen SMEs in Nigeria struggle with this firsthand / I've worked with African businesses that couldn't afford data tools / etc.]
>
> [If co-founders: introduce them and their complementary skills]
>
> My first two hires will be a growth lead for the African market and a customer success manager to ensure our SME users get value from day one."

---

## [7:15–8:00] THE ASK (45 seconds)

> "From Incubateur HEC Paris, I'm looking for three things:
>
> **One — mentorship** on SaaS go-to-market strategy for B2B in emerging markets.
>
> **Two — investor introductions** for a pre-seed round of 200 to 500 thousand euros, which will fund our first two hires and our launch in Nigeria and Kenya.
>
> **Three — Francophone Africa access.** Paris is the gateway to 29 Francophone African countries, and HEC's alumni network is the best door into that market.
>
> We're building the data infrastructure layer for the next billion businesses. The ones that Fivetran, Snowflake, and dbt were never designed for. I'd love to build it here, with you.
>
> Thank you."

---

## ANTICIPATED JURY QUESTIONS + ANSWERS

### "Why not just use Airbyte? It's open-source and free."
> "Airbyte is built for data engineers. You need Docker, Kubernetes, and command-line knowledge to deploy and maintain it. Our target user is a business owner who has never opened a terminal. Also, Airbyte has zero Africa-native connectors — no M-Pesa, no Paystack, no WhatsApp Business. We're solving a different problem for a different user."

### "How will you compete with Fivetran if they decide to go downmarket?"
> "Fivetran's average contract value is over $50,000/year. Their entire sales motion, support structure, and engineering roadmap is built around enterprise customers. Going downmarket to serve $40/month SMEs would cannibalize their positioning and economics. It's the classic innovator's dilemma — it doesn't make strategic sense for them. Meanwhile, building Africa-native connectors and local currency billing requires deep market knowledge they don't have and aren't incentivized to develop."

### "What's your customer acquisition strategy?"
> "Product-led growth. Free tier to get users in the door. Content marketing in English and French targeting 'how to automate your business data' searches. Partnerships with fintech platforms — Paystack and Flutterwave have merchant networks of hundreds of thousands of SMEs. Every one of those merchants is a potential user."

### "You're a solo founder. How will you scale?"
> "I've built a production-grade platform alone — that proves I can execute at an elite level. My first two hires are a growth lead and a customer success manager. I'm not looking to build a 50-person engineering team. The platform architecture is designed for scale — auto-scaling workers, Kubernetes deployment, multi-tenant isolation. I need people for growth and support, not more engineering at this stage."

### "Why France? Why not stay in Africa?"
> "Paris is uniquely positioned. It's the cultural and business gateway to Francophone Africa — 29 countries, 400 million people. The French tech ecosystem is increasingly focused on Africa through initiatives like Digital Africa. Station F gives me access to investors, mentors, and a founder community I can't get anywhere else. And HEC's 60,000 alumni network spans the exact markets I'm targeting."

### "What's your unfair advantage?"
> "Three things: One, I understand the African SME market firsthand — the pain points, the tools they use, the price sensitivity. Two, I've built connectors for data sources no competitor supports. Three, I'm a solo founder who shipped a production platform — I move faster than a team of ten. By the time a competitor decides to build an M-Pesa connector, I'll have ten thousand users syncing data through it."

### "How do you handle data privacy and compliance?"
> "The platform is multi-tenant with complete organization isolation at the database level. All credentials are encrypted. We support role-based access control with audit logging of every action. For African markets, we're aligned with Nigeria's NDPR and Kenya's Data Protection Act. For European operations, we'll be GDPR-compliant — data processing agreements, right to deletion, data residency options."
