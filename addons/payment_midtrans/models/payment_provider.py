import base64
import logging

import requests

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .. import const

_logger = logging.getLogger(__name__)


class PaymentProvider(models.Model):
    _inherit = "payment.provider"

    code = fields.Selection(
        selection_add=[("midtrans", "Midtrans")], ondelete={"midtrans": "set default"}
    )
    midtrans_merchant_id = fields.Char(string="Merchant ID", required_if_provider="midtrans")
    midtrans_client_key = fields.Char(string="Client Key", required_if_provider="midtrans")
    midtrans_server_key = fields.Char(
        string="Server Key", required_if_provider="midtrans", groups="base.group_system"
    )
    midtrans_snap_url_override = fields.Char(
        string="Snap URL override",
        groups="base.group_system",
        help="Only for offline demos against a mock. Leave empty to use Midtrans.",
    )
    midtrans_api_url_override = fields.Char(
        string="API URL override",
        groups="base.group_system",
        help="Only for offline demos against a mock. Leave empty to use Midtrans.",
    )

    @api.model
    def _get_compatible_providers(self, *args, is_validation=False, report=None, **kwargs):
        """Snap has no zero-amount card validation; hide Midtrans for validation operations."""
        providers = super()._get_compatible_providers(
            *args, is_validation=is_validation, report=report, **kwargs
        )
        if is_validation:
            providers = providers.filtered(lambda p: p.code != "midtrans")
        return providers

    def _get_supported_currencies(self):
        supported = super()._get_supported_currencies()
        if self.code == "midtrans":
            supported = supported.filtered(lambda c: c.name == "IDR")
        return supported

    def _get_default_payment_method_codes(self):
        codes = super()._get_default_payment_method_codes()
        if self.code != "midtrans":
            return codes
        return const.DEFAULT_PAYMENT_METHOD_CODES

    # -- API --------------------------------------------------------------------------
    def _midtrans_base(self, kind):
        self.ensure_one()
        provider = self.sudo()
        override = (
            provider.midtrans_snap_url_override
            if kind == "snap"
            else provider.midtrans_api_url_override
        )
        if override:
            return override.rstrip("/")
        mapping = const.SNAP_URL if kind == "snap" else const.API_URL
        return mapping["enabled" if self.state == "enabled" else "test"]

    def _midtrans_headers(self):
        key = f"{self.sudo().midtrans_server_key or ''}:".encode()
        return {
            "Authorization": "Basic " + base64.b64encode(key).decode(),
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    def _midtrans_request(self, kind, endpoint, payload=None, method="POST"):
        """Call Snap (`kind="snap"`) or the Core API (`kind="api"`)."""
        self.ensure_one()
        url = f"{self._midtrans_base(kind)}/{endpoint.lstrip('/')}"
        try:
            if method == "GET":
                response = requests.get(url, headers=self._midtrans_headers(), timeout=15)
            else:
                response = requests.post(
                    url, json=payload, headers=self._midtrans_headers(), timeout=15
                )
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout) as exc:
            _logger.exception("Midtrans unreachable at %s", url)
            raise ValidationError(_("Midtrans: %s", _("Could not reach Midtrans."))) from exc
        try:
            data = response.json()
        except ValueError:
            data = {}
        if response.status_code >= 400:
            messages = data.get("error_messages") or [
                data.get("status_message") or response.text[:200]
            ]
            _logger.warning("Midtrans error %s at %s: %s", response.status_code, url, messages)
            raise ValidationError(_("Midtrans: %s", "; ".join(str(m) for m in messages)))
        return data
