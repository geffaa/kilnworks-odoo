{
    "name": "Kilnworks Export Reports",
    "summary": "Export packing list per carton with HS codes, weights and firing lots",
    "version": "18.0.1.0.0",
    "category": "Inventory",
    "author": "Kilnworks demo (synthetic)",
    "website": "https://github.com/geffaa/kilnworks-odoo",
    "license": "LGPL-3",
    "depends": ["stock", "sale_stock"],
    "data": [
        "views/product_views.xml",
        "views/stock_picking_views.xml",
        "report/packing_list.xml",
    ],
    "installable": True,
}
