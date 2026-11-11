from odoo import _, api, fields, models
from odoo.exceptions import UserError


class KwFiringBatch(models.Model):
    _name = "kw.firing.batch"
    _description = "Firing batch"
    _inherit = ["mail.thread"]
    _order = "fired_on desc, id desc"

    # 17.0 dropped `states=` on fields; read-only-when-done now lives in the views.
    name = fields.Char(default="/", readonly=True, copy=False)
    kiln_id = fields.Many2one("kw.kiln", required=True)
    fired_on = fields.Date(required=True, default=fields.Date.context_today)
    peak_temp = fields.Integer(string="Peak temperature (°C)")
    duration_h = fields.Float(string="Duration (h)")
    state = fields.Selection(
        [("draft", "Draft"), ("in_kiln", "In kiln"), ("done", "Done"), ("rejected", "Rejected")],
        default="draft",
        tracking=True,
    )
    line_ids = fields.One2many("kw.firing.batch.line", "batch_id")
    lot_ids = fields.One2many("stock.lot", "firing_batch_id", string="Lots")
    defect_rate = fields.Float(compute="_compute_defect_rate", store=True, string="Defect rate (%)")
    note = fields.Text()

    @api.depends("line_ids.qty_loaded", "line_ids.qty_good")
    def _compute_defect_rate(self):
        for batch in self:
            loaded = sum(batch.line_ids.mapped("qty_loaded"))
            good = sum(batch.line_ids.mapped("qty_good"))
            batch.defect_rate = round((loaded - good) / loaded * 100, 1) if loaded else 0.0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("name", "/") == "/":
                vals["name"] = self.env["ir.sequence"].next_by_code("kw.firing.batch") or "/"
        return super().create(vals_list)

    # name_get() is gone in 18.0; display_name is a regular computed field.
    @api.depends("name", "kiln_id.name", "peak_temp")
    def _compute_display_name(self):
        for batch in self:
            parts = [batch.name or ""]
            if batch.kiln_id:
                parts.append(batch.kiln_id.name)
            if batch.peak_temp:
                parts.append(f"{batch.peak_temp} °C")
            batch.display_name = " · ".join(parts)

    def action_start(self):
        self.write({"state": "in_kiln"})

    def action_done(self):
        for batch in self:
            if not batch.peak_temp:
                raise UserError(_("Record the peak temperature before closing %s.", batch.name))
        self.write({"state": "done"})

    def action_reject(self):
        self.write({"state": "rejected"})


class KwFiringBatchLine(models.Model):
    _name = "kw.firing.batch.line"
    _description = "Firing batch load"

    batch_id = fields.Many2one("kw.firing.batch", required=True, ondelete="cascade")
    product_id = fields.Many2one("product.product", required=True)
    qty_loaded = fields.Integer(string="Loaded")
    qty_good = fields.Integer(string="Good")
