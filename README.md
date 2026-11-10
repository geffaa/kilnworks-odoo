# Kilnworks on Odoo

Custom Odoo 18 Community modules for a **synthetic** stoneware maker, built as a portfolio of the work
Odoo clients ask for most: custom modules, integrations, payment providers, REST APIs, dashboards and
reports, and version migrations. Kilnworks Stoneware is made up; so is every customer, vendor and number.

> Demo build, not client work.

## Modules

| Module | What it shows | Status |
|---|---|---|
| `kw_demo` | Company in IDR with the Indonesian chart, four role-based users, 90 days of purchases, sales, deliveries and invoices | done (M1) |
| `kw_approval` | Multi-level PO and discount approvals on top of OCA `base_tier_validation`, delegation, SLA escalation | planned (M2) |
| `kw_shopify` | Shopify orders and stock through signed webhooks and `queue_job`, with a sync log and retry | planned (M3) |
| `payment_midtrans` | A payment provider written from scratch on `payment.provider` | planned (M4) |
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
