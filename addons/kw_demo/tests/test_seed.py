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
        showcase = sos.filtered("review_ids")
        self.assertEqual(len(sos), SO_COUNT + len(showcase))
        self.assertEqual(len(pos.filtered(lambda p: not p.review_ids)), PO_COUNT)
        self.assertTrue(sos.filtered(lambda s: s.state == "draft"), "some quotations stay open")
        self.assertTrue(pos[0].name.startswith("PO/"))
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
        # raw-material vendors are not VAT-registered
        self.assertFalse(pos.order_line.taxes_id)

    def test_hook_runs_once(self):
        before = self.env["sale.order"].search_count([])
        post_init_hook(self.env)
        self.assertEqual(self.env["sale.order"].search_count([]), before)

    def test_approval_showcase(self):
        ratna = self.env.ref("kw_demo.user_ratna")
        dimas = self.env.ref("kw_demo.user_dimas")
        sekar = self.env.ref("kw_demo.user_sekar")
        clay = self.env["purchase.order"].search([("amount_total", "=", 48_600_000)])
        self.assertEqual(len(clay), 1)
        tier1, tier2 = clay.review_ids.sorted("sequence")
        self.assertEqual(tier1.kw_redirected_from_id, dimas)
        self.assertEqual(tier1.reviewer_ids, ratna | sekar, "owner plus her delegate")
        self.assertTrue(tier1.kw_escalated_at)
        self.assertEqual(tier2.status, "waiting")
        quote = self.env["sale.order"].search([("kw_max_discount", "=", 15)])
        self.assertEqual(quote.review_ids.status, "pending")
        inbox = (
            self.env["tier.review"]
            .with_user(ratna)
            .search([("reviewer_ids", "in", ratna.id), ("status", "=", "pending")])
        )
        self.assertEqual(len(inbox), 3)

    def test_shopify_history(self):
        store = self.env.ref("kw_demo.shopify_store")
        events = self.env["kw.shopify.event"].search([("store_id", "=", store.id)])
        stuck = events.filtered(lambda e: e.state == "needs_mapping")
        self.assertEqual(stuck.order_name, "#KW1043")
        self.assertEqual(stuck.missing_skus, "KW-MUG-350-SAGE")
        failed = events.filtered(lambda e: e.state == "failed")
        self.assertEqual(failed.topic, "orders/cancelled")
        orders = self.env["sale.order"].search([("kw_channel", "=", "shopify")])
        self.assertEqual(len(orders), 39)
        self.assertEqual(set(orders.mapped("currency_id")), {self.env.ref("base.USD")})
        data = store.get_console_data(store.id)
        self.assertEqual(data["counts"]["attention"], 2)
        self.assertEqual(data["duplicates_today"], 2)
