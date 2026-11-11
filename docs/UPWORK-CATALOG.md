# Upwork Project Catalog drafts

Six catalogs, one per module. Each is ready to paste: title (under 75 characters), description,
three packages, requirements and FAQ. Prices are a starting point to adjust; delivery days assume part-time work.

Proof for every catalog: public repo `github.com/geffaa/kilnworks-odoo` (the module folder), its tests in CI,
a 20–30 second GIF (`media/gif/<scene>.gif`: approval, shopify, payment, api, dashboard, firing) and the walkthrough video (`media/kilnworks-walkthrough.mp4`). Every catalog says plainly that Kilnworks is a demo build with synthetic data.

Shared line for the end of each description:

> Proof of work: Kilnworks on Odoo, my open demo build (synthetic company, not client work). Browse the module's
> code and tests on GitHub, or log in to the live demo before you order.

---

## 1. Custom module with approvals

**Title:** I will build a custom Odoo 18 module with multi-level approvals

**Category:** Development & IT › ERP / CRM Software

**Description**

Need purchase orders, discounts or your own documents approved before they move on? I build approval flows on
top of OCA tier validation, the standard community engine, instead of a custom engine you would have to maintain.

What you get:
- Approval rules by amount, discount, team or any field (e.g. POs above Rp 10 M to the production lead, above Rp 25 M to the owner)
- No self-approval: the person who created a document cannot approve it
- Delegation while an approver is away, with an "approved on behalf of" audit trail
- Reminders and escalation when a request waits too long (e.g. 24 working hours)
- An approval inbox, activity notifications, tests for each rule

Works on Odoo 16–18, Community or Enterprise, Odoo.sh or self-hosted.

| | Basic | Standard | Premium |
| --- | --- | --- | --- |
| Name | One approval rule | Approval flow | Approval suite |
| Scope | 1 document type, up to 2 levels | Up to 2 document types, 3 levels, no self-approval | Up to 4 document types, delegation, SLA escalation, approval inbox |
| Tests | ✓ | ✓ | ✓ |
| Delivery | 3 days | 6 days | 10 days |
| Revisions | 1 | 2 | 3 |
| Price | $90 | $220 | $450 |

**Requirements from buyer:** Odoo version and edition, hosting (Odoo.sh / own server), the documents and amounts to
approve, who approves at each level, a staging database or access to create one.

**FAQ**
- *Do you modify core Odoo files?* No. Everything is a separate module that extends core and OCA, so upgrades stay possible.
- *Can it work on my own model?* Yes. Any model with a state can get tier validation.
- *Enterprise?* Yes. The module depends only on Community modules, so it runs on both.

---

## 2. Shopify integration

**Title:** I will integrate Shopify with Odoo: orders, stock sync and webhooks

**Description**

Shopify orders appear in Odoo as sale orders within seconds, and Odoo stock levels are pushed back to Shopify.
Built with webhooks and a job queue, so nothing is lost when either side is slow or down.

What you get:
- Shopify orders, customers and cancellations imported through HMAC-verified webhooks (duplicates are ignored)
- Stock pushed to Shopify through the GraphQL Admin API, batched so rate limits are respected
- SKU mapping, with orders for unmapped products held in a "needs mapping" list instead of failing silently
- A sync log where failed jobs can be seen and retried in one click
- Multi-currency: shop in USD, accounting in your currency

| | Basic | Standard | Premium |
| --- | --- | --- | --- |
| Name | Orders in | Two-way sync | Full connector |
| Scope | Orders → sale orders via webhooks | + stock push, SKU mapping, sync log | + cancellations/refunds, multi-currency, retry console, fulfilment status back to Shopify |
| Tests | ✓ | ✓ | ✓ |
| Delivery | 4 days | 8 days | 14 days |
| Revisions | 1 | 2 | 3 |
| Price | $150 | $350 | $700 |

**Requirements from buyer:** Odoo version and hosting, Shopify store with a custom app (I can guide you), product
SKU list, which warehouse feeds Shopify stock.

**FAQ**
- *Why not an Apps Store connector?* Those work for standard cases. Choose this when you need your own rules,
  readable code you own, or a fix for a connector that loses orders.
- *Does it need a public URL?* Yes, Shopify webhooks need Odoo reachable over HTTPS (Odoo.sh is fine).

---

## 3. Payment gateway

**Title:** I will add a custom payment gateway to Odoo (Midtrans, Xendit, any REST API)

**Description**

Your gateway is not in Odoo? I write the payment provider so customers pay invoices and website orders through
it, with the same flow as Odoo's built-in Stripe or PayPal.

What you get:
- A payment provider module on Odoo's `payment.provider` framework (portal invoices, website checkout, payment links)
- Redirect or hosted payment page, with the methods your gateway supports (VA, QRIS, e-wallets, cards…)
- Server-to-server notifications checked for signature and amount before an invoice is marked paid
- Status check on the return page, refunds if the gateway supports them
- Sandbox testing end to end, then a go-live checklist

Example in the demo: Midtrans Snap (Indonesia), which Odoo does not include.

| | Basic | Standard | Premium |
| --- | --- | --- | --- |
| Name | Pay by link | Full provider | Provider + refunds |
| Scope | Redirect payment, notifications, invoice marked paid | + portal and website checkout, status check, multiple methods | + refunds, partial payments, tokenised cards if supported, reconciliation report |
| Tests | ✓ | ✓ | ✓ |
| Delivery | 5 days | 9 days | 14 days |
| Revisions | 1 | 2 | 3 |
| Price | $180 | $400 | $750 |

**Requirements from buyer:** gateway name and API docs, sandbox credentials, Odoo version and hosting, which
flows you need (invoice, website, both).

**FAQ**
- *Stripe or PayPal?* They are already in Odoo core; I can configure them, no custom module needed.
- *Is card data stored in Odoo?* No. Card entry happens on the gateway's page.

---

## 4. REST API and webhooks

**Title:** I will build a REST API and webhooks for your Odoo (mobile app, website)

**Description**

Your mobile app, website or partner system needs clean JSON endpoints instead of XML-RPC. I add a versioned
REST API to Odoo with proper keys, scopes and documentation, plus outgoing webhooks so other systems hear about
changes immediately.

What you get:
- `/api/v1` endpoints for the resources you need (products, stock, orders, partners…), with pagination and filters
- API keys stored as hashes, with scopes, rotation, expiry and per-key rate limits
- Odoo access rights and record rules still apply to every call
- Signed outgoing webhooks (e.g. `order.confirmed`, `stock.low`) with retries over hours
- OpenAPI documentation and a Postman collection

| | Basic | Standard | Premium |
| --- | --- | --- | --- |
| Name | Read API | Read + write API | API + webhooks |
| Scope | Up to 3 read endpoints, API keys | Up to 6 endpoints incl. create/update, scopes, rate limits, OpenAPI | + signed webhooks with retries, key rotation, Postman collection |
| Tests | ✓ | ✓ | ✓ |
| Delivery | 3 days | 7 days | 12 days |
| Revisions | 1 | 2 | 3 |
| Price | $120 | $300 | $600 |

**Requirements from buyer:** Odoo version and hosting, the client that will call the API, list of data and actions needed.

**FAQ**
- *Why not Odoo's built-in JSON-RPC?* It works, but exposes the whole ORM to anyone with a password. A REST layer
  limits each key to what it should do and is easier for app developers.

---

## 5. Dashboards and reports

**Title:** I will build Odoo dashboards and custom PDF reports (OWL, QWeb)

**Description**

Stop exporting to Excel every Monday. I build dashboards inside Odoo that show the numbers your team checks every
day, and PDF reports that look the way your customers and couriers expect.

What you get:
- An OWL dashboard: KPI tiles, charts, lists that open the underlying records, period comparison
- Works in Odoo Community (no Enterprise spreadsheet needed)
- QWeb PDF reports: invoices, delivery slips, packing lists with HS codes and carton weights, certificates…
- Fast queries (read_group, not loops), checked on large data sets
- Tests, including a browser test for the dashboard

| | Basic | Standard | Premium |
| --- | --- | --- | --- |
| Name | One report | Dashboard | Dashboard + reports |
| Scope | 1 QWeb PDF report or report redesign | OWL dashboard with up to 6 KPIs/charts | Dashboard up to 10 widgets + 2 PDF reports |
| Tests | ✓ | ✓ | ✓ |
| Delivery | 3 days | 6 days | 10 days |
| Revisions | 2 | 2 | 3 |
| Price | $80 | $250 | $480 |

**Requirements from buyer:** Odoo version, the KPIs or report layout you want (a sketch or Excel sample is enough), sample data or staging access.

---

## 6. Version migration

**Title:** I will migrate your custom Odoo modules to Odoo 18

**Description**

Stuck on Odoo 14, 15, 16 or 17 because of custom modules? I port them to Odoo 18 and write the migration scripts
that keep your data, then rehearse the full database upgrade before your go-live.

What you get:
- Custom modules ported to 18: views (attrs/states → expressions, tree → list), Python API changes, OWL components
- Migration scripts for renamed fields and changed data, so history is kept
- A full upgrade rehearsal on a copy of your database (OpenUpgrade for Community, or the Odoo upgrade service for Enterprise)
- A report of what changed, what was checked and what to watch on go-live day
- Tests passing on 18

Example in the demo: a module written for Odoo 16, migrated to 18 in separate commits, upgraded from a 16.0
database through 17 to 18 with its data checked.

| | Basic | Standard | Premium |
| --- | --- | --- | --- |
| Name | Port one module | Port + data migration | Full upgrade rehearsal |
| Scope | 1 small module ported to 18 (code only) | Up to 3 modules + migration scripts | Up to 6 modules + full database rehearsal + go-live report |
| Tests | ✓ | ✓ | ✓ |
| Delivery | 3 days | 8 days | 15 days |
| Revisions | 1 | 2 | 2 |
| Price | $100 | $350 | $800 |

**Requirements from buyer:** module source code, current and target versions, a recent database copy (anonymised
is fine) for the data steps, list of third-party modules used.

**FAQ**
- *Do you migrate Enterprise databases?* The database itself goes through Odoo's upgrade service; I port your
  custom modules and write their scripts so they pass that upgrade.
- *How big is "small"?* Roughly up to 5 models and 10 views. Larger modules get a fixed quote after a code review.
