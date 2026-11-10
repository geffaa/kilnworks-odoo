from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestPackingList(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        Product = cls.env["product.product"]
        cls.mug = Product.create(
            {
                "name": "Celadon mug",
                "is_storable": True,
                "weight": 0.42,
                "kw_hs_code": "6912.00",
                "kw_carton_qty": 24,
                "kw_carton_tare_kg": 1.2,
            }
        )
        cls.plate = Product.create(
            {
                "name": "Dinner plate",
                "is_storable": True,
                "weight": 0.95,
                "kw_hs_code": "6912.00",
                "kw_carton_qty": 12,
                "kw_carton_tare_kg": 1.5,
            }
        )
        cls.customer = cls.env["res.partner"].create(
            {"name": "Harbour Kitchen Supply", "country_id": cls.env.ref("base.nz").id}
        )
        warehouse = cls.env["stock.warehouse"].search(
            [("company_id", "=", cls.env.company.id)], limit=1
        )
        cls.picking = cls.env["stock.picking"].create(
            {
                "partner_id": cls.customer.id,
                "picking_type_id": warehouse.out_type_id.id,
                "location_id": warehouse.lot_stock_id.id,
                "location_dest_id": cls.env.ref("stock.stock_location_customers").id,
                "move_ids": [
                    (
                        0,
                        0,
                        {
                            "name": "mug",
                            "product_id": cls.mug.id,
                            "product_uom_qty": 50,
                            "product_uom": cls.mug.uom_id.id,
                            "location_id": warehouse.lot_stock_id.id,
                            "location_dest_id": cls.env.ref("stock.stock_location_customers").id,
                        },
                    ),
                    (
                        0,
                        0,
                        {
                            "name": "plate",
                            "product_id": cls.plate.id,
                            "product_uom_qty": 12,
                            "product_uom": cls.plate.uom_id.id,
                            "location_id": warehouse.lot_stock_id.id,
                            "location_dest_id": cls.env.ref("stock.stock_location_customers").id,
                        },
                    ),
                ],
            }
        )

    def test_cartons_split_by_units_per_carton(self):
        cartons = self.picking._kw_cartons()
        # 50 mugs at 24 per carton -> 24, 24, 2; 12 plates -> one carton
        self.assertEqual([c["units"] for c in cartons], [24, 24, 2, 12])
        self.assertEqual([c["number"] for c in cartons], [1, 2, 3, 4])
        self.assertEqual(cartons[0]["net_kg"], 10.08)
        self.assertEqual(cartons[0]["gross_kg"], 11.28)

    def test_totals_match_lines(self):
        totals = self.picking._kw_packing_totals()
        cartons = self.picking._kw_cartons()
        self.assertEqual(totals["cartons"], 4)
        self.assertEqual(totals["units"], 62)
        self.assertAlmostEqual(totals["gross_kg"], sum(c["gross_kg"] for c in cartons), places=2)
        self.assertAlmostEqual(totals["net_kg"], 50 * 0.42 + 12 * 0.95, places=2)

    def test_missing_hs_code_blocks_printing(self):
        self.plate.kw_hs_code = False
        with self.assertRaisesRegex(UserError, "Dinner plate"):
            self.picking.action_kw_print_packing_list()

    def test_report_renders(self):
        html, _fmt = self.env["ir.actions.report"]._render_qweb_html(
            "kw_reports.report_packing_list", self.picking.ids
        )
        text = html.decode()
        self.assertIn("Packing List", text)
        self.assertIn("6912.00", text)
        self.assertIn("Harbour Kitchen Supply", text)
