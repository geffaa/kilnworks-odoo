"""Send a signed Shopify orders/create webhook to the local Odoo, as Shopify would.

    python3 tools/mocks/send_order.py                      # a normal order
    python3 tools/mocks/send_order.py --sku KW-MUG-350-SAGE  # an unmapped SKU -> needs mapping
    python3 tools/mocks/send_order.py --repeat             # same webhook id twice -> one event

The demo store's secret is public on purpose: it only exists in the synthetic demo database.
"""

import argparse
import base64
import hashlib
import hmac
import json
import random
import time
import urllib.request
import uuid

DEMO_SECRET = "kilnworks-demo-webhook-secret"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://localhost:8069")
    parser.add_argument("--store", type=int, default=1)
    parser.add_argument("--secret", default=DEMO_SECRET)
    parser.add_argument("--sku", default="KW-MUG-350-CEL")
    parser.add_argument("--qty", type=int, default=2)
    parser.add_argument("--repeat", action="store_true")
    args = parser.parse_args()

    number = random.randint(2000, 9999)
    order = {
        "id": int(time.time() * 1000),
        "admin_graphql_api_id": f"gid://shopify/Order/{int(time.time() * 1000)}",
        "name": f"#KW{number}",
        "email": "demo.buyer@example.com",
        "currency": "USD",
        "total_price": f"{24 * args.qty:.2f}",
        "customer": {"first_name": "Demo", "last_name": "Buyer", "email": "demo.buyer@example.com"},
        "shipping_address": {"city": "Melbourne", "country_code": "AU"},
        "line_items": [
            {"sku": args.sku, "quantity": args.qty, "price": "24.00", "discount_allocations": []}
        ],
    }
    body = json.dumps(order).encode()
    signature = base64.b64encode(
        hmac.new(args.secret.encode(), body, hashlib.sha256).digest()
    ).decode()
    webhook_id = str(uuid.uuid4())
    for _ in range(2 if args.repeat else 1):
        request = urllib.request.Request(
            f"{args.url}/kw_shopify/webhook/{args.store}",
            data=body,
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Hmac-Sha256": signature,
                "X-Shopify-Topic": "orders/create",
                "X-Shopify-Webhook-Id": webhook_id,
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=10) as response:
            print(order["name"], response.status, response.read().decode())


if __name__ == "__main__":
    main()
