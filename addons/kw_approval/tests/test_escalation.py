from datetime import timedelta

from odoo import fields
from odoo.tests import tagged

from .common import KwApprovalCase


@tagged("post_install", "-at_install")
class TestEscalation(KwApprovalCase):
    def setUp(self):
        super().setUp()
        self.po = self._po(48_600_000, user=self.buyer)
        self.po.with_user(self.buyer).request_validation()
        self.tier1 = self.po.review_ids.sorted("sequence")[0]
        self.activity_type = self.env.ref("mail.mail_activity_data_todo")

    def _activities(self):
        return self.po.activity_ids.filtered(lambda a: a.activity_type_id == self.activity_type)

    def test_pending_since_is_stamped(self):
        self.assertTrue(self.tier1.kw_pending_since)
        tier2 = self.po.review_ids.sorted("sequence")[1]
        self.assertFalse(tier2.kw_pending_since, "a waiting tier has not started its clock")
        self.po.with_user(self.lead).validate_tier()
        self.assertTrue(tier2.kw_pending_since)

    def test_clock_not_reset_by_repeated_pending_writes(self):
        started = fields.Datetime.now() - timedelta(hours=26)
        self.tier1.kw_pending_since = started
        self.tier1.write({"status": "pending"})
        self.tier1._compute_can_review()
        self.assertEqual(self.tier1.kw_pending_since, started)
        self.assertGreaterEqual(self.tier1.kw_waiting_hours, 26)

    def test_fresh_review_not_escalated(self):
        self.env["tier.review"]._cron_kw_escalate()
        self.assertFalse(self.tier1.kw_escalated_at)

    def test_overdue_review_escalates_once(self):
        # A week covers 24 working hours on any calendar.
        self.tier1.kw_pending_since = fields.Datetime.now() - timedelta(days=7)
        self.env["tier.review"]._cron_kw_escalate()
        self.assertTrue(self.tier1.kw_escalated_at)
        first = self._activities()
        self.assertEqual(first.user_id, self.tier1.reviewer_ids)
        self.assertTrue(self.po.message_ids.filtered(lambda m: "Escalated to" in (m.body or "")))
        self.env["tier.review"]._cron_kw_escalate()
        self.assertEqual(self._activities(), first, "no second round of activities")

    def test_deadline_uses_working_calendar(self):
        """24 working hours on a 40 h/week calendar is three working days, not one day."""
        monday_9 = fields.Datetime.to_datetime("2026-11-09 02:00:00")  # 09:00 Asia/Jakarta
        calendar = self.env.company.resource_calendar_id
        calendar.tz = "Asia/Jakarta"
        self.tier1.kw_pending_since = monday_9
        deadline = self.tier1._kw_deadline()
        self.assertGreaterEqual(deadline - monday_9, timedelta(days=2))
