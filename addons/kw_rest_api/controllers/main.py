"""REST API v1. JSON in, JSON out; every request is authenticated by a scoped key."""

import functools
import json
import logging
from pathlib import Path

from odoo import fields, http
from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.http import request

_logger = logging.getLogger(__name__)

DEFAULT_LIMIT, MAX_LIMIT = 50, 200
OPENAPI = Path(__file__).resolve().parent.parent / "static" / "api" / "openapi.json"


def error(status, code, message, headers=None):
    return request.make_json_response(
        {"error": {"code": code, "message": message}}, status=status, headers=headers
    )


def api_route(path, scope, methods=("GET",)):
    """Route decorator: Bearer key, scope check, rate limit, then run as the key's user."""

    def decorator(func):
        @http.route(
            path, type="http", auth="public", methods=list(methods), csrf=False, save_session=False
        )
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            header = request.httprequest.headers.get("Authorization", "")
            raw = header[7:].strip() if header.lower().startswith("bearer ") else ""
            key = request.env["kw.api.key"]._authenticate(raw)
            if not key:
                return error(401, "invalid_key", "Missing, unknown, revoked or expired API key.")
            if key._hit_rate_limit():
                return error(
                    429,
                    "rate_limited",
                    "Too many requests; try again shortly.",
                    headers=[("Retry-After", "60")],
                )
            if not key._has_scope(scope):
                return error(403, "insufficient_scope", f"This key lacks the {scope} scope.")
            key.sudo().last_used_at = fields.Datetime.now()
            request.update_env(user=key.user_id.id)
            try:
                return func(self, *args, **kwargs)
            except AccessError:
                return error(403, "forbidden", "The key's user may not access this record.")
            except (UserError, ValidationError) as exc:
                request.env.cr.rollback()
                return error(422, "invalid", str(exc))

        return wrapper

    return decorator


def paginate(model, domain, order="id"):
    args = request.httprequest.args
    try:
        limit = min(int(args.get("limit", DEFAULT_LIMIT)), MAX_LIMIT)
        cursor = int(args.get("cursor", 0))
    except ValueError:
        limit, cursor = DEFAULT_LIMIT, 0
    records = request.env[model].search(
        domain + [("id", ">", cursor)], order=order, limit=limit + 1
    )
    page, more = records[:limit], len(records) > limit
    return page, (page[-1].id if more else None)


class KwRestApi(http.Controller):
    @http.route("/api/v1/docs", type="http", auth="public", methods=["GET"], save_session=False)
    def docs(self):
        return request.make_response(
            OPENAPI.read_bytes(), headers=[("Content-Type", "application/json")]
        )

    @api_route("/api/v1/products", scope="products:read")
    def products(self, **_query):
        page, cursor = paginate(
            "product.product", [("sale_ok", "=", True), ("default_code", "!=", False)]
        )
        return request.make_json_response(
            {
                "data": [
                    {
                        "id": p.id,
                        "sku": p.default_code,
                        "name": p.name,
                        "list_price": p.lst_price,
                        "currency": p.currency_id.name,
                        "uom": p.uom_id.name,
                        "weight_kg": p.weight,
                    }
                    for p in page
                ],
                "next_cursor": cursor,
            }
        )

    @api_route("/api/v1/stock", scope="stock:read")
    def stock(self, **_query):
        args = request.httprequest.args
        warehouse = request.env["stock.warehouse"].search(
            [("company_id", "=", request.env.company.id)], limit=1
        )
        location = warehouse.lot_stock_id
        domain = [("is_storable", "=", True), ("default_code", "!=", False)]
        if args.get("sku"):
            domain.append(("default_code", "=", args["sku"]))
        page, cursor = paginate("product.product", domain)
        page = page.with_context(location=location.id)
        return request.make_json_response(
            {
                "location": location.complete_name,
                "data": [
                    {
                        "sku": p.default_code,
                        "on_hand": p.qty_available,
                        "free": p.free_qty,
                        "incoming": p.incoming_qty,
                        "outgoing": p.outgoing_qty,
                    }
                    for p in page
                ],
                "next_cursor": cursor,
            }
        )

    @api_route("/api/v1/orders", scope="orders:read")
    def orders(self, **_query):
        args = request.httprequest.args
        domain = []
        if args.get("state"):
            domain.append(("state", "=", args["state"]))
        page, cursor = paginate("sale.order", domain)
        return request.make_json_response(
            {"data": [o._kw_api_payload(with_lines=False) for o in page], "next_cursor": cursor}
        )

    @api_route("/api/v1/orders/<int:order_id>", scope="orders:read")
    def order(self, order_id, **_query):
        order = request.env["sale.order"].search([("id", "=", order_id)], limit=1)
        if not order:
            return error(404, "not_found", "No such order.")
        return request.make_json_response({"data": order._kw_api_payload()})

    @api_route("/api/v1/orders", scope="orders:write", methods=("POST",))
    def create_order(self, **_query):
        try:
            body = json.loads(request.httprequest.get_data() or b"{}")
        except ValueError:
            return error(400, "invalid_json", "Body must be JSON.")
        lines = body.get("lines") or []
        if not lines:
            return error(422, "invalid", "At least one line is required.")
        Product = request.env["product.product"]
        order_lines = []
        for line in lines:
            product = Product.search([("default_code", "=", line.get("sku"))], limit=1)
            if not product:
                return error(422, "unknown_sku", f"Unknown SKU {line.get('sku')!r}.")
            vals = {"product_id": product.id, "product_uom_qty": float(line.get("quantity") or 1)}
            if "price_unit" in line:
                vals["price_unit"] = float(line["price_unit"])
            order_lines.append((0, 0, vals))
        partner = request.env["res.partner"].search([("id", "=", body.get("partner_id"))], limit=1)
        if not partner:
            return error(422, "invalid", "partner_id does not match a contact this key can see.")
        order = request.env["sale.order"].create(
            {
                "partner_id": partner.id,
                "client_order_ref": body.get("client_ref"),
                "order_line": order_lines,
            }
        )
        return request.make_json_response({"data": order._kw_api_payload()}, status=201)

    @api_route("/api/v1/partners", scope="partners:read")
    def partners(self, **_query):
        page, cursor = paginate(
            "res.partner", [("is_company", "=", True), ("customer_rank", ">", 0)]
        )
        return request.make_json_response(
            {
                "data": [
                    {
                        "id": p.id,
                        "name": p.name,
                        "email": p.email or None,
                        "city": p.city or None,
                        "country": p.country_id.code or None,
                    }
                    for p in page
                ],
                "next_cursor": cursor,
            }
        )
