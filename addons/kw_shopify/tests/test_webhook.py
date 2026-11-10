from odoo.addons.queue_job.tests.common import trap_jobs
from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

from .common import ShopifySetupMixin, order_payload


@tagged("post_install", "-at_install")
class TestWebhook(ShopifySetupMixin, HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_shopify()

    def _post(self, payload, webhook_id="wh-1", signature=None, store=None, topic="orders/create"):
        body, good = self.signed(payload)
        store = store or self.store
        return self.url_open(
            f"/kw_shopify/webhook/{store.id}",
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Hmac-Sha256": signature if signature is not None else good,
                "X-Shopify-Topic": topic,
                "X-Shopify-Webhook-Id": webhook_id,
            },
        )

    def _events(self):
        return self.env["kw.shopify.event"].search([("store_id", "=", self.store.id)])

    def test_valid_webhook_is_stored_and_queued(self):
        with trap_jobs() as trap:
            response = self._post(order_payload())
            self.assertEqual(response.status_code, 200)
            trap.assert_jobs_count(1)
            self.assertEqual(trap.enqueued_jobs[0].method_name, "process")
        event = self._events()
        self.assertEqual(event.order_name, "#KW1042")
        self.assertEqual(event.order_gid, "gid://shopify/Order/820982911946154508")
        self.assertEqual(event.state, "queued")
        self.assertFalse(
            self.env["sale.order"].search([("kw_shopify_store_id", "=", self.store.id)]),
            "the request only stores; the job creates the order",
        )

    @mute_logger("odoo.addons.kw_shopify.controllers.main")
    def test_bad_signature_rejected_and_not_stored(self):
        response = self._post(order_payload(), signature="bm90LXRoZS1yaWdodC1zaWc=")
        self.assertEqual(response.status_code, 401)
        self.assertFalse(self._events())

    def test_redelivery_is_ignored(self):
        with trap_jobs() as trap:
            self._post(order_payload(), webhook_id="wh-dup")
            self._post(order_payload(), webhook_id="wh-dup")
            trap.assert_jobs_count(1)
        event = self._events()
        self.assertEqual(len(event), 1)
        self.assertEqual(event.duplicate_count, 1)

    def test_unknown_store(self):
        response = self.url_open(
            "/kw_shopify/webhook/999999", data=b"{}", headers={"X-Shopify-Hmac-Sha256": "x"}
        )
        self.assertEqual(response.status_code, 404)

    def test_oversized_body(self):
        response = self.url_open(
            f"/kw_shopify/webhook/{self.store.id}",
            data=b"x" * (1024 * 1024 + 1),
            headers={"X-Shopify-Hmac-Sha256": "x"},
        )
        self.assertEqual(response.status_code, 413)
