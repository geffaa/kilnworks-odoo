import logging

import requests

from odoo import api, fields, models
from odoo.addons.queue_job.exception import RetryableJobError
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

STOCK_PUSH_DELAY = 60  # seconds: changes inside this window go out in one call
STOCK_PUSH_BATCH = (
    100  # inventorySetQuantities accepts up to this many quantities (verify per version)
)

SET_QUANTITIES = """
mutation SetQuantities($input: InventorySetQuantitiesInput!) {
  inventorySetQuantities(input: $input) {
    userErrors { field message code }
  }
}
"""


class KwShopifyStore(models.Model):
    _name = "kw.shopify.store"
    _description = "Shopify store"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    shop_domain = fields.Char(required=True, help="kilnworks-studio.myshopify.com")
    api_version = fields.Char(default="2025-10", required=True)
    api_base_url = fields.Char(
        string="API base URL",
        help="Leave empty for https://<shop domain>. Set to the mock server for offline demos.",
    )
    access_token = fields.Char(groups="base.group_system", copy=False)
    webhook_secret = fields.Char(groups="base.group_system", copy=False)
    location_gid = fields.Char(
        string="Shopify location",
        required=True,
        help="gid://shopify/Location/… whose available stock this store mirrors.",
    )
    company_id = fields.Many2one("res.company", required=True, default=lambda s: s.env.company)
    warehouse_id = fields.Many2one(
        "stock.warehouse", required=True, domain="[('company_id', '=', company_id)]"
    )
    pricelist_id = fields.Many2one(
        "product.pricelist", required=True, help="Its currency is the store currency."
    )
    salesperson_id = fields.Many2one("res.users", string="Salesperson")
    active = fields.Boolean(default=True)
    last_stock_push_at = fields.Datetime(readonly=True)
    last_stock_push_count = fields.Integer(readonly=True)
    map_ids = fields.One2many("kw.shopify.product.map", "store_id", string="Product map")
    map_count = fields.Integer(compute="_compute_map_count")
    webhook_url = fields.Char(compute="_compute_webhook_url")

    _sql_constraints = [("domain_uniq", "unique(shop_domain)", "This store is already connected.")]

    def _compute_map_count(self):
        for store in self:
            store.map_count = len(store.map_ids)

    def _compute_webhook_url(self):
        base = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        for store in self:
            store.webhook_url = f"{base}/kw_shopify/webhook/{store.id}" if store.id else False

    # -- Shopify API ----------------------------------------------------------------
    def _graphql_url(self):
        self.ensure_one()
        base = (self.api_base_url or f"https://{self.shop_domain}").rstrip("/")
        return f"{base}/admin/api/{self.api_version}/graphql.json"

    def _graphql(self, query, variables):
        """Call the Admin GraphQL API. Throttling becomes a retryable job error."""
        self.ensure_one()
        try:
            response = requests.post(
                self._graphql_url(),
                json={"query": query, "variables": variables},
                headers={"X-Shopify-Access-Token": self.sudo().access_token or ""},
                timeout=20,
            )
        except requests.RequestException as exc:
            raise RetryableJobError(f"Shopify unreachable: {exc}", seconds=60) from exc
        if response.status_code == 429:
            wait = int(float(response.headers.get("Retry-After", 2)))
            raise RetryableJobError("Shopify rate limit (HTTP 429)", seconds=max(wait, 2))
        if response.status_code >= 500:
            raise RetryableJobError(f"Shopify error {response.status_code}", seconds=60)
        if response.status_code != 200:
            raise UserError(
                self.env._(
                    "Shopify refused the call (%(code)s): %(body)s",
                    code=response.status_code,
                    body=response.text[:300],
                )
            )
        body = response.json()
        errors = body.get("errors") or []
        if any((e.get("extensions") or {}).get("code") == "THROTTLED" for e in errors):
            raise RetryableJobError("Shopify GraphQL cost limit reached", seconds=5)
        if errors:
            raise UserError(self.env._("Shopify GraphQL error: %s", errors[0].get("message")))
        return body.get("data") or {}

    # -- stock ----------------------------------------------------------------------
    @api.model
    def _kw_schedule_stock_push(self, products):
        """Called when stock moves. One delayed push per store, however many changes."""
        products = products.filtered(lambda p: p.is_storable)
        if not products:
            return
        maps = (
            self.env["kw.shopify.product.map"]
            .sudo()
            .search([("product_id", "in", products.ids), ("store_id.active", "=", True)])
        )
        for store in maps.store_id:
            store.with_delay(
                eta=STOCK_PUSH_DELAY,
                identity_key=f"kw_shopify.push_stock:{store.id}",
                channel="root.kw_shopify",
                description=f"Push stock to {store.shop_domain}",
            ).push_stock()

    def _available_quantities(self):
        self.ensure_one()
        location = self.warehouse_id.lot_stock_id
        result = []
        for line in self.map_ids.filtered(lambda m: m.inventory_item_gid):
            qty = line.product_id.with_context(location=location.id).free_qty
            result.append(
                {
                    "inventoryItemId": line.inventory_item_gid,
                    "locationId": self.location_gid,
                    "quantity": max(int(qty), 0),
                }
            )
        return result

    def push_stock(self):
        """Set Shopify's "available" quantity for every mapped product to Odoo's free stock."""
        self.ensure_one()
        quantities = self._available_quantities()
        for start in range(0, len(quantities), STOCK_PUSH_BATCH):
            batch = quantities[start : start + STOCK_PUSH_BATCH]
            data = self._graphql(
                SET_QUANTITIES,
                {
                    "input": {
                        "name": "available",
                        "reason": "correction",
                        "ignoreCompareQuantity": True,
                        "quantities": batch,
                    }
                },
            )
            user_errors = (data.get("inventorySetQuantities") or {}).get("userErrors") or []
            if user_errors:
                raise UserError(
                    self.env._("Shopify rejected the stock update: %s", user_errors[0]["message"])
                )
        self.write(
            {"last_stock_push_at": fields.Datetime.now(), "last_stock_push_count": len(quantities)}
        )
        return len(quantities)

    def action_push_stock_now(self):
        for store in self:
            store.with_delay(channel="root.kw_shopify").push_stock()
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {"message": self.env._("Stock push queued."), "type": "info"},
        }

    # -- console --------------------------------------------------------------------
    @api.model
    def get_console_data(self, store_id=None, state_filter="attention", event_id=None):
        """Everything the Shopify console shows, in one call."""
        store = self.browse(store_id) if store_id else self.search([], limit=1)
        if not store:
            return {"store": False}
        Event = self.env["kw.shopify.event"]
        since = fields.Datetime.subtract(fields.Datetime.now(), hours=24)
        base = [("store_id", "=", store.id), ("received_at", ">=", since)]
        counts = {"all": Event.search_count(base)}
        counts["attention"] = Event.search_count(base + [("state", "in", Event.ATTENTION)])
        counts["done"] = Event.search_count(base + [("state", "=", "done")])
        domain = list(base)
        if state_filter == "attention":
            domain += [("state", "in", Event.ATTENTION)]
        elif state_filter == "done":
            domain += [("state", "=", "done")]
        events = Event.search(domain, limit=80)
        if state_filter == "attention":
            events |= Event.search(base + [("state", "=", "done")], limit=6)
        selected = Event.browse(event_id) if event_id else (events[:1])
        return {
            "store": {
                "id": store.id,
                "name": store.name,
                "domain": store.shop_domain,
                "api_version": store.api_version,
                "map_count": store.map_count,
                "location": store.warehouse_id.lot_stock_id.display_name,
                "last_push": fields.Datetime.to_string(store.last_stock_push_at)
                if store.last_stock_push_at
                else False,
                "last_push_count": store.last_stock_push_count,
            },
            "counts": counts,
            "duplicates_today": store._duplicate_count_today(),
            "events": [e._console_row() for e in events.sorted("received_at", reverse=True)],
            "selected": selected._console_detail() if selected else False,
        }

    def _duplicate_count_today(self):
        self.ensure_one()
        today = fields.Datetime.to_datetime(fields.Date.context_today(self))
        events = self.env["kw.shopify.event"].search(
            [("store_id", "=", self.id), ("last_duplicate_at", ">=", today)]
        )
        return sum(events.mapped("duplicate_count"))
