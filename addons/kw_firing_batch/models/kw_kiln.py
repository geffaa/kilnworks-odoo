from odoo import fields, models


class KwKiln(models.Model):
    _name = "kw.kiln"
    _description = "Kiln"

    name = fields.Char(required=True)
    kiln_type = fields.Selection([("gas", "Gas"), ("electric", "Electric")], required=True, default="gas")
    capacity_pcs = fields.Integer(string="Capacity (pieces)")
    active = fields.Boolean(default=True)
