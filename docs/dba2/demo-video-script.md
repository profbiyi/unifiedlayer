# Demo Video Script — UnifiedLayer Fintech Scenarios

**Target length:** 5–7 minutes. **Deliverable for:** DBA Phase 5 (prototype demonstration).
**Prep:** seed the demo orgs first (`python -m backend.scripts.seed_demo_scenarios`), log in as
each demo admin in separate browser profiles (or use super-admin impersonation), close every
other tab, hide bookmarks bar, browser at 100% zoom, light theme.

**Recording:** QuickTime (File → New Screen Recording) or Loom. Record narration live or dub
after. Speak slowly — the viewer is a founder, not an engineer. Test the finished video on 2–3
non-technical people before sending it anywhere (prof's own advice).

---

## Scene 0 — The problem (0:00–0:45) · on unifiedlayer.io

*Show the homepage, scroll slowly through the hero and "Sound familiar?" cards.*

> "If you run a fintech business in Lagos, Nairobi, or Accra, your data is scattered.
> Payments in Paystack. Wallets in M-Pesa. Your books in a spreadsheet. Month-end means
> exporting CSVs and praying the numbers agree.
>
> UnifiedLayer pulls all of it into one warehouse you control. I'm going to show you what
> that looks like for three real kinds of fintech businesses: a payment provider, a mobile
> wallet, and a micro-lender."

## Scene 1 — NairaLink Payments: payment provider (0:45–2:30)

*Log in as `demo.nairalink@unifiedlayer.io`. Land on Overview.*

> "This is NairaLink, a digital payment provider. Their problem: transactions live in
> Paystack, settlements live in an internal database, and reconciling the two for CBN
> reporting eats days every month."

*Click **Sources** — show the two sources (Paystack, Settlement Database).*

> "Two clicks connected Paystack — just the API key. The settlement database is a normal
> Postgres connection. No code."

*Click **Pipelines** — show the two pipelines with schedules.*

> "Two pipelines run automatically: Paystack syncs every six hours, settlements
> reconcile nightly. Nobody exports anything by hand anymore."

*Click **Runs** — scroll the run history slowly.*

> "Here's the proof it runs without babysitting: about six weeks of history, thousands of
> rows per sync, and when something fails — networks fail in Lagos, we know — it retries
> and tells you."

## Scene 2 — KoboVault Wallet: mobile wallet (2:30–3:50)

*Switch to `demo.kobovault@unifiedlayer.io`.*

> "KoboVault runs a mobile wallet. Product wants activity numbers, compliance wants KYC
> records — two teams, two systems, one platform."

*Sources: show MongoDB (Wallet Activity) + Google Sheets (KYC Register).*

> "Wallet events live in MongoDB. And their compliance register? It's a Google Sheet —
> because in the real world, compliance officers love spreadsheets. UnifiedLayer treats
> that sheet as a first-class data source."

*Pipelines + Runs: show the activity sync volume.*

> "Activity syncs every four hours — these runs move several thousand events each. The KYC
> register syncs daily. Both land in one warehouse, so 'active users' and 'verified users'
> finally come from the same place."

## Scene 3 — SwiftCredit MFB: micro-lender (3:50–5:10)

*Switch to `demo.swiftcredit@unifiedlayer.io`.*

> "SwiftCredit is a micro-lender. Loans disbursed from one system, repayments collected in
> another — and the regulator wants portfolio numbers that agree."

*Sources: Loan Management System (Postgres) + Repayments (MySQL). Pipelines: show both.*

> "Disbursements sync nightly, repayments twice a day. From this one warehouse they can
> answer the questions that matter: what did we disburse, what came back, what's at risk —
> and produce the regulatory return from data that reconciles by construction."

## Scene 4 — Why this is different (5:10–6:30) · back on unifiedlayer.io

*Scroll to the pricing section. Click Nigeria → Kenya → Ghana on the market selector.*

> "Two things make this platform different. First, pricing: ₦15,000 a month in Nigeria.
> Not a London price converted to naira — a price set for the Nigerian market. Kenya pays
> Kenyan rates, Ghana pays Ghanaian rates."

*Scroll to the Data Sovereignty section.*

> "Second, control. Designed around the Nigeria Data Protection Act, encrypted credentials,
> and you decide who touches your data. Your data is never sold, shared, or mined."

*Show the Request Access button / form briefly.*

> "Every trial is guided — you request access, we talk for fifteen minutes, and if it fits,
> you get fifteen days with our team helping hands-on. If you run a fintech SME in Nigeria
> or France, we'd like to show you your own business in one place. unifiedlayer.io."

*End card: logo + unifiedlayer.io/request-access.*

---

## Contingencies
- If a page loads empty during recording, refresh once off-camera; the seeded orgs have data.
- Do not show the admin panel or any real access requests in the video.
- Keep the browser profile clean: demo accounts only, no personal email visible.
