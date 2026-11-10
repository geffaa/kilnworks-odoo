from odoo.tests import HttpCase, TransactionCase, tagged

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

    def test_midtrans_ready_for_open_invoices(self):
        provider = self.env.ref("payment_midtrans.payment_provider_midtrans")
        self.assertEqual(provider.state, "test")
        self.assertTrue(provider.is_published)
        link = self.env["ir.config_parameter"].sudo().get_param("kw_demo.payment_link")
        self.assertIn("/my/invoices/", link)
        self.assertIn("access_token=", link)
        compatible = (
            self.env["payment.provider"]
            .sudo()
            ._get_compatible_providers(
                self.env.company.id,
                self.env.ref("kw_demo.c_teras").id,
                21_000_000,
                currency_id=self.env.ref("base.IDR").id,
            )
        )
        self.assertIn(provider, compatible)

    def test_midtrans_payment_settles_invoice(self):
        from odoo.addons.payment_midtrans.models.payment_transaction import midtrans_signature

        from ..hooks import DEMO_MIDTRANS_SERVER_KEY

        provider = self.env.ref("payment_midtrans.payment_provider_midtrans")
        invoice = self.env["account.move"].search(
            [("move_type", "=", "out_invoice"), ("payment_state", "=", "not_paid")], limit=1
        )
        tx = self.env["payment.transaction"].create(
            {
                "provider_id": provider.id,
                "payment_method_id": self.env.ref("payment.payment_method_bank_bca").id,
                "amount": invoice.amount_residual,
                "currency_id": invoice.currency_id.id,
                "partner_id": invoice.partner_id.id,
                "reference": invoice.name.replace("/", "-") + "-T",
                "operation": "online_redirect",
                "invoice_ids": [(6, 0, invoice.ids)],
            }
        )
        gross = f"{int(round(tx.amount))}.00"
        data = {
            "order_id": tx.reference,
            "status_code": "200",
            "gross_amount": gross,
            "transaction_status": "settlement",
            "payment_type": "bank_transfer",
            "va_numbers": [{"bank": "bca", "va_number": "12785002530231"}],
            "signature_key": midtrans_signature(
                tx.reference, "200", gross, DEMO_MIDTRANS_SERVER_KEY
            ),
        }
        tx._handle_notification_data("midtrans", data)
        tx._post_process()
        self.assertEqual(tx.state, "done")
        self.assertTrue(tx.payment_id, "an accounting payment was created")
        invoice.invalidate_recordset(["payment_state", "amount_residual"])
        self.assertIn(invoice.payment_state, ("paid", "in_payment"))

    def test_dashboard_on_demo_data(self):
        ratna = self.env.ref("kw_demo.user_ratna")
        data = self.env["kw.ops.dashboard"].with_user(ratna).get_data(30)
        self.assertEqual(data["approvals"]["count"], 3)
        self.assertTrue(data["approvals"]["rows"][0]["late"], "the escalated PO comes first")
        self.assertEqual(data["sync"]["count"], 2)
        self.assertEqual(data["low_stock"]["count"], 5)
        b2b, shopify = data["revenue"]["channels"]
        self.assertGreater(b2b["orders"], 0)
        self.assertGreater(shopify["orders"], 0)
        self.assertTrue(shopify["foreign"])

    def test_export_fields_and_api_key(self):
        from ..hooks import DEMO_API_KEY

        mug = self.env["product.product"].search([("default_code", "=", "KW-MUG-350-CEL")])
        self.assertEqual(mug.kw_hs_code, "6912.00")
        self.assertEqual(mug.kw_carton_qty, 24)
        key = self.env["kw.api.key"]._authenticate(DEMO_API_KEY)
        self.assertEqual(key.name, "Warehouse scanner app")


@tagged("post_install", "-at_install")
class TestDemoTour(HttpCase):
    def test_dashboard_to_purchase_order(self):
        self.start_tour(
            "/odoo/action-kw_ops_dashboard.action_dashboard", "kw_dashboard_to_po", login="ratna"
        )
