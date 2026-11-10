{
    "name": "Kilnworks Ops Dashboard",
    "summary": "One screen for what needs doing today: approvals, sync failures, revenue by "
    "channel, low stock and invoices due",
    "version": "18.0.1.0.0",
    "category": "Operations",
    "author": "Kilnworks demo (synthetic)",
    "website": "https://github.com/geffaa/kilnworks-odoo",
    "license": "LGPL-3",
    "depends": ["kw_approval", "kw_shopify", "account", "stock"],
    "data": ["views/dashboard_views.xml"],
    "assets": {
        "web.assets_backend": ["kw_ops_dashboard/static/src/dashboard/*"],
        "web.assets_tests": ["kw_ops_dashboard/static/tests/tours/*"],
    },
    "installable": True,
}
