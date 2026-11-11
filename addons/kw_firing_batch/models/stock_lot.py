from odoo import fields, models


class StockLot(models.Model):
    _inherit = "stock.lot"

    firing_batch_id = fields.Many2one("kw.firing.batch", string="Firing batch")
