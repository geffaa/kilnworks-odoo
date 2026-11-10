"""Seed the synthetic Kilnworks company.

Runs once on install. The random generator is seeded so every fresh database gets the
same 90 days of history, shifted to end on the install date.
"""

import logging
import random
from datetime import timedelta

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
    finally:
        rules.active = True
    _stock_levels(env, goods)
    _orderpoints(env, goods)
    _approval_showcase(env)
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
