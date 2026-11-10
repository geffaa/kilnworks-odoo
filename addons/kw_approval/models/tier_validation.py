from odoo import models


class TierValidation(models.AbstractModel):
    _inherit = "tier.validation"

    def _validate_tier(self, tiers=False):
        """Record who a delegate approved for, after OCA marks the reviews approved."""
        before = (tiers or self.review_ids).filtered(lambda r: r.status != "approved")
        res = super()._validate_tier(tiers=tiers)
        user = self.env.user
        for review in before.filtered(lambda r: r.status == "approved" and r.done_by == user):
            principals = review._kw_base_reviewers()
            if user not in principals:
                delegations = self.env["kw.approval.delegation"]._delegates_of(principals)
                for principal, delegates in delegations.items():
                    if user in delegates:
                        review.kw_acted_on_behalf_of_id = principal
                        break
        return res

    def request_validation(self):
        res = super().request_validation()
        for rec in self:
            redirected = rec.review_ids.filtered("kw_redirected_from_id")
            for review in redirected:
                rec.message_post(
                    body=self.env._(
                        "Tier %(seq)s reviewer changed from %(old)s to %(new)s: "
                        "the creator of a document cannot approve it.",
                        seq=review.sequence,
                        old=review.kw_redirected_from_id.name,
                        new=", ".join(review.reviewer_ids.mapped("name")),
                    ),
                    subtype_xmlid="mail.mt_note",
                    author_id=self.env.ref("base.partner_root").id,
                )
        return res
