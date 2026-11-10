import copy
import json

from odoo.tests import new_test_user

from ..controllers.main import shopify_signature

SECRET = "test-webhook-secret"

ORDER = {
    "id": 820982911946154508,
    "admin_graphql_api_id": "gid://shopify/Order/820982911946154508",
    "name": "#KW1042",
    "email": "m.okafor@example.com",
    "currency": "USD",
    "total_price": "118.00",
    "customer": {"first_name": "Maya", "last_name": "Okafor", "email": "m.okafor@example.com"},
    "shipping_address": {
        "address1": "14 Harbour St",
        "city": "Wellington",
        "zip": "6011",
        "country_code": "NZ",
    },
    "line_items": [
        {"sku": "KW-MUG-350-CEL", "quantity": 4, "price": "24.00", "discount_allocations": []},
        {
            "sku": "KW-PLT-210-SPK",
            "quantity": 1,
            "price": "22.00",
            "discount_allocations": [{"amount": "2.20"}],
        },
    ],
}


def order_payload(**overrides):
    payload = copy.deepcopy(ORDER)
    payload.update(overrides)
    return payload


class ShopifySetupMixin:
    @classmethod
    def _setup_shopify(cls):
        env = cls.env
        cls.usd = env.ref("base.USD")
        cls.usd.active = True
        cls.pricelist = env["product.pricelist"].create(
            {"name": "Shopify USD", "currency_id": cls.usd.id}
        )
        cls.warehouse = env["stock.warehouse"].search(
            [("company_id", "=", env.company.id)], limit=1
        )
        cls.store = env["kw.shopify.store"].create(
            {
                "name": "Kilnworks Studio",
                "shop_domain": "kilnworks-test.myshopify.com",
                "api_base_url": "http://shopify.test",
                "access_token": "shpat_test",
                "webhook_secret": SECRET,
                "location_gid": "gid://shopify/Location/1",
                "warehouse_id": cls.warehouse.id,
                "pricelist_id": cls.pricelist.id,
            }
        )
        Product = env["product.product"]
        cls.mug = Product.create(
            {
                "name": "Celadon mug 350 ml",
                "default_code": "KW-MUG-350-CEL",
                "is_storable": True,
                "type": "consu",
            }
        )
        cls.plate = Product.create(
            {
                "name": "Speckled side plate",
                "default_code": "KW-PLT-210-SPK",
                "is_storable": True,
                "type": "consu",
            }
        )
        Map = env["kw.shopify.product.map"]
        for i, product in enumerate((cls.mug, cls.plate), start=1):
            Map.create(
                {
                    "store_id": cls.store.id,
                    "product_id": product.id,
                    "sku": product.default_code,
                    "variant_gid": f"gid://shopify/ProductVariant/{i}",
                    "inventory_item_gid": f"gid://shopify/InventoryItem/{i}",
                }
            )
        cls.ops = new_test_user(
            env,
            "kw_ops_user",
            groups="base.group_user,kw_ops.group_manager,sales_team.group_sale_salesman",
        )

    @staticmethod
    def signed(payload, secret=SECRET):
        body = json.dumps(payload).encode()
        return body, shopify_signature(secret, body)
