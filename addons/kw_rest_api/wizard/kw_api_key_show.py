from odoo import fields, models


class KwApiKeyShow(models.TransientModel):
    _name = "kw.api.key.show"
    _description = "Show a new API key once"

    key_id = fields.Many2one("kw.api.key", string="API key", readonly=True)
    key = fields.Char(string="Secret", readonly=True)
