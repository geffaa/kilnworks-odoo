"""A stand-in for Midtrans Snap and the status API, for offline demos. Not affiliated with Midtrans.

- POST /snap/v1/transactions    -> token + redirect_url to a local payment page
- GET  /snap/v4/redirection/<t> -> a plain page with "Pay" and "Let it expire" buttons
- POST /pay/<t>                 -> sends a signed HTTP notification to Odoo, then returns the
                                   browser to the finish URL
- GET  /v2/<order_id>/status    -> current status, signed like a notification

Standard library only. Env: PUBLIC_URL (browser-facing), NOTIFY_URL (Odoo notification endpoint),
MIDTRANS_SERVER_KEY (must match the provider's server key).
"""

import hashlib
import html
import json
import os
import urllib.parse
import urllib.request
import uuid
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

PUBLIC_URL = os.environ.get("PUBLIC_URL", "http://localhost:8090")
NOTIFY_URL = os.environ.get("NOTIFY_URL", "http://odoo:8069/payment/midtrans/notification")
SERVER_KEY = os.environ.get("MIDTRANS_SERVER_KEY", "SB-Mid-server-kilnworks-demo")
TX = {}  # token -> transaction
BY_ORDER = {}  # order_id -> token

CHANNEL = {
    "bca_va": ("bank_transfer", {"va_numbers": [{"bank": "bca", "va_number": "12785002530231"}]}),
    "bni_va": ("bank_transfer", {"va_numbers": [{"bank": "bni", "va_number": "9881278500253023"}]}),
    "bri_va": ("bank_transfer", {"va_numbers": [{"bank": "bri", "va_number": "127850025302312"}]}),
    "permata_va": ("bank_transfer", {"permata_va_number": "8562000025302312"}),
    "echannel": ("echannel", {"bill_key": "702253023123", "biller_code": "70012"}),
    "gopay": ("gopay", {}),
    "shopeepay": ("shopeepay", {}),
    "other_qris": ("qris", {}),
    "credit_card": ("credit_card", {"fraud_status": "accept", "masked_card": "48111111-1114"}),
}


def signed(tx, status):
    status_code = {"settlement": "200", "capture": "200", "pending": "201"}.get(status, "407")
    gross = f"{tx['gross_amount']}.00"
    payment_type, extra = CHANNEL.get(tx["channel"], ("bank_transfer", {}))
    body = {
        "transaction_time": tx["created"],
        "transaction_status": status,
        "transaction_id": tx["transaction_id"],
        "status_code": status_code,
        "status_message": "mock notification",
        "signature_key": hashlib.sha512(
            f"{tx['order_id']}{status_code}{gross}{SERVER_KEY}".encode()
        ).hexdigest(),
        "payment_type": payment_type,
        "order_id": tx["order_id"],
        "merchant_id": "G000000000",
        "gross_amount": gross,
        "currency": "IDR",
    }
    body.update(extra)
    return body


PAGE = """<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1"><title>Payment mock</title>
<style>
 body{{margin:0;font:15px/1.5 system-ui,sans-serif;background:#f2f3f5;color:#1f2328}}
 main{{max-width:420px;margin:48px auto;padding:24px;background:#fff;border:1px solid #dee2e6;border-radius:8px}}
 .note{{font-size:13px;color:#4a5059;background:#fdf1d6;padding:8px 12px;border-radius:6px}}
 .amt{{font-size:28px;font-weight:600;margin:8px 0 0}} dl{{display:grid;grid-template-columns:120px 1fr;gap:4px 12px}}
 dt{{color:#4a5059}} dd{{margin:0}} button{{font:inherit;padding:10px 16px;border-radius:6px;border:0;cursor:pointer}}
 .pay{{background:#1d7a46;color:#fff}} .exp{{background:#e7e9ed;margin-left:8px}}
</style></head><body><main>
<p class="note">Local payment mock standing in for Midtrans Snap. No money moves.</p>
<div>Order {order}</div><div class="amt">Rp {amount}</div>
<dl><dt>Channel</dt><dd>{channel}</dd>{va}</dl>
<form method="post" action="/pay/{token}">
 <button class="pay" name="result" value="settlement">Pay</button>
 <button class="exp" name="result" value="expire">Let it expire</button>
</form></main></body></html>"""


class Handler(BaseHTTPRequestHandler):
    def _json(self, status, body):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _body(self):
        return self.rfile.read(int(self.headers.get("Content-Length", 0)))

    def do_GET(self):
        # Odoo's redirect form submits with GET, which appends an empty query string.
        path = urllib.parse.urlparse(self.path).path
        parts = path.strip("/").split("/")
        if path.startswith("/snap/v4/redirection/") and parts[-1] in TX:
            tx = TX[parts[-1]]
            _ptype, extra = CHANNEL.get(tx["channel"], ("", {}))
            va = extra.get("va_numbers", [{}])[0].get("va_number") or extra.get("permata_va_number")
            page = PAGE.format(
                order=html.escape(tx["order_id"]),
                amount=f"{tx['gross_amount']:,}",
                channel=html.escape(tx["channel"]),
                va=f"<dt>Virtual account</dt><dd>{va}</dd>" if va else "",
                token=parts[-1],
            ).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.end_headers()
            return self.wfile.write(page)
        if len(parts) == 3 and parts[0] == "v2" and parts[2] == "status":
            order_id = urllib.parse.unquote(parts[1])
            token = BY_ORDER.get(order_id)
            if not token:
                return self._json(
                    200, {"status_code": "404", "status_message": "Transaction doesn't exist."}
                )
            tx = TX[token]
            return self._json(200, signed(tx, tx["status"]))
        return self._json(200, {"ok": True})

    def do_POST(self):
        if self.path == "/snap/v1/transactions":
            request = json.loads(self._body() or b"{}")
            details = request["transaction_details"]
            if details["order_id"] in BY_ORDER:
                return self._json(
                    400, {"error_messages": ["transaction_details.order_id has already been taken"]}
                )
            token = str(uuid.uuid4())
            TX[token] = {
                "order_id": details["order_id"],
                "gross_amount": int(details["gross_amount"]),
                "channel": (request.get("enabled_payments") or ["bca_va"])[0],
                "finish": (request.get("callbacks") or {}).get("finish", ""),
                "status": "pending",
                "transaction_id": str(uuid.uuid4()),
                "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            BY_ORDER[details["order_id"]] = token
            print(f"snap: {details['order_id']} Rp {details['gross_amount']}", flush=True)
            return self._json(
                201, {"token": token, "redirect_url": f"{PUBLIC_URL}/snap/v4/redirection/{token}"}
            )
        if self.path.startswith("/pay/"):
            token = self.path.rsplit("/", 1)[-1]
            tx = TX.get(token)
            if not tx:
                return self._json(404, {"error": "unknown token"})
            form = urllib.parse.parse_qs(self._body().decode())
            tx["status"] = form.get("result", ["settlement"])[0]
            notification = json.dumps(signed(tx, tx["status"])).encode()
            try:
                req = urllib.request.Request(
                    NOTIFY_URL,
                    data=notification,
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    print(f"notify {tx['order_id']} {tx['status']} -> {resp.status}", flush=True)
            except Exception as exc:  # the return URL still syncs the status
                print(f"notify failed: {exc}", flush=True)
            query = urllib.parse.urlencode(
                {"order_id": tx["order_id"], "transaction_status": tx["status"]}
            )
            self.send_response(303)
            self.send_header("Location", f"{tx['finish']}?{query}")
            self.end_headers()
            return None
        return self._json(404, {"error": "not found"})

    def log_message(self, *_args):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8090"))
    print(f"Midtrans mock listening on :{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
