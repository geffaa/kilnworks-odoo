from odoo import api, fields, models


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    kw_amount_company = fields.Monetary(
        string="Total in company currency",
        currency_field="company_currency_id",
        compute="_compute_kw_amount_company",
        store=True,
        help="Order total converted at the order date. Approval limits compare against this, "
        "so a USD order cannot slip under an IDR limit.",
    )
    company_currency_id = fields.Many2one(related="company_id.currency_id")

    @api.depends("amount_total", "currency_id", "date_order", "company_id")
    def _compute_kw_amount_company(self):
        for order in self:
            order.kw_amount_company = order.currency_id._convert(
                order.amount_total,
                order.company_id.currency_id,
                order.company_id,
                fields.Date.to_date(order.date_order) or fields.Date.context_today(order),
            )
