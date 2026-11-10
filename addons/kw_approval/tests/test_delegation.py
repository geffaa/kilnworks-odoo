from datetime import timedelta

from psycopg2 import IntegrityError

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import KwApprovalCase


@tagged("post_install", "-at_install")
class TestDelegation(KwApprovalCase):
    def _delegate(self, frm, to, start=0, end=4):
        today = fields.Date.today()
        return self.env["kw.approval.delegation"].create(
            {
                "delegator_id": frm.id,
                "delegate_id": to.id,
                "date_from": today + timedelta(days=start),
                "date_to": today + timedelta(days=end),
            }
        )

    def test_delegate_approves_on_behalf(self):
        self._delegate(self.owner, self.delegate)
        po = self._po(48_600_000, user=self.lead)
        po.with_user(self.lead).request_validation()
        tier1 = po.review_ids.sorted("sequence")[0]
        self.assertIn(self.delegate, tier1.reviewer_ids)
        po.with_user(self.delegate).validate_tier()
        self.assertEqual(tier1.status, "approved")
        self.assertEqual(tier1.done_by, self.delegate)
        self.assertEqual(tier1.kw_acted_on_behalf_of_id, self.owner)

    def test_delegation_added_later_reaches_open_reviews(self):
        po = self._po(48_600_000, user=self.lead)
        po.with_user(self.lead).request_validation()
        tier1 = po.review_ids.sorted("sequence")[0]
        self.assertNotIn(self.delegate, tier1.reviewer_ids)
        delegation = self._delegate(self.owner, self.delegate)
        self.assertIn(self.delegate, tier1.reviewer_ids)
        delegation.unlink()
        self.assertNotIn(self.delegate, tier1.reviewer_ids)

    def test_future_delegation_not_active_yet(self):
        self._delegate(self.owner, self.delegate, start=3, end=6)
        po = self._po(48_600_000, user=self.lead)
        po.with_user(self.lead).request_validation()
        self.assertNotIn(self.delegate, po.review_ids.reviewer_ids)

    def test_delegate_never_approves_own_order(self):
        self._delegate(self.owner, self.buyer)
        po = self._po(48_600_000, user=self.buyer)
        po.with_user(self.buyer).request_validation()
        self.assertNotIn(self.buyer, po.review_ids.reviewer_ids)

    def test_loop_refused(self):
        self._delegate(self.owner, self.delegate)
        with self.assertRaises(ValidationError):
            self._delegate(self.delegate, self.owner, start=1, end=2)

    @mute_logger("odoo.sql_db")
    def test_self_delegation_refused(self):
        with self.assertRaises(IntegrityError):
            self._delegate(self.owner, self.owner)

    @mute_logger("odoo.sql_db")
    def test_end_before_start_refused(self):
        with self.assertRaises(IntegrityError):
            self._delegate(self.owner, self.delegate, start=3, end=1)
