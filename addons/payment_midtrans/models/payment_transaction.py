import hashlib
import hmac
import logging
import re

from werkzeug import urls

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from .. import const
from ..controllers.main import MidtransController

_logger = logging.getLogger(__name__)


def midtrans_signature(order_id, status_code, gross_amount, server_key):
    """SHA512(order_id + status_code + gross_amount + server_key): how Midtrans signs data."""
    raw = f"{order_id}{status_code}{gross_amount}{server_key}".encode()
    return hashlib.sha512(raw).hexdigest()


class PaymentTransaction(models.Model):
    _inherit = "payment.transaction"

    midtrans_payment_type = fields.Char(readonly=True)
    midtrans_va_number = fields.Char(string="Virtual account", readonly=True)

    @api.model
    def _compute_reference(self, provider_code, prefix=None, separator="-", **kwargs):
        """Midtrans order ids allow letters, digits and - _ . ~ only (verify against the docs), so
        invoice names such as INV/2026/00391 become INV-2026-00391."""
        if provider_code == "midtrans":
            if not prefix:
                prefix = (
                    self.sudo()._compute_reference_prefix(provider_code, separator, **kwargs)
                    or None
                )
            if prefix:
                prefix = re.sub(r"[^A-Za-z0-9\-_.~]", "-", prefix)
        return super()._compute_reference(
            provider_code, prefix=prefix, separator=separator, **kwargs
        )

    def _midtrans_gross_amount(self):
        # IDR has no minor unit at Midtrans: send whole rupiah.
        return int(round(self.amount))

    def _get_specific_rendering_values(self, processing_values):
        res = super()._get_specific_rendering_values(processing_values)
        if self.provider_code != "midtrans":
            return res
        base_url = self.provider_id.get_base_url()
        first, last = (
            self.partner_name.split(" ", 1)
            if " " in (self.partner_name or "")
            else (self.partner_name, "")
        )
        enabled = const.PAYMENT_METHODS_MAPPING.get(self.payment_method_code)
        payload = {
            "transaction_details": {
                "order_id": self.reference,
                "gross_amount": self._midtrans_gross_amount(),
            },
            "customer_details": {
                "first_name": first or "",
                "last_name": last or "",
                "email": self.partner_email or "",
                "phone": self.partner_phone or "",
            },
            "callbacks": {"finish": urls.url_join(base_url, MidtransController._return_url)},
        }
        if enabled:
            payload["enabled_payments"] = [enabled]
        data = self.provider_id._midtrans_request("snap", "snap/v1/transactions", payload)
        self.provider_reference = data.get("token")
        return {"api_url": data["redirect_url"]}

    def _get_tx_from_notification_data(self, provider_code, notification_data):
        tx = super()._get_tx_from_notification_data(provider_code, notification_data)
        if provider_code != "midtrans" or len(tx) == 1:
            return tx
        reference = notification_data.get("order_id")
        if not reference:
            raise ValidationError(_("Midtrans: %s", _("Received data with missing order id.")))
        tx = self.search([("reference", "=", reference), ("provider_code", "=", "midtrans")])
        if not tx:
            raise ValidationError(
                _("Midtrans: no transaction found matching reference %s.", reference)
            )
        return tx

    def _midtrans_check_signature(self, data):
        """Signed data is trusted only if the signature matches and the amount is ours."""
        self.ensure_one()
        expected = midtrans_signature(
            data.get("order_id", ""),
            data.get("status_code", ""),
            data.get("gross_amount", ""),
            self.provider_id.sudo().midtrans_server_key or "",
        )
        if not hmac.compare_digest(expected, data.get("signature_key") or ""):
            raise ValidationError(_("Midtrans: %s", _("Invalid notification signature.")))
        try:
            amount = float(data.get("gross_amount") or 0)
        except ValueError:
            amount = -1
        if int(round(amount)) != self._midtrans_gross_amount():
            raise ValidationError(
                _(
                    "Midtrans: amount %(got)s does not match %(want)s.",
                    got=data.get("gross_amount"),
                    want=self._midtrans_gross_amount(),
                )
            )

    def _process_notification_data(self, notification_data):
        super()._process_notification_data(notification_data)
        if self.provider_code != "midtrans":
            return
        self._midtrans_check_signature(notification_data)
        self.provider_reference = notification_data.get("transaction_id") or self.provider_reference
        self._midtrans_update_payment_method(notification_data)

        status = (notification_data.get("transaction_status") or "").lower()
        fraud = (notification_data.get("fraud_status") or "accept").lower()
        if status == "capture":  # card: captured, but a fraud review may still be pending
            if fraud == "accept":
                self._set_done()
            else:
                self._set_pending(_("Card payment is under fraud review at Midtrans."))
        elif status in const.STATUS_MAPPING["done"]:
            self._set_done()
        elif status in const.STATUS_MAPPING["pending"]:
            self._set_pending()
        elif status in const.STATUS_MAPPING["cancel"]:
            self._set_canceled(_("Midtrans: the payment was %s.", status))
        elif status in const.STATUS_MAPPING["error"]:
            self._set_error(_("Midtrans declined the payment (status %s).", status))
        elif status in ("refund", "partial_refund"):
            _logger.info(
                "Midtrans refund notification for %s left for manual handling", self.reference
            )
        else:
            _logger.warning("Unknown Midtrans status %s for %s", status, self.reference)
            self._set_error(_("Midtrans: unknown payment status %s.", status))

    def _midtrans_update_payment_method(self, data):
        payment_type = data.get("payment_type") or ""
        code = {
            "gopay": "gopay",
            "shopeepay": "shopeepay",
            "qris": "qris",
            "credit_card": "card",
            "echannel": "mandiri",
        }.get(payment_type)
        if payment_type == "bank_transfer":
            if data.get("permata_va_number"):
                code = "bank_permata"
                self.midtrans_va_number = data["permata_va_number"]
            elif data.get("va_numbers"):
                va = data["va_numbers"][0]
                code = {"bca": "bank_bca", "bni": "bni", "bri": "bri"}.get(va.get("bank"))
                self.midtrans_va_number = va.get("va_number")
        self.midtrans_payment_type = payment_type or self.midtrans_payment_type
        method = self.env["payment.method"]._get_from_code(code) if code else False
        if method:
            self.payment_method_id = method

    def _midtrans_sync_status(self):
        """Ask Midtrans for the current status. Used on return from Snap, where the query string
        cannot be trusted and the notification may not have arrived (or cannot, on localhost)."""
        self.ensure_one()
        data = self.provider_id._midtrans_request(
            "api", f"v2/{self.reference}/status", method="GET"
        )
        if str(data.get("status_code")) == "404":
            return False
        self._handle_notification_data("midtrans", data)
        return True
