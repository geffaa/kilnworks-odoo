"""A tiny stand-in for the Shopify Admin GraphQL API, for offline demos and CI.

Answers inventorySetQuantities like Shopify does and prints each call. Set MOCK_THROTTLE_EVERY=3
to answer every third call with HTTP 429 and watch the job retry. Standard library only.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

THROTTLE_EVERY = int(os.environ.get("MOCK_THROTTLE_EVERY", "0"))
calls = {"n": 0}


class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, headers=None):
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        for key, value in (headers or {}).items():
            self.send_header(key, value)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # health check
        self._send(200, {"ok": True})

    def do_POST(self):
        if not self.path.endswith("/graphql.json"):
            return self._send(404, {"errors": "Not Found"})
        if not self.headers.get("X-Shopify-Access-Token"):
            return self._send(401, {"errors": "[API] Invalid API key or access token"})
        calls["n"] += 1
        if THROTTLE_EVERY and calls["n"] % THROTTLE_EVERY == 0:
            return self._send(429, {"errors": "Throttled"}, {"Retry-After": "2.0"})
        length = int(self.headers.get("Content-Length", 0))
        request = json.loads(self.rfile.read(length) or b"{}")
        if "inventorySetQuantities" in request.get("query", ""):
            quantities = request["variables"]["input"]["quantities"]
            print(f"inventorySetQuantities: {len(quantities)} items", flush=True)
            return self._send(
                200,
                {
                    "data": {"inventorySetQuantities": {"userErrors": []}},
                    "extensions": {
                        "cost": {
                            "requestedQueryCost": 10,
                            "throttleStatus": {
                                "maximumAvailable": 2000.0,
                                "currentlyAvailable": 1990,
                                "restoreRate": 100.0,
                            },
                        }
                    },
                },
            )
        return self._send(200, {"errors": [{"message": "mock: query not supported"}]})

    def log_message(self, *_args):
        pass


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    print(f"Shopify mock listening on :{port}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", port), Handler).serve_forever()
