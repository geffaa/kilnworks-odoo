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
| `kw_rest_api` | `/api/v1` with hashed, scoped, rotatable keys, 60 req/min limits and record rules applied; signed outgoing webhooks (`order.confirmed`, `stock.low`) with a 1 min → 6 h retry schedule; OpenAPI at `/api/v1/docs` | done (M5) |
| `kw_ops_dashboard`, `kw_reports` | OWL dashboard (approvals, sync failures, revenue by channel, low stock, invoices due) covered by a browser tour; export packing list per carton with HS codes and weights | done (M5) |
| `kw_firing_batch` | A module written for 16.0 and migrated to 18.0 in its own commit, with a data-keeping migration script and an OpenUpgrade 16 → 17 → 18 rehearsal ([notes](docs/MIGRATION-16-18.md)) | done (M6) |

## See it

[Walkthrough video (2½ min, English captions)](media/kilnworks-walkthrough.mp4). Recorded from the local demo with
`tools/capture.py` and `tools/make_media.sh`.

| Approvals | Shopify sync |
|---|---|
| ![Approval inbox and a purchase order waiting for the production lead](media/gif/approval.gif) | ![Unknown SKU mapped, order retried and imported](media/gif/shopify.gif) |
| **Midtrans payment** | **REST API** |
| ![Invoice paid by BCA virtual account through Midtrans](media/gif/payment.gif) | ![OpenAPI routes and a stock call with and without a key](media/gif/api.gif) |
| **Dashboard** | **16 → 18 migration** |
| ![Operations dashboard](media/gif/dashboard.gif) | ![Firing batches migrated from Odoo 16](media/gif/firing.gif) |

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

Try the API with the demo key (synthetic, local only):

```bash
curl -H "Authorization: Bearer kw_demo0001_UfT6pGQ2y0wq3m9hVbXk7cLr1sNaZ4eJ" "localhost:8069/api/v1/stock?sku=KW-PLT-270-SPK"
docker compose logs -f shopify-mock   # outgoing webhooks land here, signed, after you confirm an order
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

Case study: [docs/CASE-STUDY.md](docs/CASE-STUDY.md). Migration notes: [docs/MIGRATION-16-18.md](docs/MIGRATION-16-18.md).
Product and technical plan: [BREAKDOWN.md](BREAKDOWN.md), [docs/](docs/). UI mockups: [mockups/](mockups/).

## Licence

Each module declares its licence in `__manifest__.py`: LGPL-3, except `kw_approval` (AGPL-3, as it extends AGPL-3
OCA modules). OCA submodules keep their own licences.
