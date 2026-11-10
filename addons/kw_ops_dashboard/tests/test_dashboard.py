from datetime import timedelta

from odoo import fields
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestDashboard(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.customer = cls.env["res.partner"].create({"name": "Teras Kopi Jakal"})
        cls.mug = cls.env["product.product"].create(
            {
                "name": "Celadon mug",
                "default_code": "KW-MUG",
                "is_storable": True,
                "list_price": 100000,
            }
        )
        cls.Dashboard = cls.env["kw.ops.dashboard"]

    def test_shape_on_empty_data(self):
        data = self.Dashboard.get_data(30)
        self.assertEqual(data["period"], 30)
        self.assertEqual(
            set(data), {"period", "range", "approvals", "sync", "revenue", "low_stock", "invoices"}
        )
        self.assertEqual([c["code"] for c in data["revenue"]["channels"]], ["b2b", "shopify"])

    def test_unknown_period_falls_back(self):
        self.assertEqual(self.Dashboard.get_data(12)["period"], 30)

    def test_revenue_counts_confirmed_orders_in_period(self):
        order = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "order_line": [
                    (0, 0, {"product_id": self.mug.id, "product_uom_qty": 10, "tax_id": False})
                ],
            }
        )
        order.action_confirm()
        old = order.copy()
        old.action_confirm()
        old.date_order = fields.Datetime.now() - timedelta(days=45)
        b2b = self.Dashboard.get_data(30)["revenue"]["channels"][0]
        self.assertEqual(b2b["orders"], 1)
        self.assertEqual(b2b["delta"], 0.0, "same amount in the previous 30 days")
        weekly = self.Dashboard.get_data(7)["revenue"]["series"]
        self.assertEqual(len(weekly), 7)
        self.assertAlmostEqual(sum(s["b2b"] for s in weekly), 1.0, places=2)

    def test_low_stock_sorted_by_shortfall(self):
        warehouse = self.env["stock.warehouse"].search(
            [("company_id", "=", self.env.company.id)], limit=1
        )
        bowl = self.env["product.product"].create({"name": "Bowl", "is_storable": True})
        for product, qty, minimum in ((self.mug, 30, 60), (bowl, 5, 50)):
            self.env["stock.quant"]._update_available_quantity(product, warehouse.lot_stock_id, qty)
            self.env["stock.warehouse.orderpoint"].create(
                {
                    "product_id": product.id,
                    "warehouse_id": warehouse.id,
                    "location_id": warehouse.lot_stock_id.id,
                    "product_min_qty": minimum,
                    "product_max_qty": minimum * 2,
                    "trigger": "manual",
                }
            )
        low = self.Dashboard.get_data()["low_stock"]
        self.assertEqual(low["count"], 2)
        self.assertEqual([r["name"] for r in low["rows"]], ["Bowl", "Celadon mug"])
