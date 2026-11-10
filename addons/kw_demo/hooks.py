"""Seed the synthetic Kilnworks company.

Runs once on install. The random generator is seeded so every fresh database gets the
same 90 days of history, shifted to end on the install date.
"""

import base64
import logging
import random
from datetime import timedelta
from pathlib import Path

from odoo import Command, fields

_logger = logging.getLogger(__name__)

SEED_FLAG = "kw_demo.seeded"

# On-hand quantity and minimum after seeding: the dashboard's "below minimum" block.
STOCK_TARGETS = {
    "KW-MUG-350-CEL": (42, 120),
    "KW-PLT-270-SPK": (18, 80),
    "KW-BWL-900-ASH": (9, 60),
    "KW-ESP-090-SND": (64, 150),
    "KW-DRP-002-IRR": (11, 40),
}
DEFAULT_ON_HAND, DEFAULT_MIN = 220, 60

RAW_PURCHASES = [
    # sku, qty range per order
    ("RM-CLAY-GDN", (1200, 2600)),
    ("RM-GLZ-CEL", (30, 70)),
    ("RM-GLZ-ASH", (20, 50)),
    ("RM-OXD-IRN", (10, 25)),
    ("RM-CTN-5PLY", (200, 500)),
    ("RM-LPG-50", (4, 10)),
]
PO_COUNT, SO_COUNT = 14, 26


def post_init_hook(env):
    icp = env["ir.config_parameter"].sudo()
    if icp.get_param(SEED_FLAG):
        _logger.info("Kilnworks demo data already seeded, skipping")
        return
    _setup_company(env)
    registry = env.registry
    if not registry.loaded:
        # Charts must load on a complete registry. `account` runs the hook below at the end of
        # module loading (and may have queued the generic chart there); take that slot so the
        # Indonesian chart is loaded instead and the data is seeded right after.
        def load_and_seed(final_env):
            _load_chart(final_env)
            _seed(final_env)

        registry._auto_install_template = load_and_seed
    else:
        _load_chart(env)
        _seed(env)


def _seed(env):
    rng = random.Random(20261110)
    env = env(context=dict(env.context, tracking_disable=True, mail_notrack=True))
    _numbering(env)
    goods = _products(env, "KW-")
    # Products were created before the chart existed, so they carry no default taxes yet.
    company = env.ref("base.main_company")
    goods.product_tmpl_id.taxes_id = company.account_sale_tax_id
    _products(env, "RM-").product_tmpl_id.supplier_taxes_id = False
    _stock_levels(env, goods, base=1000)
    # The 90 days of history predate the approval rules. OCA has no bypass for state changes,
    # so the rules are switched off while the history is written.
    rules = env["tier.definition"].search([])
    rules.active = False
    try:
        _purchases(env, rng)
        _sales(env, rng, goods)
        _shopify(env, rng)
    finally:
        rules.active = True
    _stock_levels(env, goods)
    _orderpoints(env, goods)
    _approval_showcase(env)
    _midtrans(env)
    env["ir.config_parameter"].sudo().set_param(SEED_FLAG, fields.Datetime.now())
    _logger.info("Kilnworks demo data seeded")


def _setup_company(env):
    company = env.ref("base.main_company")
    idr = env.ref("base.IDR")
    idr.active = True
    company.write(
        {
            "name": "Kilnworks Stoneware",
            "street": "Jl. Kasongan 41",
            "city": "Bantul",
            "zip": "55184",
            "country_id": env.ref("base.id").id,
            "currency_id": idr.id,
            "email": "hello@kilnworks.example",
            "website": "https://kilnworks.example",
            "logo": base64.b64encode(
                (Path(__file__).parent / "static/description/logo.png").read_bytes()
            ),
        }
    )
    env.ref("base.partner_admin").tz = "Asia/Jakarta"
    # The default pricelist was created in USD before the company switched currency.
    env["product.pricelist"].search([("currency_id", "!=", idr.id)]).write({"currency_id": idr.id})
    return company


def _load_chart(env):
    # Switching away from the generic chart is allowed while no journal entries exist.
    company = env.ref("base.main_company")
    if company.chart_template != "id":
        env["account.chart.template"].try_loading("id", company=company, install_demo=False)


def _products(env, prefix):
    return env["product.product"].search(
        [("default_code", "=like", prefix + "%")], order="default_code"
    )


def _by_sku(env, sku):
    return env["product.product"].search([("default_code", "=", sku)], limit=1)


def _stock_levels(env, products, base=None):
    """Set absolute on-hand quantities with an inventory adjustment."""
    location = env.ref("stock.warehouse0").lot_stock_id
    Quant = env["stock.quant"].with_context(inventory_mode=True)
    for product in products:
        qty = (
            base
            if base is not None
            else STOCK_TARGETS.get(product.default_code, (DEFAULT_ON_HAND,))[0]
        )
        quant = Quant.search(
            [("product_id", "=", product.id), ("location_id", "=", location.id)], limit=1
        )
        if not quant:
            quant = Quant.create({"product_id": product.id, "location_id": location.id})
        quant.inventory_quantity = qty
        quant.action_apply_inventory()


def _orderpoints(env, products):
    warehouse = env.ref("stock.warehouse0")
    for product in products:
        minimum = STOCK_TARGETS.get(product.default_code, (0, DEFAULT_MIN))[1]
        env["stock.warehouse.orderpoint"].create(
            {
                "product_id": product.id,
                "warehouse_id": warehouse.id,
                "location_id": warehouse.lot_stock_id.id,
                "product_min_qty": minimum,
                "product_max_qty": minimum * 3,
                "trigger": "manual",
            }
        )


def _validate_picking(picking, when):
    for move in picking.move_ids:
        move.quantity = move.product_uom_qty
        move.picked = True
    picking.button_validate()
    picking.date_done = when


def _purchases(env, rng):
    today = fields.Datetime.now()
    dimas = env.ref("kw_demo.user_dimas")
    for i in range(PO_COUNT):
        days_ago = int(90 - i * (86 / PO_COUNT)) - rng.randint(0, 3)
        when = today - timedelta(days=max(days_ago, 4))
        picks = rng.sample(RAW_PURCHASES, rng.randint(1, 3))
        vendor = _by_sku(env, picks[0][0]).seller_ids[:1].partner_id
        lines = []
        for sku, (lo, hi) in picks:
            product = _by_sku(env, sku)
            # One vendor per order: keep only products this vendor sells.
            if product.seller_ids[:1].partner_id != vendor:
                continue
            step = 50 if hi > 500 else 5 if hi > 20 else 1
            lines.append(
                Command.create(
                    {
                        "product_id": product.id,
                        "product_qty": rng.randrange(lo, hi + 1, step),
                        "price_unit": product.seller_ids[:1].price,
                        "taxes_id": [Command.clear()],  # vendors are not VAT-registered
                    }
                )
            )
        po = (
            env["purchase.order"]
            .with_user(dimas)
            .create({"partner_id": vendor.id, "user_id": dimas.id, "order_line": lines})
        )
        po = po.sudo()
        po.button_confirm()
        po.write({"date_order": when, "date_approve": when})
        for picking in po.picking_ids:
            _validate_picking(picking, when + timedelta(days=3))


def _sales(env, rng, goods):
    today = fields.Datetime.now()
    sekar = env.ref("kw_demo.user_sekar")
    customers = env["res.partner"].search([("category_id", "in", env.ref("kw_demo.tag_b2b").ids)])
    journal = env["account.journal"].search(
        [("type", "=", "bank"), ("company_id", "=", env.company.id)], limit=1
    )
    for i in range(SO_COUNT):
        days_ago = int(88 - i * (86 / SO_COUNT))
        when = today - timedelta(days=max(days_ago, 0), hours=rng.randint(0, 6))
        lines = [
            Command.create(
                {
                    "product_id": product.id,
                    "product_uom_qty": rng.choice([12, 24, 36, 48, 60, 120]),
                    "discount": rng.choice([0, 0, 0, 5, 7.5, 10]),
                }
            )
            for product in rng.sample(list(goods), rng.randint(2, 4))
        ]
        so = (
            env["sale.order"]
            .with_user(sekar)
            .create(
                {"partner_id": rng.choice(customers).id, "user_id": sekar.id, "order_line": lines}
            )
            .sudo()
        )
        if i >= SO_COUNT - 3:
            so.date_order = when  # the three newest stay quotations
            continue
        so.action_confirm()
        so.date_order = when
        if days_ago < 5:
            continue
        for picking in so.picking_ids:
            _validate_picking(picking, when + timedelta(days=2))
        invoice = so._create_invoices()
        invoice.invoice_date = (when + timedelta(days=2)).date()
        invoice.action_post()
        # Older invoices are paid; the last few stay open for the dashboard.
        if days_ago > 20 and rng.random() < 0.85:
            env["account.payment.register"].with_context(
                active_model="account.move", active_ids=invoice.ids
            ).create(
                {
                    "journal_id": journal.id,
                    "payment_date": invoice.invoice_date + timedelta(days=12),
                }
            )._create_payments()


def _numbering(env):
    """Year-based numbers such as PO/2026/0418 instead of P00018."""
    for xmlid, prefix, start in (
        ("purchase.seq_purchase_order", "PO/%(year)s/", 404),
        ("sale.seq_sale_order", "S/%(year)s/", 1158),
    ):
        seq = env.ref(xmlid)
        seq.write({"prefix": prefix, "padding": 4, "number_next": start})


def _approval_showcase(env):
    """The approvals the demo opens on: one escalated two-tier PO, one discount, one small PO."""
    now = fields.Datetime.now()
    ratna = env.ref("kw_demo.user_ratna")
    dimas = env.ref("kw_demo.user_dimas")
    sekar = env.ref("kw_demo.user_sekar")
    today = fields.Date.context_today(env["res.users"].with_user(ratna))
    env["kw.approval.delegation"].create(
        {
            "delegator_id": ratna.id,
            "delegate_id": sekar.id,
            "date_from": today,
            "date_to": today + timedelta(days=4),
            "reason": "Trade fair in Jakarta",
        }
    )

    def po_line(sku, qty, price=None):
        product = _by_sku(env, sku)
        return Command.create(
            {
                "product_id": product.id,
                "product_qty": qty,
                "price_unit": price or product.seller_ids[:1].price,
                "taxes_id": [Command.clear()],
            }
        )

    clay_po = (
        env["purchase.order"]
        .with_user(dimas)
        .create(
            {
                "partner_id": env.ref("kw_demo.v_lempung").id,
                "partner_ref": "SLG/INV/11-026",
                "order_line": [
                    po_line("RM-CLAY-GDN", 2400),
                    po_line("RM-GLZ-CEL", 60),
                    po_line("RM-CTN-5PLY", 400),
                ],
            }
        )
    )
    # A note Dimas typed, not an interface string: no translation.
    clay_po.message_post(  # pylint: disable=translation-required
        body="Clay for the December glaze run. Price is up Rp 500/kg from October, "
        "still below Bantul suppliers.",
        author_id=dimas.partner_id.id,
        message_type="comment",
        subtype_xmlid="mail.mt_note",
    )
    clay_po.with_user(dimas).request_validation()
    tier1 = clay_po.review_ids.sorted("sequence")[:1]
    tier1.sudo().kw_pending_since = now - timedelta(hours=26)
    tier1.sudo()._kw_escalate(now - timedelta(minutes=40))

    glaze_po = (
        env["purchase.order"]
        .with_user(dimas)
        .create(
            {
                "partner_id": env.ref("kw_demo.v_glasir").id,
                "order_line": [po_line("RM-GLZ-CEL", 60), po_line("RM-GLZ-ASH", 50)],
            }
        )
    )
    glaze_po.with_user(dimas).request_validation()
    glaze_po.review_ids.sudo().kw_pending_since = now - timedelta(hours=2)

    mug = _by_sku(env, "KW-MUG-350-CEL")
    quote = (
        env["sale.order"]
        .with_user(sekar)
        .create(
            {
                "partner_id": env.ref("kw_demo.c_teras").id,
                "user_id": sekar.id,
                "order_line": [
                    Command.create({"product_id": mug.id, "product_uom_qty": 120, "discount": 15})
                ],
            }
        )
    )
    quote.with_user(sekar).request_validation()
    quote.review_ids.sudo().kw_pending_since = now - timedelta(hours=5)


# -- Shopify ------------------------------------------------------------------------------
DEMO_WEBHOOK_SECRET = "kilnworks-demo-webhook-secret"  # public: synthetic demo only
USD_PER_IDR = 1 / 16250  # synthetic demo rate, not a market quote
SHOPIFY_PRICES = {  # USD
    "KW-MUG-350-CEL": 24,
    "KW-MUG-350-ASH": 24,
    "KW-MUG-250-SND": 21,
    "KW-ESP-090-SND": 14,
    "KW-ESP-090-CEL": 14,
    "KW-CUP-200-IRR": 19,
    "KW-SAU-140-IRR": 11,
    "KW-PLT-270-SPK": 34,
    "KW-PLT-210-SPK": 22,
    "KW-PLT-270-CEL": 36,
    "KW-BWL-900-ASH": 32,
    "KW-BWL-500-CEL": 19,
    "KW-BWL-150-SND": 10,
    "KW-DRP-002-IRR": 42,
    "KW-SRV-001-CEL": 38,
    "KW-TPT-800-ASH": 64,
    "KW-VAS-180-SPK": 28,
    "KW-SET-4PC-CEL": 89,
}
BUYERS = [
    ("Maya", "Okafor", "Wellington", "NZ"),
    ("Lena", "Vogel", "Hamburg", "DE"),
    ("Tom", "Hartley", "Bristol", "GB"),
    ("Aiko", "Tanaka", "Fukuoka", "JP"),
    ("Priya", "Raman", "Singapore", "SG"),
    ("Jonas", "de Wit", "Utrecht", "NL"),
    ("Claire", "Dubois", "Montréal", "CA"),
    ("Sam", "Whitfield", "Portland", "US"),
    ("Noor", "Haddad", "Melbourne", "AU"),
    ("Ellis", "Moreno", "Austin", "US"),
    ("Hana", "Kim", "Vancouver", "CA"),
    ("Olivia", "Brandt", "Copenhagen", "DK"),
]
SHOPIFY_ORDERS = 40  # #KW1005 … #KW1044 over 30 days


def _shopify(env, rng):
    company = env.ref("base.main_company")
    usd = env.ref("base.USD")
    usd.active = True
    env["res.currency.rate"].create(
        {
            "currency_id": usd.id,
            "company_id": company.id,
            "rate": USD_PER_IDR,
            "name": fields.Date.today() - timedelta(days=120),
        }
    )
    pricelist = env["product.pricelist"].create({"name": "Shopify (USD)", "currency_id": usd.id})
    store = env["kw.shopify.store"].create(
        {
            "name": "Kilnworks Studio",
            "shop_domain": "kilnworks-studio.myshopify.com",
            "api_version": "2025-10",
            "api_base_url": "http://shopify-mock:8080",
            "access_token": "shpat_demo_not_a_real_token",
            "webhook_secret": DEMO_WEBHOOK_SECRET,
            "location_gid": "gid://shopify/Location/71522431",
            "warehouse_id": env.ref("stock.warehouse0").id,
            "pricelist_id": pricelist.id,
            "salesperson_id": env.ref("kw_demo.user_bayu").id,
        }
    )
    env["ir.model.data"].create(
        {
            "module": "kw_demo",
            "name": "shopify_store",
            "model": store._name,
            "res_id": store.id,
            "noupdate": True,
        }
    )
    for i, sku in enumerate(SHOPIFY_PRICES, start=1):
        env["kw.shopify.product.map"].create(
            {
                "store_id": store.id,
                "product_id": _by_sku(env, sku).id,
                "sku": sku,
                "variant_gid": f"gid://shopify/ProductVariant/4419{i:04d}",
                "inventory_item_gid": f"gid://shopify/InventoryItem/5520{i:04d}",
            }
        )
    now = fields.Datetime.now()
    skus = list(SHOPIFY_PRICES)
    events = env["kw.shopify.event"]
    for i in range(SHOPIFY_ORDERS):
        number = 1005 + i
        # Spread over 30 days; the last eight land in the past 24 hours.
        hours_ago = (
            (SHOPIFY_ORDERS - 1 - i) * 2.4 if i >= SHOPIFY_ORDERS - 8 else (30 - i * 0.75) * 24
        )
        when = now - timedelta(hours=hours_ago)
        first, last, city, country = BUYERS[i % len(BUYERS)]
        items = []
        for sku in rng.sample(skus, rng.randint(1, 3)):
            items.append(
                {
                    "sku": sku,
                    "quantity": rng.choice([1, 2, 2, 4, 6]),
                    "price": f"{SHOPIFY_PRICES[sku]:.2f}",
                    "discount_allocations": [],
                }
            )
        if number == 1043:
            items[0]["sku"] = "KW-MUG-350-SAGE"  # added in Shopify yesterday, not mapped yet
        total = sum(float(it["price"]) * it["quantity"] for it in items)
        gid = f"gid://shopify/Order/58{number:08d}"
        payload = {
            "id": int(f"58{number:08d}"),
            "admin_graphql_api_id": gid,
            "name": f"#KW{number}",
            "email": f"{first.lower()}.{last.lower().replace(' ', '')}@example.com",
            "currency": "USD",
            "total_price": f"{total:.2f}",
            "created_at": when.isoformat(),
            "customer": {
                "first_name": first,
                "last_name": last,
                "email": f"{first.lower()}.{last.lower().replace(' ', '')}@example.com",
            },
            "shipping_address": {"city": city, "country_code": country},
            "line_items": items,
        }
        event = events.create(
            {
                "store_id": store.id,
                "webhook_id": f"b54557e4-{number:04d}-4b37-8a5f-bf7d70bcd043",
                "topic": "orders/create",
                "order_name": payload["name"],
                "order_gid": gid,
                "payload": payload,
                "received_at": when,
            }
        )
        event.log = [
            [when.isoformat(), "Received, signature checked, stored"],
            [when.isoformat(), "Queued on channel root.kw_shopify"],
        ]
        event.process()
        event.processed_at = when + timedelta(seconds=2)
        order = event.sale_order_id
        if order:
            order.date_order = when
            if hours_ago > 48:
                for picking in order.picking_ids:
                    _validate_picking(picking, when + timedelta(days=1))
    # A customer cancelled #KW1031 after it had shipped: a person has to arrange the return.
    shipped = events.search([("order_name", "=", "#KW1031")]).payload
    cancel = events.create(
        {
            "store_id": store.id,
            "webhook_id": "c0a8b3f2-1031-4e1c-9d2e-7a7f1b2c1031",
            "topic": "orders/cancelled",
            "order_name": "#KW1031",
            "order_gid": shipped["admin_graphql_api_id"],
            "payload": dict(
                shipped,
                cancelled_at=(now - timedelta(hours=6)).isoformat(),
                cancel_reason="customer",
            ),
            "received_at": now - timedelta(hours=6),
        }
    )
    cancel.process()
    # Shopify retried two deliveries we had already stored.
    events.search([("order_name", "in", ("#KW1041", "#KW1042"))]).write(
        {"duplicate_count": 1, "last_duplicate_at": now - timedelta(hours=1)}
    )
    store.write(
        {"last_stock_push_at": now - timedelta(minutes=20), "last_stock_push_count": len(skus)}
    )


# -- Midtrans -----------------------------------------------------------------------------
DEMO_MIDTRANS_SERVER_KEY = "SB-Mid-server-kilnworks-demo"  # matches tools/mocks; demo only


def _midtrans(env):
    """Midtrans in test mode against the local mock, and one open invoice to pay."""
    icp = env["ir.config_parameter"].sudo()
    icp.set_param("web.base.url", "http://localhost:8069")
    icp.set_param("web.base.url.freeze", "True")
    # payment_midtrans installed before account_payment, so its accounting payment method was
    # never created; run the setup again now that account_payment is present.
    env["payment.provider"]._setup_provider("midtrans")
    provider = env.ref("payment_midtrans.payment_provider_midtrans")
    provider.write(
        {
            "state": "test",
            "is_published": True,
            "company_id": env.ref("base.main_company").id,
            "midtrans_merchant_id": "G000000000",
            "midtrans_client_key": "SB-Mid-client-kilnworks-demo",
            "midtrans_server_key": DEMO_MIDTRANS_SERVER_KEY,
            "midtrans_snap_url_override": "http://midtrans-mock:8090",
            "midtrans_api_url_override": "http://midtrans-mock:8090",
            # account_payment links a journal only to providers that exist when it installs;
            # payments need it (and the payment method line it creates) to post.
            "journal_id": env["account.journal"]
            .search(
                [("type", "=", "bank"), ("company_id", "=", env.ref("base.main_company").id)],
                limit=1,
            )
            .id,
        }
    )
    # Without an outstanding-receipts account Odoo 18 leaves the payment "in process" with no
    # journal entry, so it cannot be matched to the invoice until bank reconciliation.
    company = env.ref("base.main_company")
    outstanding = env["account.account"].create(
        {
            "name": "Outstanding Receipts (Midtrans)",
            "code": "112901",
            "account_type": "asset_current",
            "reconcile": True,
            "company_ids": [(6, 0, company.ids)],
        }
    )
    env["account.payment.method.line"].search([("payment_provider_id", "=", provider.id)]).write(
        {"payment_account_id": outstanding.id}
    )
    invoice = env["account.move"].search(
        [
            ("move_type", "=", "out_invoice"),
            ("payment_state", "=", "not_paid"),
            ("state", "=", "posted"),
        ],
        order="invoice_date desc",
        limit=1,
    )
    if invoice:
        invoice._portal_ensure_token()
        icp.set_param("kw_demo.payment_link", invoice.get_base_url() + invoice._get_share_url())
