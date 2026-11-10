from odoo import fields, models


class KwShopifyProductMap(models.Model):
    _name = "kw.shopify.product.map"
    _description = "Shopify variant ↔ Odoo product"
    _order = "sku"
    _rec_name = "sku"

    store_id = fields.Many2one("kw.shopify.store", required=True, ondelete="cascade", index=True)
    product_id = fields.Many2one("product.product", required=True, ondelete="cascade", index=True)
    sku = fields.Char(string="Shopify SKU", required=True, index=True)
    variant_gid = fields.Char(string="Variant", help="gid://shopify/ProductVariant/…")
    inventory_item_gid = fields.Char(
        string="Inventory item", help="gid://shopify/InventoryItem/… (needed to push stock)"
    )

    _sql_constraints = [
        ("sku_uniq", "unique(store_id, sku)", "This SKU is already mapped for the store."),
        ("product_uniq", "unique(store_id, product_id)", "This product is already mapped."),
    ]
