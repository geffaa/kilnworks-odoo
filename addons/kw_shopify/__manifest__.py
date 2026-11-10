{
    "name": "Kilnworks Shopify Connector",
    "summary": "Shopify orders and stock through signed webhooks and queue_job, "
    "with a sync log people can fix and retry",
    "version": "18.0.1.0.0",
    "category": "Sales",
    "author": "Kilnworks demo (synthetic)",
    "website": "https://github.com/geffaa/kilnworks-odoo",
    "license": "LGPL-3",
    "depends": ["kw_ops", "sale_stock", "queue_job"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "security/ir.model.access.csv",
        "data/queue_job_data.xml",
        "views/kw_shopify_product_map_views.xml",
        "views/kw_shopify_store_views.xml",
        "views/kw_shopify_event_views.xml",
        "views/sale_order_views.xml",
        "views/menus.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "kw_shopify/static/src/console/*",
        ],
    },
    "installable": True,
}
