from datetime import timedelta

import pytz

from odoo import api, fields, models


class TierReview(models.Model):
    _inherit = "tier.review"

    kw_redirected_from_id = fields.Many2one(
        "res.users",
        string="Redirected from",
        readonly=True,
        help="The document's creator, who would otherwise have reviewed it.",
    )
    kw_pending_since = fields.Datetime(readonly=True)
    kw_escalated_at = fields.Datetime(string="Escalated", readonly=True)
    kw_acted_on_behalf_of_id = fields.Many2one("res.users", string="On behalf of", readonly=True)
    kw_waiting_hours = fields.Integer(string="Waiting (h)", compute="_compute_kw_waiting_hours")

    kw_document_name = fields.Char(string="Document", compute="_compute_kw_document")
    kw_document_amount = fields.Monetary(
        string="Amount", compute="_compute_kw_document", currency_field="kw_currency_id"
    )
    kw_currency_id = fields.Many2one("res.currency", compute="_compute_kw_document")

    @api.depends("model", "res_id")
    def _compute_kw_document(self):
        for rec in self:
            doc = rec._kw_document()
            rec.kw_document_name = doc.display_name if doc else False
            rec.kw_document_amount = doc.amount_total if doc and "amount_total" in doc else 0.0
            rec.kw_currency_id = doc.currency_id if doc and "currency_id" in doc else False

    def action_kw_open_document(self):
        """Approvals happen on the document itself, with its lines and chatter in view."""
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": self.model,
            "res_id": self.res_id,
            "view_mode": "form",
            "views": [(False, "form")],
        }

    @api.depends("kw_pending_since", "status")
    def _compute_kw_waiting_hours(self):
        now = fields.Datetime.now()
        for rec in self:
            if rec.status == "pending" and rec.kw_pending_since:
                rec.kw_waiting_hours = int((now - rec.kw_pending_since).total_seconds() // 3600)
            else:
                rec.kw_waiting_hours = 0

    # -- reviewers ---------------------------------------------------------------------
    def _kw_base_reviewers(self):
        """Reviewers before delegation: OCA's answer, minus the document's creator."""
        reviewers = super()._get_reviewers()
        creator = self._kw_document().create_uid
        if creator and creator in reviewers:
            reviewers -= creator
            if not reviewers and self.definition_id.kw_self_approval_group_id:
                reviewers = self.definition_id.kw_self_approval_group_id.users - creator
        return reviewers

    def _get_reviewers(self):
        reviewers = self._kw_base_reviewers()
        delegates = self.env["kw.approval.delegation"]._delegates_of(reviewers)
        for extra in delegates.values():
            reviewers |= extra
        creator = self._kw_document().create_uid
        return reviewers - creator if creator else reviewers

    def _kw_document(self):
        if not self.model or not self.res_id:
            return self.env["res.partner"].browse()
        return self.env[self.model].browse(self.res_id).exists()

    @api.model
    def _kw_recompute_reviewers(self):
        reviews = self.search([("status", "in", ("waiting", "pending"))])
        if reviews:
            self.env.add_to_compute(self._fields["reviewer_ids"], reviews)
            reviews._recompute_recordset(["reviewer_ids"])

    @api.depends("reviewer_ids")
    def _compute_todo_by(self):  # pylint: disable=missing-return
        """OCA shows the group name for group tiers. After a redirect or with a delegate the
        group is no longer who acts, so name the people instead."""
        super()._compute_todo_by()
        for rec in self:
            group_users = rec.reviewer_group_id.users
            if rec.reviewer_group_id and rec.reviewer_ids != group_users:
                rec.todo_by = ", ".join(rec.reviewer_ids.mapped("name"))

    # -- bookkeeping -------------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        for rec in records:
            vals = {}
            creator = rec._kw_document().create_uid
            if creator and creator in super(TierReview, rec)._get_reviewers():
                vals["kw_redirected_from_id"] = creator.id
            if rec.status == "pending":
                vals["kw_pending_since"] = fields.Datetime.now()
            if vals:
                rec.write(vals)
        return records

    def write(self, vals):
        res = super().write(vals)
        if vals.get("status") == "pending" and "kw_pending_since" not in vals:
            # OCA rewrites "pending" on reviews that already are; the clock starts only once.
            self.filtered(lambda r: not r.kw_pending_since).write(
                {"kw_pending_since": fields.Datetime.now()}
            )
        return res

    # -- escalation --------------------------------------------------------------------
    def _kw_deadline(self):
        """When this pending review breaches its SLA, on the company's working calendar."""
        self.ensure_one()
        hours = self.definition_id.kw_sla_hours
        if not hours or not self.kw_pending_since:
            return None
        start = pytz.utc.localize(self.kw_pending_since)
        calendar = (self.company_id or self.env.company).resource_calendar_id
        deadline = calendar.plan_hours(hours, start, compute_leaves=True) if calendar else None
        if not deadline:
            return self.kw_pending_since + timedelta(hours=hours)
        return deadline.astimezone(pytz.utc).replace(tzinfo=None)

    @api.model
    def _cron_kw_escalate(self, now=None):
        now = now or fields.Datetime.now()
        reviews = self.search(
            [
                ("status", "=", "pending"),
                ("kw_escalated_at", "=", False),
                ("kw_pending_since", "!=", False),
                ("definition_id.kw_sla_hours", ">", 0),
            ]
        )
        for review in reviews:
            deadline = review._kw_deadline()
            if deadline and deadline <= now:
                review._kw_escalate(now)

    def _kw_escalate(self, now):
        self.ensure_one()
        record = self._kw_document()
        if not record:
            return
        self.kw_escalated_at = now
        hours = self.definition_id.kw_sla_hours
        summary = self.env._("Approval overdue: %(doc)s", doc=record.display_name)
        for user in self.reviewer_ids:
            record.activity_schedule(
                "mail.mail_activity_data_todo",
                summary=summary,
                note=self.env._(
                    "Tier %(seq)s has waited more than %(h)s working hours.",
                    seq=self.sequence,
                    h=hours,
                ),
                user_id=user.id,
            )
        watchers = self.definition_id.kw_escalation_group_id.users
        body = self.env._(
            "Tier %(seq)s validation has waited more than %(h)s working hours. "
            "Escalated to %(who)s.",
            seq=self.sequence,
            h=hours,
            who=", ".join((self.reviewer_ids | watchers).mapped("name")),
        )
        record.message_post(
            body=body,
            partner_ids=watchers.partner_id.ids,
            subtype_xmlid="mail.mt_note",
            author_id=self.env.ref("base.partner_root").id,
        )
