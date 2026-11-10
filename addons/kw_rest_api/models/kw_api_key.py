import hashlib
import hmac
import secrets

from odoo import api, fields, models
from odoo.exceptions import UserError

RATE_LIMIT_PER_MINUTE = 60


def hash_secret(secret):
    return hashlib.sha256(secret.encode()).hexdigest()


class KwApiScope(models.Model):
    _name = "kw.api.scope"
    _description = "API scope"
    _order = "code"
    _rec_name = "code"

    code = fields.Char(required=True)
    description = fields.Char()

    _sql_constraints = [("code_uniq", "unique(code)", "Scope codes are unique.")]


class KwApiKey(models.Model):
    _name = "kw.api.key"
    _description = "API key"
    _inherit = ["mail.thread"]
    _order = "create_date desc"

    name = fields.Char(required=True, help="Who uses it, e.g. Warehouse scanner app", tracking=True)
    user_id = fields.Many2one(
        "res.users",
        string="Acts as",
        required=True,
        help="Requests run with this user's access rights and record rules.",
        tracking=True,
    )
    key_prefix = fields.Char(readonly=True, index=True, copy=False)
    key_hash = fields.Char(readonly=True, groups="base.group_system", copy=False)
    scope_ids = fields.Many2many("kw.api.scope", string="Scopes", tracking=True)
    expires_at = fields.Datetime(string="Expires")
    last_used_at = fields.Datetime(readonly=True)
    active = fields.Boolean(default=True, tracking=True)

    _sql_constraints = [("prefix_uniq", "unique(key_prefix)", "Key prefixes must be unique.")]

    def action_generate(self):
        """Create a new secret and show it once. Only its hash is stored."""
        self.ensure_one()
        prefix = secrets.token_hex(4)
        secret = secrets.token_urlsafe(32)
        full = f"kw_{prefix}_{secret}"
        self.sudo().write({"key_prefix": prefix, "key_hash": hash_secret(full)})
        self.message_post(body=self.env._("A new key was generated (kw_%s_…).", prefix))
        wizard = self.env["kw.api.key.show"].create({"key_id": self.id, "key": full})
        return {
            "type": "ir.actions.act_window",
            "res_model": "kw.api.key.show",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    def action_revoke(self):
        self.write({"active": False})

    @api.model
    def _authenticate(self, raw_key):
        """Return the active, unexpired key for a raw `kw_<prefix>_<secret>` string, or empty."""
        parts = (raw_key or "").split("_", 2)
        if len(parts) != 3 or parts[0] != "kw":
            return self.browse()
        key = self.sudo().search([("key_prefix", "=", parts[1])], limit=1)
        if not key or not hmac.compare_digest(key.key_hash or "", hash_secret(raw_key)):
            return self.browse()
        if key.expires_at and key.expires_at < fields.Datetime.now():
            return self.browse()
        return key

    def _has_scope(self, code):
        return code in self.scope_ids.mapped("code")

    def _hit_rate_limit(self):
        """Count this request in the current minute. True when over the limit."""
        self.ensure_one()
        window = fields.Datetime.now().replace(second=0, microsecond=0)
        self.env.cr.execute(
            """
            INSERT INTO kw_api_rate_bucket (key_id, window_start, count)
            VALUES (%s, %s, 1)
            ON CONFLICT (key_id, window_start) DO UPDATE SET count = kw_api_rate_bucket.count + 1
            RETURNING count
            """,
            (self.id, window),
        )
        count = self.env.cr.fetchone()[0]
        return count > RATE_LIMIT_PER_MINUTE

    def write(self, vals):
        if (
            "key_hash" in vals
            and not self.env.su
            and not self.env.user.has_group("base.group_system")
        ):
            raise UserError(self.env._("Generate keys with the button; hashes cannot be edited."))
        return super().write(vals)


class KwApiRateBucket(models.Model):
    _name = "kw.api.rate.bucket"
    _description = "API request counter per key and minute"
    _log_access = False

    key_id = fields.Many2one("kw.api.key", required=True, ondelete="cascade", index=True)
    window_start = fields.Datetime(required=True)
    count = fields.Integer(default=0)

    _sql_constraints = [("window_uniq", "unique(key_id, window_start)", "One counter per minute.")]

    @api.autovacuum
    def _gc_old_buckets(self):
        cutoff = fields.Datetime.subtract(fields.Datetime.now(), hours=1)
        self.search([("window_start", "<", cutoff)]).unlink()
