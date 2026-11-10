import json

from odoo.tests import HttpCase, new_test_user, tagged
from odoo.tools import mute_logger


@tagged("post_install", "-at_install")
class TestApi(HttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.tech = new_test_user(
            cls.env,
            "kw_api_tech",
            groups="base.group_user,sales_team.group_sale_salesman_all_leads,stock.group_stock_user",
        )
        cls.customer = cls.env["res.partner"].create(
            {"name": "Teras Kopi Jakal", "is_company": True, "customer_rank": 1, "city": "Sleman"}
        )
        cls.mug = cls.env["product.product"].create(
            {
                "name": "Celadon mug",
                "default_code": "KW-MUG-350-CEL",
                "is_storable": True,
                "list_price": 185000,
            }
        )
        location = (
            cls.env["stock.warehouse"]
            .search([("company_id", "=", cls.env.company.id)], limit=1)
            .lot_stock_id
        )
        cls.env["stock.quant"]._update_available_quantity(cls.mug, location, 42)

    def _key(self, *scopes, user=None):
        scope_ids = self.env["kw.api.scope"].search([("code", "in", scopes)]).ids
        key = self.env["kw.api.key"].create(
            {"name": "test", "user_id": (user or self.tech).id, "scope_ids": [(6, 0, scope_ids)]}
        )
        wizard = self.env["kw.api.key.show"].browse(key.action_generate()["res_id"])
        return key, wizard.key

    def _get(self, path, raw):
        return self.url_open(path, headers={"Authorization": f"Bearer {raw}"})

    def test_key_stored_as_hash_only(self):
        key, raw = self._key("stock:read")
        self.assertTrue(raw.startswith(f"kw_{key.key_prefix}_"))
        self.assertNotIn(raw, key.sudo().key_hash)
        self.assertEqual(len(key.sudo().key_hash), 64)

    def test_stock_with_scope(self):
        _key, raw = self._key("stock:read")
        response = self._get("/api/v1/stock?sku=KW-MUG-350-CEL", raw)
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(
            data,
            [
                {
                    "sku": "KW-MUG-350-CEL",
                    "on_hand": 42.0,
                    "free": 42.0,
                    "incoming": 0.0,
                    "outgoing": 0.0,
                }
            ],
        )

    def test_missing_scope(self):
        _key, raw = self._key("stock:read")
        response = self.url_open(
            "/api/v1/orders",
            data=json.dumps({}),
            headers={"Authorization": f"Bearer {raw}", "Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["error"]["code"], "insufficient_scope")

    def test_bad_revoked_and_expired_keys(self):
        self.assertEqual(self._get("/api/v1/stock", "kw_nope_nope").status_code, 401)
        self.assertEqual(self.url_open("/api/v1/stock").status_code, 401)
        key, raw = self._key("stock:read")
        key.action_revoke()
        self.assertEqual(self._get("/api/v1/stock", raw).status_code, 401)
        key2, raw2 = self._key("stock:read")
        key2.expires_at = "2020-01-01 00:00:00"
        self.assertEqual(self._get("/api/v1/stock", raw2).status_code, 401)

    def test_rotation_invalidates_old_key(self):
        key, old = self._key("stock:read")
        new = self.env["kw.api.key.show"].browse(key.action_generate()["res_id"]).key
        self.assertEqual(self._get("/api/v1/stock", old).status_code, 401)
        self.assertEqual(self._get("/api/v1/stock", new).status_code, 200)

    def test_rate_limit(self):
        key, raw = self._key("products:read")
        window = self.env["kw.api.rate.bucket"]
        # pre-fill the current minute so the next request is the 61st
        from odoo import fields

        window.sudo().create(
            {
                "key_id": key.id,
                "count": 60,
                "window_start": fields.Datetime.now().replace(second=0, microsecond=0),
            }
        )
        response = self._get("/api/v1/products", raw)
        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.headers.get("Retry-After"), "60")

    def test_create_quotation_then_read_it(self):
        _key, raw = self._key("orders:write", "orders:read")
        body = {
            "partner_id": self.customer.id,
            "client_ref": "WH-7781",
            "lines": [{"sku": "KW-MUG-350-CEL", "quantity": 24}],
        }
        response = self.url_open(
            "/api/v1/orders",
            data=json.dumps(body),
            headers={"Authorization": f"Bearer {raw}", "Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 201)
        created = response.json()["data"]
        self.assertEqual(created["state"], "draft")
        self.assertEqual(created["lines"][0]["quantity"], 24.0)
        order = self.env["sale.order"].browse(created["id"])
        self.assertEqual(order.create_uid, self.tech, "created as the key's user")
        detail = self._get(f"/api/v1/orders/{created['id']}", raw).json()["data"]
        self.assertEqual(detail["client_ref"], "WH-7781")

    def test_unknown_sku_is_422(self):
        _key, raw = self._key("orders:write")
        body = {"partner_id": self.customer.id, "lines": [{"sku": "NOPE", "quantity": 1}]}
        response = self.url_open(
            "/api/v1/orders",
            data=json.dumps(body),
            headers={"Authorization": f"Bearer {raw}", "Content-Type": "application/json"},
        )
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["error"]["code"], "unknown_sku")

    @mute_logger("odoo.http")
    def test_record_rules_apply(self):
        """A salesman limited to own documents does not see someone else's orders."""
        own_only = new_test_user(
            self.env, "kw_api_own", groups="base.group_user,sales_team.group_sale_salesman"
        )
        other = self.env["sale.order"].create(
            {
                "partner_id": self.customer.id,
                "user_id": self.tech.id,
                "order_line": [(0, 0, {"product_id": self.mug.id})],
            }
        )
        _key, raw = self._key("orders:read", user=own_only)
        listed = self._get("/api/v1/orders", raw).json()["data"]
        self.assertNotIn(other.id, [o["id"] for o in listed])
        self.assertEqual(self._get(f"/api/v1/orders/{other.id}", raw).status_code, 404)

    def test_pagination(self):
        for i in range(3):
            self.env["product.product"].create({"name": f"Bowl {i}", "default_code": f"KW-T-{i}"})
        _key, raw = self._key("products:read")
        first = self._get("/api/v1/products?limit=2", raw).json()
        self.assertEqual(len(first["data"]), 2)
        second = self._get(f"/api/v1/products?limit=2&cursor={first['next_cursor']}", raw).json()
        self.assertTrue(
            set(p["id"] for p in first["data"]).isdisjoint(p["id"] for p in second["data"])
        )

    def test_docs_public(self):
        spec = self.url_open("/api/v1/docs").json()
        self.assertEqual(spec["openapi"], "3.1.0")
        self.assertIn("/stock", spec["paths"])
