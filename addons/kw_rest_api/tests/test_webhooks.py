import hashlib
import hmac
from unittest.mock import MagicMock, patch

import requests

from odoo.tests import TransactionCase, tagged

from ..models.kw_webhook import RETRY_SCHEDULE

POST = "odoo.addons.kw_rest_api.models.kw_webhook.requests.post"


@tagged("post_install", "-at_install")
class TestWebhooks(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.endpoint = cls.env["kw.webhook.endpoint"].create(
            {"name": "Warehouse app", "url": "https://hooks.example.com/kw", "secret": "s3cret"}
        )
        cls.customer = cls.env["res.partner"].create({"name": "Teras Kopi Jakal"})
        cls.mug = cls.env["product.product"].create(
            {"name": "Celadon mug", "default_code": "KW-MUG", "is_storable": True}
        )

    def _deliveries(self, event):
        return self.env["kw.webhook.delivery"].search([("event", "=", event)])

    def test_order_confirmed_emits_signed_delivery(self):
        order = self.env["sale.order"].create(
            {"partner_id": self.customer.id, "order_line": [(0, 0, {"product_id": self.mug.id})]}
        )
        order.action_confirm()
        delivery = self._deliveries("order.confirmed")
        self.assertEqual(len(delivery), 1)
        self.assertEqual(delivery.payload["name"], order.name)
        with patch(POST, return_value=MagicMock(status_code=200)) as post:
            self.assertEqual(delivery.send(), "sent")
        headers = post.call_args.kwargs["headers"]
        body = post.call_args.kwargs["data"]
        expected = "sha256=" + hmac.new(b"s3cret", body, hashlib.sha256).hexdigest()
        self.assertEqual(headers["X-Kw-Signature"], expected)
        self.assertEqual(headers["X-Kw-Delivery"], delivery.delivery_uid)
        self.assertEqual(delivery.state, "sent")

    def test_unsubscribed_event_not_sent(self):
        self.endpoint.event_order_confirmed = False
        order = self.env["sale.order"].create(
            {"partner_id": self.customer.id, "order_line": [(0, 0, {"product_id": self.mug.id})]}
        )
        order.action_confirm()
        self.assertFalse(self._deliveries("order.confirmed"))

    def test_retry_schedule_then_failed(self):
        delivery = self.env["kw.webhook.delivery"].create(
            {"endpoint_id": self.endpoint.id, "event": "order.confirmed", "payload": {"id": 1}}
        )
        waits = []
        with patch(POST, return_value=MagicMock(status_code=503)):
            for _ in range(len(RETRY_SCHEDULE)):
                result = delivery.send()
                waits.append(int(result.split()[2].rstrip("s")))
                self.assertEqual(delivery.state, "retrying")
            self.assertEqual(delivery.send(), "failed")
        self.assertEqual(waits, RETRY_SCHEDULE)
        self.assertEqual(delivery.state, "failed")
        self.assertEqual(delivery.attempts, 6)
        self.assertEqual(delivery.last_error, "HTTP 503")

    def test_timeout_counts_as_failure(self):
        delivery = self.env["kw.webhook.delivery"].create(
            {"endpoint_id": self.endpoint.id, "event": "stock.low", "payload": {"sku": "KW-MUG"}}
        )
        with patch(POST, side_effect=requests.Timeout("read timed out")):
            delivery.send()
        self.assertEqual(delivery.state, "retrying")
        self.assertIn("timed out", delivery.last_error)

    def test_resend_keeps_delivery_id(self):
        delivery = self.env["kw.webhook.delivery"].create(
            {
                "endpoint_id": self.endpoint.id,
                "event": "order.confirmed",
                "payload": {"id": 1},
                "state": "failed",
                "attempts": 6,
            }
        )
        uid = delivery.delivery_uid
        delivery.action_resend()
        self.assertEqual(delivery.state, "pending")
        self.assertEqual(delivery.attempts, 0)
        self.assertEqual(delivery.delivery_uid, uid)

    def test_stock_low_fires_when_crossing_minimum(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        location = warehouse.lot_stock_id
        self.env["stock.warehouse.orderpoint"].create(
            {
                "product_id": self.mug.id,
                "warehouse_id": warehouse.id,
                "location_id": location.id,
                "product_min_qty": 20,
                "product_max_qty": 60,
                "trigger": "manual",
            }
        )
        self.env["stock.quant"]._update_available_quantity(self.mug, location, 25)
        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "warehouse_id": warehouse.id,
                "order_line": [(0, 0, {"product_id": self.mug.id, "product_uom_qty": 10})],
            }
        )
        order.action_confirm()
        picking = order.picking_ids
        picking.action_assign()
        for move in picking.move_ids:
            move.quantity = move.product_uom_qty
            move.picked = True
        picking.button_validate()
        low = self._deliveries("stock.low")
        self.assertEqual(len(low), 1)
        self.assertEqual(low.payload["on_hand"], 15.0)
        self.assertEqual(low.payload["minimum"], 20.0)
