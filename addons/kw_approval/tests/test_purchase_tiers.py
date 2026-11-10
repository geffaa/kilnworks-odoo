from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from .common import KwApprovalCase


@tagged("post_install", "-at_install")
class TestPurchaseTiers(KwApprovalCase):
    def test_small_order_needs_nothing(self):
        po = self._po(5_000_000)
        self.assertFalse(po.need_validation)
        po.button_confirm()
        self.assertEqual(po.state, "purchase")

    def test_mid_order_needs_lead_only(self):
        po = self._po(12_000_000, user=self.buyer)
        po.with_user(self.buyer).request_validation()
        self.assertEqual(len(po.review_ids), 1)
        self.assertEqual(po.review_ids.reviewer_ids, self.lead | self.owner)

    def test_large_order_two_tiers_in_order(self):
        po = self._po(48_600_000, user=self.buyer)
        po.with_user(self.buyer).request_validation()
        tiers = po.review_ids.sorted("sequence")
        self.assertEqual(len(tiers), 2)
        self.assertEqual(tiers[0].status, "pending")
        self.assertEqual(tiers[1].status, "waiting")
        with self.assertRaises(ValidationError):
            po.with_user(self.buyer).button_confirm()

    def test_creator_cannot_approve_own_order(self):
        po = self._po(48_600_000, user=self.lead)
        po.with_user(self.lead).request_validation()
        tier1 = po.review_ids.sorted("sequence")[0]
        self.assertNotIn(self.lead, tier1.reviewer_ids)
        self.assertEqual(tier1.reviewer_ids, self.owner)
        self.assertEqual(tier1.kw_redirected_from_id, self.lead)
        self.assertTrue(
            po.message_ids.filtered(lambda m: "cannot approve it" in (m.body or "")),
            "the redirect is explained in the chatter",
        )
        self.assertEqual(tier1.todo_by, "Owner", "names the person, not the group")
        redirect_msg = po.message_ids.filtered(lambda m: "cannot approve it" in (m.body or ""))
        self.assertEqual(redirect_msg.author_id, self.env.ref("base.partner_root"))
        # trying anyway approves nothing
        po.with_user(self.lead).validate_tier()
        self.assertEqual(tier1.status, "pending")

    def test_owner_approves_each_tier_separately(self):
        po = self._po(48_600_000, user=self.lead)
        po.with_user(self.lead).request_validation()
        tier1, tier2 = po.review_ids.sorted("sequence")
        po.with_user(self.owner).validate_tier()
        self.assertEqual(tier1.status, "approved")
        self.assertEqual(tier2.status, "pending")
        self.assertFalse(po.validated)
        po.with_user(self.owner).validate_tier()
        self.assertTrue(po.validated)
        po.with_user(self.owner).button_confirm()
        self.assertEqual(po.state, "purchase")

    def test_reject_blocks_confirmation(self):
        po = self._po(12_000_000, user=self.buyer)
        po.with_user(self.buyer).request_validation()
        po.with_user(self.lead).reject_tier()
        self.assertTrue(po.rejected)
        with self.assertRaises(ValidationError):
            po.with_user(self.buyer).button_confirm()

    def test_usd_order_converted_before_comparing(self):
        usd = self.env.ref("base.USD")
        usd.active = True
        self.env["res.currency.rate"].create(
            {
                "currency_id": usd.id,
                "name": fields.Date.today(),
                "rate": 1 / 16_000,
                "company_id": self.env.company.id,
            }
        )
        po = self._po(2_000, user=self.buyer, currency=usd)  # US$ 2,000 ≈ Rp 32 M
        self.assertAlmostEqual(po.kw_amount_company, 32_000_000, delta=1)
        po.with_user(self.buyer).request_validation()
        self.assertEqual(len(po.review_ids), 2)

    def test_lines_locked_once_validation_is_requested(self):
        """OCA refuses edits under validation, so an approval can never cover a changed total."""
        po = self._po(12_000_000, user=self.buyer)
        po.with_user(self.buyer).request_validation()
        po.with_user(self.lead).validate_tier()
        with self.assertRaises(ValidationError):
            po.with_user(self.buyer).write(
                {"order_line": [Command.update(po.order_line.id, {"price_unit": 13_000_000})]}
            )

    def test_tier_order_lead_then_owner(self):
        po = self._po(48_600_000, user=self.buyer)
        po.with_user(self.buyer).request_validation()
        tier1, tier2 = po.review_ids.sorted("sequence")
        self.assertEqual(tier1.definition_id, self.env.ref("kw_approval.tier_po_lead"))
        self.assertEqual(tier2.definition_id, self.env.ref("kw_approval.tier_po_owner"))

    def test_discount_rule_on_quotations(self):
        so = (
            self.env["sale.order"]
            .with_user(self.buyer)
            .create(
                {
                    "partner_id": self.customer.id,
                    "order_line": [
                        Command.create(
                            {"product_id": self.clay.id, "product_uom_qty": 120, "discount": 15}
                        ),
                        Command.create(
                            {"product_id": self.clay.id, "product_uom_qty": 10, "discount": 5}
                        ),
                    ],
                }
            )
        )
        self.assertEqual(so.kw_max_discount, 15)
        self.assertTrue(so.need_validation)
        so.order_line[0].discount = 10
        so.invalidate_recordset(["need_validation"])  # OCA computes it without dependencies
        self.assertFalse(so.need_validation, "10 % is the limit, not above it")
