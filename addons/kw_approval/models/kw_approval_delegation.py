from odoo import api, fields, models
from odoo.exceptions import ValidationError


class KwApprovalDelegation(models.Model):
    _name = "kw.approval.delegation"
    _description = "Approval delegation"
    _inherit = ["mail.thread"]
    _order = "date_from desc, id desc"

    delegator_id = fields.Many2one(
        "res.users",
        string="Approver",
        required=True,
        default=lambda self: self.env.user,
        tracking=True,
    )
    delegate_id = fields.Many2one("res.users", string="Delegate to", required=True, tracking=True)
    date_from = fields.Date(string="From", required=True, default=fields.Date.context_today)
    date_to = fields.Date(string="To", required=True, tracking=True)
    reason = fields.Char()
    active = fields.Boolean(default=True)
    is_current = fields.Boolean(compute="_compute_is_current")

    _sql_constraints = [
        (
            "dates_ordered",
            "CHECK (date_to >= date_from)",
            "The end date must not be before the start.",
        ),
        ("not_self", "CHECK (delegator_id != delegate_id)", "You cannot delegate to yourself."),
    ]

    @api.depends("date_from", "date_to", "active")
    def _compute_is_current(self):
        today = fields.Date.context_today(self)
        for rec in self:
            rec.is_current = rec.active and rec.date_from <= today <= rec.date_to

    @api.depends("delegator_id", "delegate_id", "date_from", "date_to")
    def _compute_display_name(self):
        for rec in self:
            rec.display_name = self.env._(
                "%(who)s → %(to)s",
                who=rec.delegator_id.name or "",
                to=rec.delegate_id.name or "",
            )

    @api.constrains("delegator_id", "delegate_id", "date_from", "date_to", "active")
    def _check_no_loop(self):
        """A delegates to B while B delegates back to A over the same days would let
        either approve as the other forever; refuse it."""
        for rec in self.filtered("active"):
            reverse = self.search(
                [
                    ("id", "!=", rec.id),
                    ("delegator_id", "=", rec.delegate_id.id),
                    ("delegate_id", "=", rec.delegator_id.id),
                    ("date_from", "<=", rec.date_to),
                    ("date_to", ">=", rec.date_from),
                ],
                limit=1,
            )
            if reverse:
                raise ValidationError(
                    self.env._(
                        "%(b)s already delegates to %(a)s on overlapping days. "
                        "Delegations cannot point at each other.",
                        a=rec.delegator_id.name,
                        b=rec.delegate_id.name,
                    )
                )

    @api.model
    def _delegates_of(self, users, day=None):
        """Users currently allowed to act for `users`, as {delegator: delegates}."""
        day = day or fields.Date.context_today(self)
        delegations = self.sudo().search(
            [
                ("delegator_id", "in", users.ids),
                ("date_from", "<=", day),
                ("date_to", ">=", day),
            ]
        )
        result = {}
        for rec in delegations:
            result.setdefault(rec.delegator_id, self.env["res.users"])
            result[rec.delegator_id] |= rec.delegate_id
        return result

    # Open reviews must follow delegation changes: recompute their reviewers.
    @api.model_create_multi
    def create(self, vals_list):
        records = super().create(vals_list)
        records._refresh_open_reviews()
        return records

    def write(self, vals):
        res = super().write(vals)
        self._refresh_open_reviews()
        return res

    def unlink(self):
        res = super().unlink()
        self.env["kw.approval.delegation"]._refresh_open_reviews()
        return res

    def _refresh_open_reviews(self):
        self.env["tier.review"]._kw_recompute_reviewers()

    @api.model
    def _cron_refresh(self):
        """Delegations start and end at midnight; keep open reviews in step."""
        self.env["tier.review"]._kw_recompute_reviewers()
