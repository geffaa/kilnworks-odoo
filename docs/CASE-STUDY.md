# Case study: Kilnworks on Odoo

> Demo build, not client work. Kilnworks Stoneware, its customers, vendors and numbers are synthetic.

## The brief I set myself

Kilnworks is a small stoneware workshop in Kasongan, Yogyakarta. It sells mugs and plates abroad through Shopify
(USD) and to cafés and hotels at home on invoice (IDR), and buys clay, glaze and export cartons. Its problems are the
ones Odoo clients bring to freelancers:

- purchases and discounts go out without anyone signing off;
- Shopify orders are typed into the ERP by hand, and stock on the shop is wrong;
- local customers want to pay by virtual account or QRIS, which Odoo has no provider for;
- the café chain's app wants an API, not a CSV;
- the owner asks every Monday for numbers that live in five menus;
- one old module was written for Odoo 16 and blocks the upgrade.

Each problem became one module on Odoo 18 Community. The rule throughout: extend core and OCA, never rewrite them.

## What was built

| Problem | Module | Approach |
| --- | --- | --- |
| Approvals | `kw_approval` | On OCA `base_tier_validation`: PO tiers at Rp 10 M and Rp 25 M, discount approval above 10 %, no self-approval, delegation with an on-behalf audit trail, escalation after 24 working hours |
| Shopify | `kw_shopify` | HMAC-verified webhooks stored once and processed by `queue_job`; debounced stock push over GraphQL; an OWL console to map unknown SKUs and retry failures |
| Local payments | `payment_midtrans` | A `payment.provider` written from scratch for Midtrans Snap; notifications checked for signature and amount; the return page confirms with the Status API |
| API | `kw_rest_api` | `/api/v1` with hashed, scoped, rotatable keys, rate limits and record rules; signed outgoing webhooks retried from 1 minute to 6 hours; OpenAPI docs |
| Monday numbers | `kw_ops_dashboard`, `kw_reports` | OWL dashboard (approvals, sync failures, revenue by channel, low stock, invoices due); export packing list per carton with HS codes |
| Old module | `kw_firing_batch` | Written for 16.0, migrated to 18.0 in its own commit, with a script that renames a field without losing data and an OpenUpgrade rehearsal |

## Decisions worth explaining

- **OCA tier validation instead of a custom approval engine.** It is maintained, known by other Odoo developers and
  already handles locking. The custom work went into what it lacks: delegation, escalation, the self-approval rule.
- **Webhooks write an event row first, then a job processes it.** A Shopify retry of the same delivery hits the
  unique key and is counted, not imported twice. A failed job can be retried from the console without asking
  Shopify to resend.
- **Failed outgoing webhooks are rescheduled, not raised.** Raising a retryable error would roll back the record of
  the failed attempt, so the next attempt is scheduled explicitly and every try stays visible.
- **The payment return page asks Midtrans for the status.** The query string on the return URL can be edited by the
  customer, and notifications cannot reach a laptop, so the server confirms with the Status API.
- **Mocks for Shopify and Midtrans.** The whole demo runs offline with `make demo`, and the tests exercise real HTTP
  calls against them (signatures, 429 throttling, duplicate deliveries).

## Things that surprised me (and are now covered by tests)

- OCA numbers tiers from the highest definition `sequence`, so the owner tier needs the lower number.
- OCA rewrites the review status, which overwrote the "pending since" timestamp used for escalation.
- If `payment_midtrans` is installed before `account_payment`, its accounting payment method is never created.
- The Ubuntu `chromium` package is a snap stub, so Odoo browser tours were silently skipped until the image shipped
  Playwright's Chromium.
- The PyPI release of `openupgradelib` is too old for OpenUpgrade 18.0; it has to come from git.

## Quality

- About 90 automated tests across the modules, including HTTP-level webhook tests and a browser tour of the dashboard.
- Every module installs on a fresh database with `make test MOD=<module>`; CI runs the same image.
- `tools/smoke.py` logs in as each demo role in a real browser and fails on any console error.
- Lint: ruff, pylint-odoo, XML checks via pre-commit.

## Migration result

See [MIGRATION-16-18.md](MIGRATION-16-18.md). _Final 18.0 rehearsal numbers to be added._

## What I would do next for a real client

Run the Shopify connector against a real development store (API version and inventory arguments still need that
check), import Shopify shipping and tax lines, add a B2B portal, and configure Odoo's built-in Coretax e-Faktur
export for Indonesian tax.
