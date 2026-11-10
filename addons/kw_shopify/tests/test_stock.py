from unittest.mock import MagicMock, patch

from odoo.addons.queue_job.exception import RetryableJobError
from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged

from .common import ShopifySetupMixin

POST = "odoo.addons.kw_shopify.models.kw_shopify_store.requests.post"


def response(status=200, body=None, headers=None):
    mock = MagicMock(status_code=status, headers=headers or {}, text="")
    mock.json.return_value = (
        body if body is not None else {"data": {"inventorySetQuantities": {"userErrors": []}}}
    )
    return mock


@tagged("post_install", "-at_install")
class TestStock(ShopifySetupMixin, TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._setup_shopify()
        cls.stock = cls.warehouse.lot_stock_id

    def _set(self, product, qty):
        quant = (
            self.env["stock.quant"]
            .with_context(inventory_mode=True)
            .create(
                {"product_id": product.id, "location_id": self.stock.id, "inventory_quantity": qty}
            )
        )
        quant.action_apply_inventory()

    def _push_jobs(self):
        return self.env["queue.job"].search(
            [
                ("identity_key", "=", f"kw_shopify.push_stock:{self.store.id}"),
                ("state", "=", "pending"),
            ]
        )

    def test_stock_changes_collapse_into_one_push(self):
        self._set(self.mug, 42)
        self._set(self.plate, 18)
        self._set(self.mug, 40)
        self.assertEqual(len(self._push_jobs()), 1)

    def test_push_sends_free_quantity_for_every_mapped_product(self):
        self._set(self.mug, 42)
        self._set(self.plate, 18)
        with patch(POST, return_value=response()) as post:
            count = self.store.push_stock()
        self.assertEqual(count, 2)
        self.assertEqual(post.call_count, 1)
        sent = post.call_args.kwargs["json"]["variables"]["input"]
        self.assertEqual(sent["name"], "available")
        quantities = {q["inventoryItemId"]: q["quantity"] for q in sent["quantities"]}
        self.assertEqual(
            quantities, {"gid://shopify/InventoryItem/1": 42, "gid://shopify/InventoryItem/2": 18}
        )
        self.assertEqual(post.call_args.kwargs["headers"]["X-Shopify-Access-Token"], "shpat_test")
        self.assertTrue(post.call_args.args[0].endswith("/admin/api/2025-10/graphql.json"))
        self.assertEqual(self.store.last_stock_push_count, 2)

    def test_rate_limit_is_retryable(self):
        with patch(POST, return_value=response(429, headers={"Retry-After": "4"})):
            with self.assertRaises(RetryableJobError):
                self.store.push_stock()

    def test_graphql_throttle_is_retryable(self):
        body = {"errors": [{"message": "Throttled", "extensions": {"code": "THROTTLED"}}]}
        with patch(POST, return_value=response(body=body)):
            with self.assertRaises(RetryableJobError):
                self.store.push_stock()

    def test_user_errors_surface(self):
        body = {
            "data": {
                "inventorySetQuantities": {
                    "userErrors": [{"message": "Inventory item not stocked at location"}]
                }
            }
        }
        with patch(POST, return_value=response(body=body)):
            with self.assertRaises(UserError):
                self.store.push_stock()

    def test_unmapped_product_does_not_schedule(self):
        other = self.env["product.product"].create({"name": "Not on Shopify", "is_storable": True})
        self._set(other, 5)
        self.assertFalse(self._push_jobs())
