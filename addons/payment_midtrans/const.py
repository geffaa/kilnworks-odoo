# Midtrans Snap endpoints (https://docs.midtrans.com, verify before production use).
SNAP_URL = {
    "test": "https://app.sandbox.midtrans.com",
    "enabled": "https://app.midtrans.com",
}
API_URL = {
    "test": "https://api.sandbox.midtrans.com",
    "enabled": "https://api.midtrans.com",
}

# Odoo payment method code -> Snap `enabled_payments` value
PAYMENT_METHODS_MAPPING = {
    "bank_bca": "bca_va",
    "bni": "bni_va",
    "bri": "bri_va",
    "bank_permata": "permata_va",
    "mandiri": "echannel",
    "gopay": "gopay",
    "shopeepay": "shopeepay",
    "qris": "other_qris",
    "card": "credit_card",
}
DEFAULT_PAYMENT_METHOD_CODES = list(PAYMENT_METHODS_MAPPING)

# Midtrans transaction_status -> Odoo transaction state
STATUS_MAPPING = {
    "done": ("settlement",),
    "pending": ("pending",),
    "cancel": ("cancel", "expire"),
    "error": ("deny", "failure"),
}
