import logging

from odoo import Command, api, fields, models
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

SUPPORTED_TOPICS = ("orders/create", "orders/cancelled")


class KwShopifyEvent(models.Model):
    _name = "kw.shopify.event"
    _description = "Shopify webhook event"
    _order = "received_at desc, id desc"
    _rec_name = "order_name"

    ATTENTION = ("needs_mapping", "failed", "queued")

    store_id = fields.Many2one("kw.shopify.store", required=True, ondelete="cascade", index=True)
    webhook_id = fields.Char(
        required=True, help="X-Shopify-Webhook-Id: one per delivery attempt group"
    )
    topic = fields.Char(required=True)
    order_name = fields.Char(string="Order", help="Shopify's order name, e.g. #KW1043")
    order_gid = fields.Char(string="Order GID")
    payload = fields.Json(required=True)
    state = fields.Selection(
        [
            ("queued", "Queued"),
            ("done", "Done"),
            ("needs_mapping", "Needs mapping"),
            ("failed", "Failed"),
            ("ignored", "Ignored"),
        ],
        default="queued",
        required=True,
        index=True,
    )
    error = fields.Text()
    missing_skus = fields.Char(help="Comma-separated SKUs with no Odoo product")
    can_retry = fields.Boolean(compute="_compute_can_retry")
    sale_order_id = fields.Many2one("sale.order", readonly=True)
    attempts = fields.Integer(readonly=True)
    duplicate_count = fields.Integer(readonly=True, help="Repeat deliveries ignored by webhook ID")
    last_duplicate_at = fields.Datetime(readonly=True)
    received_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    processed_at = fields.Datetime(readonly=True)
    log = fields.Json(default=list, help="[[iso time, message], …]")

    _sql_constraints = [
        ("webhook_uniq", "unique(store_id, webhook_id)", "This webhook delivery is already stored.")
    ]

    @api.depends("state", "missing_skus")
    def _compute_can_retry(self):
        for event in self:
            if event.state == "failed":
                event.can_retry = True
            elif event.state == "needs_mapping":
                event.can_retry = not event._unmapped_skus(event._skus())
            else:
                event.can_retry = False

    def _log(self, message):
        for event in self:
            event.log = (event.log or []) + [[fields.Datetime.now().isoformat(), message]]

    # -- processing -----------------------------------------------------------------
    def _enqueue(self):
        for event in self:
            event.state = "queued"
            event.with_delay(
                channel="root.kw_shopify",
                description=f"Shopify {event.topic} {event.order_name or ''}".strip(),
            ).process()
            event._log("Queued on channel root.kw_shopify")

    def process(self):
        """Job entry point. Never leaves half an order behind: lines are resolved first."""
        self.ensure_one()
        if self.state == "done":
            return "already done"
        self.attempts += 1
        handler = {
            "orders/create": self._process_order_create,
            "orders/cancelled": self._process_order_cancelled,
        }.get(self.topic)
        if not handler:
            self.state = "ignored"
            return "ignored"
        try:
            with self.env.cr.savepoint():
                result = handler()
        except UserError as exc:
            # Link the order when there is one: the person fixing this needs to open it.
            self.write(
                {"state": "failed", "error": str(exc), "sale_order_id": self._find_order().id}
            )
            self._log(f"Failed: {exc}")
            return "failed"
        self.processed_at = fields.Datetime.now()
        return result

    def _skus(self):
        return [line.get("sku") or "" for line in (self.payload or {}).get("line_items", [])]

    def _unmapped_skus(self, skus):
        mapped = set(
            self.env["kw.shopify.product.map"]
            .search([("store_id", "=", self.store_id.id), ("sku", "in", skus)])
            .mapped("sku")
        )
        return [sku for sku in skus if sku not in mapped]

    def _process_order_create(self):
        payload = self.payload
        existing = self._find_order()
        if existing:
            self.write({"state": "done", "sale_order_id": existing.id, "error": False})
            self._log(f"Already imported as {existing.name}")
            return "duplicate order"
        missing = self._unmapped_skus(self._skus())
        if missing:
            self.write(
                {
                    "state": "needs_mapping",
                    "missing_skus": ", ".join(missing),
                    "error": self.env._("SKU %s has no Odoo product", ", ".join(missing)),
                }
            )
            self._log(f"Stopped: {len(missing)} of {len(self._skus())} SKUs unmapped")
            return "needs mapping"
        order = self.env["sale.order"].create(self._prepare_sale_order(payload))
        order.action_confirm()
        self.write(
            {"state": "done", "sale_order_id": order.id, "error": False, "missing_skus": False}
        )
        self._log(f"Created {order.name}")
        return order.name

    def _prepare_sale_order(self, payload):
        store = self.store_id
        maps = {
            m.sku: m.product_id
            for m in self.env["kw.shopify.product.map"].search([("store_id", "=", store.id)])
        }
        lines = []
        for item in payload.get("line_items", []):
            discount = sum(float(d.get("amount", 0)) for d in item.get("discount_allocations", []))
            gross = float(item["price"]) * int(item["quantity"])
            lines.append(
                Command.create(
                    {
                        "product_id": maps[item["sku"]].id,
                        "product_uom_qty": int(item["quantity"]),
                        "price_unit": float(item["price"]),
                        "discount": (discount / gross * 100) if gross else 0.0,
                        # Exports from Indonesia are zero-rated; Shopify collected no VAT.
                        "tax_id": [Command.clear()],
                    }
                )
            )
        return {
            "partner_id": self._find_or_create_customer(payload).id,
            "company_id": store.company_id.id,
            "warehouse_id": store.warehouse_id.id,
            "pricelist_id": store.pricelist_id.id,
            "user_id": store.salesperson_id.id,
            "client_order_ref": payload.get("name"),
            "origin": f"Shopify {payload.get('name')}",
            "kw_channel": "shopify",
            "kw_shopify_store_id": store.id,
            "kw_shopify_order_gid": self.order_gid,
            "order_line": lines,
        }

    def _find_or_create_customer(self, payload):
        customer = payload.get("customer") or {}
        email = (customer.get("email") or payload.get("email") or "").strip().lower()
        Partner = self.env["res.partner"]
        partner = Partner.search([("email", "=ilike", email)], limit=1) if email else Partner
        if partner:
            return partner
        address = payload.get("shipping_address") or {}
        country = self.env["res.country"].search(
            [("code", "=", (address.get("country_code") or "").upper())], limit=1
        )
        name = " ".join(p for p in (customer.get("first_name"), customer.get("last_name")) if p)
        return Partner.create(
            {
                "name": name or email or payload.get("name"),
                "email": email or False,
                "street": address.get("address1"),
                "city": address.get("city"),
                "zip": address.get("zip"),
                "country_id": country.id,
                "comment": self.env._("Created from Shopify order %s", payload.get("name")),
            }
        )

    def _find_order(self):
        if not self.order_gid:
            return self.env["sale.order"]
        return self.env["sale.order"].search(
            [
                ("kw_shopify_store_id", "=", self.store_id.id),
                ("kw_shopify_order_gid", "=", self.order_gid),
            ],
            limit=1,
        )

    def _process_order_cancelled(self):
        order = self._find_order()
        if not order:
            self.write({"state": "done", "error": False})
            self._log("No imported order to cancel")
            return "nothing to cancel"
        if order.picking_ids.filtered(lambda p: p.state == "done"):
            raise UserError(
                self.env._(
                    "%s has already shipped, so it was not cancelled. "
                    "Arrange a return in Odoo and refund in Shopify.",
                    order.name,
                )
            )
        order._action_cancel()
        self.write({"state": "done", "sale_order_id": order.id, "error": False})
        self._log(f"Cancelled {order.name}")
        return "cancelled"

    def action_retry(self):
        retryable = self.filtered("can_retry")
        if self - retryable:
            raise UserError(self.env._("Map the missing SKUs before retrying."))
        retryable._enqueue()
        return True

    def action_map_sku(self):
        """Open a new mapping for the first missing SKU."""
        self.ensure_one()
        sku = (self._unmapped_skus(self._skus()) or [""])[0]
        return {
            "type": "ir.actions.act_window",
            "res_model": "kw.shopify.product.map",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": {"default_store_id": self.store_id.id, "default_sku": sku},
        }

    # -- console rows ---------------------------------------------------------------
    def _console_row(self):
        return {
            "id": self.id,
            "received_at": fields.Datetime.to_string(self.received_at),
            "order_name": self.order_name,
            "topic": self.topic,
            "state": self.state,
            "state_label": dict(self._fields["state"].selection)[self.state],
            "sale_order": self.sale_order_id.name or False,
            "sale_order_id": self.sale_order_id.id or False,
        }

    def _console_detail(self):
        payload = self.payload or {}
        excerpt = {
            key: payload.get(key)
            for key in ("name", "currency", "total_price", "customer", "line_items")
            if key in payload
        }
        if isinstance(excerpt.get("customer"), dict):
            excerpt["customer"] = {"email": excerpt["customer"].get("email")}
        if excerpt.get("line_items"):
            excerpt["line_items"] = [
                {k: li.get(k) for k in ("sku", "quantity", "price")} for li in excerpt["line_items"]
            ]
        return dict(
            self._console_row(),
            webhook_id=self.webhook_id,
            total=payload.get("total_price"),
            currency=payload.get("currency"),
            line_count=len(payload.get("line_items", [])),
            attempts=self.attempts,
            error=self.error,
            missing_skus=self.missing_skus,
            can_retry=self.can_retry,
            log=self.log or [],
            payload_excerpt=excerpt,
        )
