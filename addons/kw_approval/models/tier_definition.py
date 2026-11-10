from odoo import fields, models


class TierDefinition(models.Model):
    _inherit = "tier.definition"

    kw_self_approval_group_id = fields.Many2one(
        "res.groups",
        string="If the creator is the reviewer, ask",
        help="A document's creator never approves it. When the only reviewer for this tier "
        "is the creator, the review goes to this group instead.",
    )
    kw_sla_hours = fields.Integer(
        string="Escalate after (working hours)",
        default=24,
        help="Pending reviews older than this, counted on the company's working calendar, "
        "get an activity for the reviewers and a note to the escalation group. 0 disables it.",
    )
    kw_escalation_group_id = fields.Many2one(
        "res.groups",
        string="Escalate to",
        help="Users told when a review on this tier waits too long.",
    )
