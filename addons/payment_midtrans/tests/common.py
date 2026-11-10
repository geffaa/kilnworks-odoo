from odoo.addons.payment.tests.common import PaymentCommon

from ..models.payment_transaction import midtrans_signature

SERVER_KEY = "SB-Mid-server-TESTKEY"


class MidtransCommon(PaymentCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.currency = cls._prepare_currency("IDR")
        cls.midtrans = cls._prepare_provider(
            "midtrans",
            update_values={
                "midtrans_merchant_id": "G000000001",
                "midtrans_client_key": "SB-Mid-client-TESTKEY",
                "midtrans_server_key": SERVER_KEY,
            },
        )
        cls.provider = cls.midtrans
        cls.payment_method = cls.env.ref("payment.payment_method_bank_bca")
        cls.payment_method_id = cls.payment_method.id
        cls.amount = 21420000
        cls.reference = "INV-2026-00391"

    def notification(
        self, status="settlement", amount=None, reference=None, key=SERVER_KEY, **extra
    ):
        gross = f"{amount if amount is not None else self.amount:.2f}"
        reference = reference or self.reference
        status_code = {"settlement": "200", "capture": "200", "pending": "201"}.get(status, "202")
        data = {
            "transaction_status": status,
            "status_code": status_code,
            "gross_amount": gross,
            "order_id": reference,
            "transaction_id": "9aed5972-5b6a-401e-894b-a32c91ed1a3a",
            "payment_type": "bank_transfer",
            "va_numbers": [{"bank": "bca", "va_number": "812785002530231"}],
            "signature_key": midtrans_signature(reference, status_code, gross, key),
        }
        data.update(extra)
        return data
