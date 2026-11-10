from odoo import models


class SaleOrder(models.Model):
    _inherit = "sale.order"

    def action_confirm(self):
        res = super().action_confirm()
        for order in self:
            self.env["kw.webhook.endpoint"]._emit("order.confirmed", order._kw_api_payload())
        return res

    def _kw_api_payload(self, with_lines=True):
        self.ensure_one()
        data = {
            "id": self.id,
            "name": self.name,
            "state": self.state,
            "date": self.date_order.isoformat() if self.date_order else None,
            "partner": {"id": self.partner_id.id, "name": self.partner_id.name},
            "currency": self.currency_id.name,
            "amount_untaxed": self.amount_untaxed,
            "amount_total": self.amount_total,
            "client_ref": self.client_order_ref or None,
        }
        if "kw_channel" in self._fields:
            data["channel"] = self.kw_channel
        if with_lines:
            data["lines"] = [
                {
                    "sku": line.product_id.default_code,
                    "product": line.product_id.name,
                    "quantity": line.product_uom_qty,
                    "price_unit": line.price_unit,
                    "discount": line.discount,
                    "subtotal": line.price_subtotal,
                }
                for line in self.order_line.filtered(lambda line: not line.display_type)
            ]
        return data
