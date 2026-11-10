from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    kw_hs_code = fields.Char(
        string="HS code", help="Customs tariff code, e.g. 6912.00 for stoneware tableware"
    )
    kw_carton_qty = fields.Integer(string="Units per carton", default=0)
    kw_carton_tare_kg = fields.Float(
        string="Carton tare (kg)", default=1.2, help="Empty carton plus packing material"
    )
    kw_carton_dims = fields.Char(string="Carton size (cm)", default="40 × 30 × 30")
