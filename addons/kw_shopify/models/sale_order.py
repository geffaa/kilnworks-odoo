from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    kw_channel = fields.Selection(
        [("b2b", "B2B"), ("shopify", "Shopify")], string="Channel", default="b2b", index=True
    )
    kw_shopify_store_id = fields.Many2one("kw.shopify.store", string="Shopify store", readonly=True)
    kw_shopify_order_gid = fields.Char(string="Shopify order", readonly=True, copy=False)

    _sql_constraints = [
        (
            "kw_shopify_order_uniq",
            "unique(kw_shopify_store_id, kw_shopify_order_gid)",
            "This Shopify order is already imported.",
        )
    ]
