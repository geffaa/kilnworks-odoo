from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_done(self, cancel_backorder=False):
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        self.env["kw.shopify.store"]._kw_schedule_stock_push(moves.product_id)
        return moves


class StockQuant(models.Model):
    _inherit = "stock.quant"

    def _apply_inventory(self, *args, **kwargs):
        res = super()._apply_inventory(*args, **kwargs)
        self.env["kw.shopify.store"]._kw_schedule_stock_push(self.product_id)
        return res
