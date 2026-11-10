from odoo import models


class StockMove(models.Model):
    _inherit = "stock.move"

    def _action_done(self, cancel_backorder=False):
        """Tell subscribers when a move takes a product from at-or-above to below its minimum."""
        orderpoints = self.env["stock.warehouse.orderpoint"].search(
            [("product_id", "in", self.product_id.ids)]
        )
        before = {
            op.id: op.product_id.with_context(location=op.location_id.id).qty_available
            for op in orderpoints
        }
        moves = super()._action_done(cancel_backorder=cancel_backorder)
        for op in orderpoints:
            after = op.product_id.with_context(location=op.location_id.id).qty_available
            if before[op.id] >= op.product_min_qty > after:
                self.env["kw.webhook.endpoint"]._emit(
                    "stock.low",
                    {
                        "sku": op.product_id.default_code,
                        "product": op.product_id.name,
                        "location": op.location_id.complete_name,
                        "on_hand": after,
                        "minimum": op.product_min_qty,
                    },
                )
        return moves
