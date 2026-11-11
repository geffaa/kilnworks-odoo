import logging
import pprint

from werkzeug.exceptions import Forbidden

from odoo import http
from odoo.exceptions import ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)


class MidtransController(http.Controller):
    _return_url = "/payment/midtrans/return"
    _notification_url = "/payment/midtrans/notification"

    @http.route(_return_url, type="http", methods=["GET"], auth="public")
    def midtrans_return(self, order_id=None, **_data):
        """Back from Snap. The query string is not trusted: the status comes from Midtrans."""
        if order_id:
            tx = request.env["payment.transaction"].sudo()._midtrans_find(order_id)
            if tx:
                try:
                    tx._midtrans_sync_status()
                except ValidationError:
                    _logger.exception("Could not sync Midtrans status for %s", order_id)
        return request.redirect("/payment/status")

    @http.route(_notification_url, type="http", methods=["POST"], auth="public", csrf=False)
    def midtrans_notification(self):
        """HTTP notification from Midtrans. 200 tells Midtrans to stop retrying."""
        data = request.get_json_data()
        _logger.info(
            "Midtrans notification:\n%s",
            pprint.pformat({k: v for k, v in data.items() if k != "signature_key"}),
        )
        try:
            tx = (
                request.env["payment.transaction"]
                .sudo()
                ._get_tx_from_notification_data("midtrans", data)
            )
            tx._midtrans_check_signature(data)
        except ValidationError as exc:
            _logger.warning("Rejected Midtrans notification: %s", exc)
            raise Forbidden() from exc
        tx._handle_notification_data("midtrans", data)
        return request.make_json_response({"status": "ok"})
