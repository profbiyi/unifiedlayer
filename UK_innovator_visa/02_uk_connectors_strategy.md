# UK-Specific Connector Strategy

## Priority UK Connectors to Build

These are the "unconventional" UK data sources equivalent to M-Pesa/Paystack in Africa — connectors that no competitor offers and that are deeply embedded in UK SME operations.

---

## Tier 1 — Must Have (Build Before Endorsement Application)

### 1. GoCardless (Direct Debit)
- **What it is:** The dominant Direct Debit platform in the UK. 75,000+ businesses use it. Direct Debit collects 80%+ of UK recurring payments (rent, subscriptions, memberships, invoices).
- **Why it's unique:** No data integration platform offers a GoCardless connector. Fivetran, Airbyte, Stitch — none of them.
- **API:** REST API, well-documented. OAuth2 for partner apps.
- **Data to extract:** Payments, payouts, mandates (authorizations), customers, refunds, events, subscriptions
- **Use case:** "See all your recurring revenue, failed payments, and customer churn in one dashboard — synced automatically from GoCardless."
- **API Docs:** https://developer.gocardless.com/

### 2. Open Banking (via TrueLayer or Plaid)
- **What it is:** Access to bank transaction data from all major UK banks (HSBC, Barclays, Lloyds, NatWest, Santander, etc.) via a single API.
- **Why it's unique:** Open Banking is typically used for payments. We use it as a **data source** — pulling transaction history, balances, and categorized spending into a data warehouse. This is novel.
- **API:** TrueLayer (UK-headquartered) or Plaid. Both provide account info (AIS) and payment initiation (PIS).
- **Data to extract:** Accounts, balances, transactions (with merchant categorization), standing orders, direct debits
- **Use case:** "Automatically sync your business bank transactions to BigQuery. See cash flow trends, categorize spending, reconcile with invoices — no manual exports."
- **Regulatory note:** We would operate as a data processor, not an AISP. The Open Banking provider (TrueLayer/Plaid) holds the FCA authorization.
- **API Docs:** https://truelayer.com/docs/

### 3. Xero
- **What it is:** The #1 cloud accounting platform for UK SMEs. 3.95M subscribers globally, dominant in UK, Australia, New Zealand.
- **Why it matters:** Every UK SME using Xero has invoicing, expense, payroll, and bank feed data locked inside it. Syncing this to a data warehouse unlocks financial analytics.
- **API:** REST API, OAuth 2.0, well-documented. Rate limited to 60 calls/minute.
- **Data to extract:** Invoices, contacts, bank transactions, accounts, payments, credit notes, purchase orders, journals, reports (P&L, balance sheet)
- **Use case:** "Sync your Xero invoicing and expense data to PostgreSQL. Build custom financial reports beyond what Xero's built-in reports offer."
- **API Docs:** https://developer.xero.com/

### 4. HMRC Making Tax Digital (MTD)
- **What it is:** The UK government's mandatory digital tax filing system. All VAT-registered businesses must submit VAT returns digitally.
- **Why it's unique:** No data integration platform connects to HMRC. This is entirely UK-specific. Every VAT-registered UK business (1.2M+) needs this.
- **API:** HMRC Developer Hub — REST APIs for VAT, Self Assessment, Corporation Tax.
- **Data to extract:** VAT returns, VAT obligations, VAT liabilities, VAT payments
- **Use case:** "Automatically sync your VAT submission history and obligations. Cross-reference with your accounting data to catch discrepancies."
- **Regulatory note:** Requires registration as an HMRC-recognized software vendor. This is a process but not prohibitive.
- **API Docs:** https://developer.service.hmrc.gov.uk/api-documentation

---

## Tier 2 — Build Within 6 Months

### 5. FreeAgent
- **What it is:** UK-based accounting software for freelancers and small businesses. Free for NatWest, RBS, and Ulster Bank customers (150,000+ users).
- **API:** REST API, OAuth 2.0
- **Data to extract:** Invoices, expenses, bank transactions, contacts, projects, timeslips, bills
- **API Docs:** https://dev.freeagent.com/

### 6. Sage Business Cloud
- **What it is:** One of the oldest and most trusted accounting platforms in the UK. Strong in traditional SMEs (trades, retail, professional services).
- **API:** REST API
- **Data to extract:** Contacts, invoices, purchase invoices, payments, bank accounts, tax rates, journals

### 7. Square (UK)
- **What it is:** POS and payment processing for retail and hospitality SMEs. Very popular in UK high-street businesses.
- **API:** REST API, well-documented
- **Data to extract:** Payments, orders, customers, inventory, locations, employees, cash drawer shifts

### 8. SumUp
- **What it is:** Mobile card reader and POS system. 4M+ merchants globally, very popular with UK micro-businesses (market stalls, food trucks, salons).
- **API:** REST API
- **Data to extract:** Transactions, receipts, merchant profile

### 9. Amazon Seller Central (UK)
- **What it is:** Amazon is the #1 ecommerce marketplace in the UK. Thousands of UK SMEs sell through Amazon.
- **API:** Amazon SP-API (Selling Partner API)
- **Data to extract:** Orders, inventory, financial events, FBA shipments, returns, product listings

### 10. Companies House API
- **What it is:** UK government registry of all companies. Free API access.
- **Why:** Enrich customer/supplier data with company registration details, filing history, director information.
- **API Docs:** https://developer.company-information.service.gov.uk/

---

## Tier 3 — Build in Year 2

### 11. Wise (TransferWise) Business
- International payments for UK businesses trading globally

### 12. Revolut Business
- Challenger bank popular with UK startups and SMEs

### 13. Tide Business Banking
- UK business banking with bookkeeping features

### 14. Deliveroo / Just Eat Partner APIs
- Restaurant and food delivery data for hospitality SMEs

### 15. Etsy Seller API
- Popular with UK craft and handmade goods sellers

---

## Connector Naming for Marketing

When presenting to the endorsing body, frame these as:

> "We are building the **UK Business Data Stack** — connecting GoCardless, Open Banking, Xero, HMRC, FreeAgent, Square, and Amazon Seller into a single data platform. No other tool does this."

This positions the product as uniquely valuable to UK SMEs and directly tied to the UK market — exactly what the endorsing body wants to see.

---

## Implementation Priority for Visa Application

Before applying for endorsement:
1. GoCardless connector (demonstrates UK-specific innovation)
2. Xero connector (most widely used UK accounting tool)
3. Open Banking connector (leverages UK's world-leading infrastructure)
4. HMRC MTD connector (UK regulatory requirement — very compelling)

These four connectors alone make a strong case that this business **must** be based in the UK to succeed.
