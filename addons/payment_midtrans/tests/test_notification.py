import json

from odoo.tests import HttpCase, tagged
from odoo.tools import mute_logger

from .common import MidtransCommon


@tagged("post_install", "-at_install")
class TestNotification(MidtransCommon, HttpCase):
    def _post(self, data):
        return self.url_open(
            "/payment/midtrans/notification",
            data=json.dumps(data),
            headers={"Content-Type": "application/json"},
        )

    @mute_logger("odoo.addons.payment_midtrans.controllers.main")
    def test_settlement_marks_done(self):
        tx = self._create_transaction("redirect")
        response = self._post(self.notification("settlement"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(tx.state, "done")

    @mute_logger("odoo.addons.payment_midtrans.controllers.main")
    def test_repeated_notification_is_harmless(self):
        tx = self._create_transaction("redirect")
        self._post(self.notification("settlement"))
        response = self._post(self.notification("settlement"))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(tx.state, "done")
        self.assertEqual(
            self.env["payment.transaction"].search_count([("reference", "=", tx.reference)]), 1
        )

    @mute_logger("odoo.addons.payment_midtrans.controllers.main", "odoo.http")
    def test_bad_signature_forbidden(self):
        tx = self._create_transaction("redirect")
        response = self._post(self.notification("settlement", key="not-the-server-key"))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(tx.state, "draft")

    @mute_logger("odoo.addons.payment_midtrans.controllers.main", "odoo.http")
    def test_amount_mismatch_forbidden(self):
        """A correctly signed notification for a different amount is still refused."""
        tx = self._create_transaction("redirect")
        response = self._post(self.notification("settlement", amount=1000))
        self.assertEqual(response.status_code, 403)
        self.assertEqual(tx.state, "draft")

    @mute_logger("odoo.addons.payment_midtrans.controllers.main", "odoo.http")
    def test_unknown_order_forbidden(self):
        response = self._post(self.notification("settlement", reference="INV-NOPE"))
        self.assertEqual(response.status_code, 403)
