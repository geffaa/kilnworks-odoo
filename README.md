# Kilnworks on Odoo

Custom Odoo 18 Community modules for a **synthetic** stoneware maker, built as a portfolio of the work
Odoo clients ask for most: custom modules, integrations, payment providers, REST APIs, dashboards and
reports, and version migrations. Kilnworks Stoneware is made up; so is every customer, vendor and number.

> Demo build, not client work.

## Modules

| Module | What it shows | Status |
|---|---|---|
| `kw_ops` | The Kilnworks Ops app and role groups (user, production lead, owner) | done (M2) |
| `kw_demo` | Company in IDR with the Indonesian chart, four role-based users, 90 days of purchases, sales, deliveries and invoices, plus open approvals to demo | done (M1–M2) |
| `kw_approval` | PO approvals above Rp 10 M (production lead) and Rp 25 M (owner) and discount approvals above 10 % on OCA `base_tier_validation`; creators never approve their own documents; delegation with on-behalf audit; escalation after 24 working hours | done (M2) |
| `kw_shopify` | Shopify orders through HMAC-verified, idempotent webhooks processed by `queue_job`; debounced stock push over GraphQL; an OWL console where unmapped SKUs and failed cancellations are fixed and retried | done (M3, against a mock Shopify) |
| `payment_midtrans` | Midtrans Snap written from scratch on `payment.provider` (Midtrans is not in Odoo core): VA, QRIS, e-wallets and cards in IDR; SHA512-signed notifications checked for signature and amount; return page confirms status with the Status API | done (M4, against a mock Midtrans) |
| `kw_rest_api` | Scoped REST API with rate limiting and signed outgoing webhooks | planned (M5) |
| `kw_ops_dashboard`, `kw_reports` | OWL dashboard, export packing list and batch-aware delivery slip | planned (M5) |
| `kw_firing_batch` | A module written for 16.0 and migrated to 18.0, commit by commit | planned (M6) |

## Run it

Requirements: Docker with Compose.

```bash
git clone --recurse-submodules https://github.com/geffaa/kilnworks-odoo.git
cd kilnworks-odoo
make demo            # creates the "kilnworks" database and starts Odoo
open http://localhost:8069   # log in as ratna / ratna (owner), dimas, sekar or bayu
```

Port clash? `ODOO_PORT=8070 make demo`.

Shopify runs against a local mock (`shopify-mock` service), so the demo works offline:

```bash
python3 tools/mocks/send_order.py                         # signed orders/create webhook -> sale order
python3 tools/mocks/send_order.py --sku KW-MUG-350-SAGE   # unmapped SKU -> "Needs mapping" in the console
python3 tools/mocks/send_order.py --repeat                # same delivery twice -> stored once
MOCK_THROTTLE_EVERY=2 docker compose up -d shopify-mock   # make the mock answer 429 and watch jobs retry
```

Midtrans runs against a local mock too (`midtrans-mock`, payment page on localhost:8090, clearly marked as a mock).
`python3 tools/e2e_payment.py` opens the demo's unpaid invoice as a customer, pays it by BCA virtual account and
checks the invoice is paid.

## Develop

```bash
make test MOD=kw_demo   # install the module in a throwaway database and run its tests
make reset              # rebuild the demo database
make lint               # ruff, pylint-odoo, XML checks (pre-commit)
python3 tools/smoke.py  # log in as each user in a real browser, fail on console errors
```

OCA dependencies are pinned git submodules under `oca/` (branch 18.0): `server-ux`, `purchase-workflow`,
`sale-workflow`, `queue`.

## Docs

Product and technical plan: [BREAKDOWN.md](BREAKDOWN.md), [docs/](docs/). UI mockups: [mockups/](mockups/).
