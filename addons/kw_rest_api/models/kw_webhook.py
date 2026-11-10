import hashlib
import hmac
import json
import logging
import secrets
import uuid
from datetime import timedelta

import requests

from odoo import api, fields, models

_logger = logging.getLogger(__name__)

EVENTS = [("order.confirmed", "Sale order confirmed"), ("stock.low", "Stock below minimum")]
# Seconds before attempt 2, 3, 4, 5, 6. After the sixth failure the delivery is marked failed.
RETRY_SCHEDULE = [60, 300, 1800, 7200, 21600]
TIMEOUT = 10


def sign(secret, body):
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


class KwWebhookEndpoint(models.Model):
    _name = "kw.webhook.endpoint"
    _description = "Outgoing webhook endpoint"
    _inherit = ["mail.thread"]

    name = fields.Char(required=True)
    url = fields.Char(required=True, tracking=True)
    event_order_confirmed = fields.Boolean(string="order.confirmed", default=True)
    event_stock_low = fields.Boolean(string="stock.low", default=True)
    secret = fields.Char(
        groups="base.group_system", copy=False, default=lambda s: secrets.token_urlsafe(24)
    )
    active = fields.Boolean(default=True)
    delivery_ids = fields.One2many("kw.webhook.delivery", "endpoint_id")
    failed_count = fields.Integer(compute="_compute_failed_count")

    def _compute_failed_count(self):
        for endpoint in self:
            endpoint.failed_count = len(
                endpoint.delivery_ids.filtered(lambda d: d.state == "failed")
            )

    def _listens(self, event):
        return {"order.confirmed": self.event_order_confirmed, "stock.low": self.event_stock_low}[
            event
        ]

    @api.model
    def _emit(self, event, payload):
        """Queue one delivery per endpoint listening to `event`."""
        endpoints = self.sudo().search([]).filtered(lambda e: e._listens(event))
        deliveries = self.env["kw.webhook.delivery"].sudo()
        for endpoint in endpoints:
            delivery = deliveries.create(
                {"endpoint_id": endpoint.id, "event": event, "payload": payload}
            )
            delivery._enqueue()
            deliveries |= delivery
        return deliveries


class KwWebhookDelivery(models.Model):
    _name = "kw.webhook.delivery"
    _description = "Outgoing webhook delivery"
    _order = "create_date desc, id desc"
    _rec_name = "delivery_uid"

    endpoint_id = fields.Many2one(
        "kw.webhook.endpoint", required=True, ondelete="cascade", index=True
    )
    event = fields.Selection(EVENTS, required=True)
    delivery_uid = fields.Char(
        required=True, default=lambda s: str(uuid.uuid4()), readonly=True, copy=False
    )
    payload = fields.Json(required=True)
    state = fields.Selection(
        [("pending", "Pending"), ("sent", "Sent"), ("retrying", "Retrying"), ("failed", "Failed")],
        default="pending",
        required=True,
        index=True,
    )
    attempts = fields.Integer(readonly=True)
    next_attempt_at = fields.Datetime(readonly=True)
    last_status_code = fields.Integer(readonly=True)
    last_error = fields.Char(readonly=True)

    _sql_constraints = [("uid_uniq", "unique(delivery_uid)", "Delivery ids are unique.")]

    def _enqueue(self, eta=None):
        for delivery in self:
            delivery.with_delay(
                eta=eta, channel="root.kw_webhook", description=f"Webhook {delivery.event}"
            ).send()

    def _body(self):
        return json.dumps(
            {
                "id": self.delivery_uid,
                "event": self.event,
                "created_at": self.create_date.isoformat(),
                "data": self.payload,
            },
            separators=(",", ":"),
        ).encode()

    def send(self):
        """One attempt. Failures schedule the next attempt; the sixth failure is final."""
        self.ensure_one()
        if self.state == "sent":
            return "already sent"
        body = self._body()
        endpoint = self.endpoint_id.sudo()
        self.attempts += 1
        try:
            response = requests.post(
                endpoint.url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Kw-Event": self.event,
                    "X-Kw-Delivery": self.delivery_uid,
                    "X-Kw-Signature": sign(endpoint.secret or "", body),
                },
                timeout=TIMEOUT,
            )
            ok, code, error = 200 <= response.status_code < 300, response.status_code, ""
            if not ok:
                error = f"HTTP {response.status_code}"
        except requests.RequestException as exc:
            ok, code, error = False, 0, str(exc)[:200]
        if ok:
            self.write(
                {
                    "state": "sent",
                    "last_status_code": code,
                    "last_error": False,
                    "next_attempt_at": False,
                }
            )
            return "sent"
        if self.attempts > len(RETRY_SCHEDULE):
            self.write(
                {
                    "state": "failed",
                    "last_status_code": code,
                    "last_error": error,
                    "next_attempt_at": False,
                }
            )
            return "failed"
        wait = RETRY_SCHEDULE[self.attempts - 1]
        self.write(
            {
                "state": "retrying",
                "last_status_code": code,
                "last_error": error,
                "next_attempt_at": fields.Datetime.now() + timedelta(seconds=wait),
            }
        )
        # Raising would roll back this bookkeeping, so schedule the next attempt as a new job.
        self._enqueue(eta=wait)
        return f"retry in {wait}s"

    def action_resend(self):
        """Send the same payload again under the same delivery id, so receivers can dedupe."""
        for delivery in self:
            delivery.write({"state": "pending", "attempts": 0, "next_attempt_at": False})
            delivery._enqueue()
        return True
