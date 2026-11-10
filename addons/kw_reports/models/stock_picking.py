import math

from odoo import _, models
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _kw_cartons(self):
        """Cartons as the warehouse packs them: one product per carton, full cartons first.

        Uses real packages when the picking has them; otherwise derives cartons from each
        product's units per carton. Returns a list of dicts in carton order.
        """
        self.ensure_one()
        cartons = []
        lines = self.move_ids.filtered(lambda m: m.state != "cancel")
        for move in lines:
            product = move.product_id
            tmpl = product.product_tmpl_id
            qty = int(move.quantity or move.product_uom_qty)
            per = tmpl.kw_carton_qty or qty or 1
            lots = ", ".join(sorted(set(move.move_line_ids.lot_id.mapped("name")))) or ""
            remaining = qty
            for _i in range(math.ceil(qty / per) if qty else 0):
                units = min(per, remaining)
                remaining -= units
                net = round(units * (product.weight or 0.0), 2)
                cartons.append(
                    {
                        "product": product,
                        "hs_code": tmpl.kw_hs_code or "",
                        "units": units,
                        "net_kg": net,
                        "gross_kg": round(net + tmpl.kw_carton_tare_kg, 2),
                        "dims": tmpl.kw_carton_dims or "",
                        "lots": lots,
                    }
                )
        for number, carton in enumerate(cartons, start=1):
            carton["number"] = number
        return cartons

    def _kw_packing_totals(self):
        cartons = self._kw_cartons()
        return {
            "cartons": len(cartons),
            "units": sum(c["units"] for c in cartons),
            "net_kg": round(sum(c["net_kg"] for c in cartons), 2),
            "gross_kg": round(sum(c["gross_kg"] for c in cartons), 2),
        }

    def action_kw_print_packing_list(self):
        missing = self.move_ids.product_id.filtered(lambda p: not p.kw_hs_code)
        if missing:
            raise UserError(
                _(
                    "Add an HS code before printing the packing list: %s",
                    ", ".join(missing.mapped("display_name")),
                )
            )
        return self.env.ref("kw_reports.action_report_packing_list").report_action(self)
