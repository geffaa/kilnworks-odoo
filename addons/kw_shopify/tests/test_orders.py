import uuid

from odoo.tests import TransactionCase, tagged

from .common import ShopifySetupMixin, order_payload


@tagged("post_install", "-at_install")
class TestOrders(ShopifySetupMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_shopify()

    def _event(self, payload=None, topic="orders/create"):
        payload = payload or order_payload()
        return self.env["kw.shopify.event"].create(
            {
                "store_id": self.store.id,
                "webhook_id": str(uuid.uuid4()),
                "topic": topic,
                "order_name": payload["name"],
                "order_gid": payload["admin_graphql_api_id"],
                "payload": payload,
            }
        )

    def test_order_becomes_confirmed_sale_order(self):
        event = self._event()
        event.process()
        order = event.sale_order_id
        self.assertEqual(event.state, "done")
        self.assertEqual(order.state, "sale")
        self.assertEqual(order.currency_id, self.usd)
        self.assertEqual(order.kw_channel, "shopify")
        self.assertEqual(order.client_order_ref, "#KW1042")
        self.assertEqual(order.partner_id.email, "m.okafor@example.com")
        self.assertEqual(order.partner_id.country_id.code, "NZ")
        self.assertFalse(order.order_line.tax_id, "exports carry no VAT")
        self.assertAlmostEqual(order.amount_total, 4 * 24 + 22 - 2.2, places=2)
        self.assertTrue(order.picking_ids, "confirmation creates the delivery")

    def test_same_order_twice_creates_one_sale_order(self):
        first = self._event()
        first.process()
        second = self._event()  # e.g. a manual resend from Shopify: new webhook id, same order
        second.process()
        self.assertEqual(second.sale_order_id, first.sale_order_id)
        self.assertEqual(
            self.env["sale.order"].search_count([("kw_shopify_store_id", "=", self.store.id)]), 1
        )

    def test_returning_customer_matched_by_email(self):
        partner = self.env["res.partner"].create(
            {"name": "Maya Okafor", "email": "M.Okafor@example.com"}
        )
        event = self._event()
        event.process()
        self.assertEqual(event.sale_order_id.partner_id, partner)

    def test_unknown_sku_stops_without_half_order(self):
        payload = order_payload(name="#KW1043", admin_graphql_api_id="gid://shopify/Order/1043")
        payload["line_items"][0]["sku"] = "KW-MUG-350-SAGE"
        event = self._event(payload)
        event.process()
        self.assertEqual(event.state, "needs_mapping")
        self.assertEqual(event.missing_skus, "KW-MUG-350-SAGE")
        self.assertFalse(event.sale_order_id)
        self.assertFalse(
            self.env["sale.order"].search(
                [("kw_shopify_order_gid", "=", "gid://shopify/Order/1043")]
            )
        )
        self.assertFalse(event.can_retry)
        # the fix: map the SKU, then retry
        sage = self.env["product.product"].create(
            {"name": "Sage mug", "default_code": "KW-MUG-350-SAGE", "is_storable": True}
        )
        self.env["kw.shopify.product.map"].create(
            {"store_id": self.store.id, "product_id": sage.id, "sku": "KW-MUG-350-SAGE"}
        )
        event.invalidate_recordset(["can_retry"])
        self.assertTrue(event.can_retry)
        event.action_retry()
        self.assertEqual(event.state, "queued")
        event.process()
        self.assertEqual(event.state, "done")
        self.assertIn(sage, event.sale_order_id.order_line.product_id)

    def test_cancel_before_shipping(self):
        created = self._event()
        created.process()
        cancel = self._event(topic="orders/cancelled")
        cancel.process()
        self.assertEqual(cancel.state, "done")
        self.assertEqual(created.sale_order_id.state, "cancel")

    def test_cancel_after_shipping_needs_a_person(self):
        created = self._event()
        created.process()
        order = created.sale_order_id
        self.env["stock.quant"]._update_available_quantity(
            self.mug, self.warehouse.lot_stock_id, 10
        )
        self.env["stock.quant"]._update_available_quantity(
            self.plate, self.warehouse.lot_stock_id, 10
        )
        picking = order.picking_ids
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        picking.button_validate()
        cancel = self._event(topic="orders/cancelled")
        cancel.process()
        self.assertEqual(cancel.state, "failed")
        self.assertIn("already shipped", cancel.error)
        self.assertEqual(order.state, "sale")
        self.assertEqual(cancel.sale_order_id, order, "linked so the person can open it")
        self.assertTrue(cancel.can_retry)

    def test_console_data(self):
        self._event().process()
        payload = order_payload(name="#KW1043", admin_graphql_api_id="gid://shopify/Order/1043")
        payload["line_items"][0]["sku"] = "KW-MUG-350-SAGE"
        stuck = self._event(payload)
        stuck.process()
        data = self.env["kw.shopify.store"].with_user(self.ops).get_console_data(self.store.id)
        self.assertEqual(data["counts"], {"all": 2, "attention": 1, "done": 1})
        self.assertEqual(data["selected"]["order_name"], "#KW1043")
        self.assertNotIn(
            "shipping_address", data["selected"]["payload_excerpt"], "excerpt keeps addresses out"
        )
