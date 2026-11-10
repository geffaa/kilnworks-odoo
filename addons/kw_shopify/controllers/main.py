import base64
import hashlib
import hmac
import json
import logging

from odoo import fields, http
from odoo.http import request

_logger = logging.getLogger(__name__)

MAX_BODY = 1024 * 1024  # Shopify order payloads are far below this


def shopify_signature(secret, body):
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


class ShopifyWebhook(http.Controller):
    @http.route(
        "/kw_shopify/webhook/<int:store_id>",
        type="http",
        auth="public",
        methods=["POST"],
        csrf=False,
        save_session=False,
    )
    def webhook(self, store_id, **_kw):
        raw = request.httprequest.get_data(cache=False)
        if len(raw) > MAX_BODY:
            return request.make_response("payload too large", status=413)
        # sudo: public route; nothing is read or written before the signature is checked.
        store = request.env["kw.shopify.store"].sudo().browse(store_id).exists()
        if not store or not store.active or not store.webhook_secret:
            return request.make_response("unknown store", status=404)
        sent = request.httprequest.headers.get("X-Shopify-Hmac-Sha256", "")
        if not hmac.compare_digest(shopify_signature(store.webhook_secret, raw), sent):
            _logger.warning("Shopify webhook with bad signature for store %s", store.id)
            return request.make_response("invalid signature", status=401)

        headers = request.httprequest.headers
        webhook_id = headers.get("X-Shopify-Webhook-Id") or headers.get("X-Shopify-Event-Id")
        topic = headers.get("X-Shopify-Topic", "")
        if not webhook_id:
            return request.make_response("missing webhook id", status=400)
        try:
            payload = json.loads(raw)
        except ValueError:
            return request.make_response("invalid json", status=400)

        Event = request.env["kw.shopify.event"].sudo()
        existing = Event.search(
            [("store_id", "=", store.id), ("webhook_id", "=", webhook_id)], limit=1
        )
        if existing:
            existing.write(
                {
                    "duplicate_count": existing.duplicate_count + 1,
                    "last_duplicate_at": fields.Datetime.now(),
                }
            )
            return request.make_response("duplicate", status=200)
        event = Event.create(
            {
                "store_id": store.id,
                "webhook_id": webhook_id,
                "topic": topic,
                "order_name": payload.get("name"),
                "order_gid": payload.get("admin_graphql_api_id")
                or (f"gid://shopify/Order/{payload['id']}" if payload.get("id") else False),
                "payload": payload,
            }
        )
        event._log("Received, signature checked, stored")
        event._enqueue()
        return request.make_response("ok", status=200)
