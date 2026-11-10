from odoo import api, fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    kw_max_discount = fields.Float(
        string="Largest line discount (%)",
        compute="_compute_kw_max_discount",
        store=True,
        digits="Discount",
    )

    @api.depends("order_line.discount")
    def _compute_kw_max_discount(self):
        for order in self:
            order.kw_max_discount = max(order.order_line.mapped("discount") or [0.0])
