from odoo.tests import TransactionCase, tagged

from ..hooks import PO_COUNT, SO_COUNT, STOCK_TARGETS, post_init_hook


@tagged("post_install", "-at_install")
class TestSeed(TransactionCase):
    def test_company(self):
        company = self.env.ref("base.main_company")
        self.assertEqual(company.name, "Kilnworks Stoneware")
        self.assertEqual(company.currency_id, self.env.ref("base.IDR"))
        self.assertEqual(company.country_id, self.env.ref("base.id"))
        self.assertEqual(company.chart_template, "id")

    def test_users_have_role_groups(self):
        ratna = self.env.ref("kw_demo.user_ratna")
        dimas = self.env.ref("kw_demo.user_dimas")
        self.assertTrue(ratna.has_group("purchase.group_purchase_manager"))
        self.assertTrue(dimas.has_group("purchase.group_purchase_user"))
        self.assertFalse(dimas.has_group("purchase.group_purchase_manager"))

    def test_catalogue(self):
        goods = self.env["product.product"].search([("default_code", "=like", "KW-%")])
        self.assertEqual(len(goods), 18)
        self.assertEqual(len(set(goods.mapped("default_code"))), 18)
        self.assertTrue(all(goods.mapped("is_storable")))

    def test_stock_matches_targets(self):
        for sku, (on_hand, minimum) in STOCK_TARGETS.items():
            product = self.env["product.product"].search([("default_code", "=", sku)])
            self.assertEqual(product.qty_available, on_hand, sku)
            orderpoint = self.env["stock.warehouse.orderpoint"].search(
                [("product_id", "=", product.id)]
            )
            self.assertEqual(orderpoint.product_min_qty, minimum, sku)

    def test_history(self):
        sos = self.env["sale.order"].search(
            [("user_id", "=", self.env.ref("kw_demo.user_sekar").id)]
        )
        pos = self.env["purchase.order"].search(
            [("user_id", "=", self.env.ref("kw_demo.user_dimas").id)]
        )
        self.assertEqual(len(sos), SO_COUNT)
        self.assertEqual(len(pos), PO_COUNT)
        self.assertTrue(sos.filtered(lambda s: s.state == "draft"), "some quotations stay open")
        idr = self.env.ref("base.IDR")
        self.assertEqual(set(sos.mapped("currency_id")), {idr})
        invoices = sos.invoice_ids
        self.assertEqual(set(invoices.mapped("currency_id")), {idr})
        # 30-day terms: some open invoices are already overdue, none fall due on the invoice date
        # B2B sales carry the company's default VAT (PPN)
        sale_tax = self.env.ref("base.main_company").account_sale_tax_id
        self.assertTrue(sale_tax)
        self.assertEqual(set(sos.order_line.tax_id), {sale_tax})
        self.assertTrue(all(m.amount_tax > 0 for m in invoices))
        self.assertTrue(all(m.invoice_date_due > m.invoice_date for m in invoices))
        self.assertTrue(invoices.filtered(lambda m: m.payment_state in ("paid", "in_payment")))
        self.assertTrue(invoices.filtered(lambda m: m.payment_state == "not_paid"))
        # vendor bills: raw-material vendors are not VAT-registered
        self.assertFalse(pos.order_line.taxes_id)

    def test_hook_runs_once(self):
        before = self.env["sale.order"].search_count([])
        post_init_hook(self.env)
        self.assertEqual(self.env["sale.order"].search_count([]), before)
