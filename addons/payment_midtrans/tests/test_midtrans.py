from unittest.mock import MagicMock, patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import MidtransCommon

REQUESTS = "odoo.addons.payment_midtrans.models.payment_provider.requests"


def response(status=201, body=None):
    mock = MagicMock(status_code=status, text="")
    mock.json.return_value = body or {}
    return mock


@tagged("post_install", "-at_install")
class TestMidtrans(MidtransCommon):
    def test_only_idr(self):
        self.assertEqual(self.midtrans._get_supported_currencies().mapped("name"), ["IDR"])

    def test_reference_is_midtrans_safe(self):
        reference = self.env["payment.transaction"]._compute_reference(
            "midtrans", prefix="INV/2026/00391"
        )
        self.assertEqual(reference, "INV-2026-00391")

    def test_snap_request_and_redirect(self):
        tx = self._create_transaction("redirect")
        body = {
            "token": "66e4fa55-fdac-4ef9-91b5-733b97d1b862",
            "redirect_url": "https://app.sandbox.midtrans.com/snap/v4/redirection/66e4fa55",
        }
        with patch(f"{REQUESTS}.post", return_value=response(201, body)) as post:
            values = tx._get_specific_rendering_values(None)
        self.assertEqual(values["api_url"], body["redirect_url"])
        self.assertEqual(tx.provider_reference, body["token"])
        url = post.call_args.args[0]
        self.assertEqual(url, "https://app.sandbox.midtrans.com/snap/v1/transactions")
        sent = post.call_args.kwargs["json"]
        self.assertRegex(tx.midtrans_order_id, rf"^{tx.reference}-[0-9a-f]{{6}}$")
        self.assertEqual(
            sent["transaction_details"],
            {"order_id": tx.midtrans_order_id, "gross_amount": 21420000},
        )
        self.assertIsInstance(sent["transaction_details"]["gross_amount"], int)
        self.assertEqual(sent["enabled_payments"], ["bca_va"])
        self.assertTrue(sent["callbacks"]["finish"].endswith("/payment/midtrans/return"))
        auth = post.call_args.kwargs["headers"]["Authorization"]
        self.assertTrue(auth.startswith("Basic "))

    def test_enabled_state_uses_production(self):
        self.midtrans.state = "enabled"
        self.assertEqual(self.midtrans._midtrans_base("snap"), "https://app.midtrans.com")
        self.assertEqual(self.midtrans._midtrans_base("api"), "https://api.midtrans.com")

    @mute_logger("odoo.addons.payment_midtrans.models.payment_provider")
    def test_snap_error_message_surfaces(self):
        tx = self._create_transaction("redirect")
        body = {"error_messages": ["transaction_details.order_id has already been taken"]}
        with patch(f"{REQUESTS}.post", return_value=response(400, body)):
            with self.assertRaisesRegex(ValidationError, "already been taken"):
                tx._get_specific_rendering_values(None)

    def test_status_mapping(self):
        cases = {
            "settlement": "done",
            "pending": "pending",
            "expire": "cancel",
            "cancel": "cancel",
            "deny": "error",
        }
        for i, (status, state) in enumerate(cases.items()):
            reference = f"INV-2026-0040{i}"
            tx = self._create_transaction("redirect", reference=reference)
            tx._handle_notification_data("midtrans", self.notification(status, reference=reference))
            self.assertEqual(tx.state, state, status)

    def test_card_capture_waits_for_fraud_review(self):
        tx = self._create_transaction("redirect")
        data = self.notification("capture", payment_type="credit_card", fraud_status="challenge")
        tx._handle_notification_data("midtrans", data)
        self.assertEqual(tx.state, "pending")
        tx._handle_notification_data(
            "midtrans",
            self.notification("capture", payment_type="credit_card", fraud_status="accept"),
        )
        self.assertEqual(tx.state, "done")
        self.assertEqual(tx.payment_method_id, self.env.ref("payment.payment_method_card"))

    def test_va_number_and_method_recorded(self):
        tx = self._create_transaction(
            "redirect", payment_method_id=self.env.ref("payment.payment_method_qris").id
        )
        tx._handle_notification_data("midtrans", self.notification("pending"))
        self.assertEqual(tx.midtrans_va_number, "812785002530231")
        self.assertEqual(tx.payment_method_id, self.env.ref("payment.payment_method_bank_bca"))

    def test_return_syncs_from_status_api(self):
        tx = self._create_transaction("redirect")
        with patch(
            f"{REQUESTS}.get", return_value=response(200, self.notification("settlement"))
        ) as get:
            tx._midtrans_sync_status()
        self.assertTrue(get.call_args.args[0].endswith(f"/v2/{tx.reference}/status"))
        self.assertEqual(tx.state, "done")

    def test_order_id_unique_per_attempt(self):
        """A rebuilt database reuses invoice references; Midtrans must still see a new order id."""
        first = self._create_transaction("redirect")
        second = self._create_transaction("redirect", reference=f"{first.reference}-retry")
        body = {
            "token": "t",
            "redirect_url": "https://app.sandbox.midtrans.com/snap/v4/redirection/t",
        }
        with patch(f"{REQUESTS}.post", return_value=response(201, body)) as post:
            first._get_specific_rendering_values(None)
            second._get_specific_rendering_values(None)
        sent = [c.kwargs["json"]["transaction_details"]["order_id"] for c in post.call_args_list]
        self.assertEqual(len(set(sent)), 2)
        self.assertTrue(sent[0].startswith(first.reference + "-") and sent[0] != first.reference)
        self.assertEqual(self.env["payment.transaction"]._midtrans_find(sent[1]), second)

    def test_status_uses_midtrans_order_id(self):
        tx = self._create_transaction("redirect")
        tx.midtrans_order_id = f"{tx.reference}-a1b2c3"
        data = dict(self.notification("settlement", reference=tx.midtrans_order_id))
        with patch(f"{REQUESTS}.get", return_value=response(200, data)) as get:
            tx._midtrans_sync_status()
        self.assertTrue(get.call_args.args[0].endswith(f"/v2/{tx.midtrans_order_id}/status"))
        self.assertEqual(tx.state, "done")
