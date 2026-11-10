{
    "name": "Payment Provider: Midtrans",
    "summary": "Midtrans Snap for Odoo invoices and orders: VA, QRIS, e-wallets and cards in IDR",
    "version": "18.0.1.0.0",
    "category": "Accounting/Payment Providers",
    "author": "Kilnworks demo (synthetic)",
    "website": "https://github.com/geffaa/kilnworks-odoo",
    "license": "LGPL-3",
    "depends": ["payment"],
    "external_dependencies": {"python": ["requests"]},
    "data": [
        "views/payment_midtrans_templates.xml",
        "views/payment_provider_views.xml",
        "data/payment_provider_data.xml",
    ],
    "post_init_hook": "post_init_hook",
    "uninstall_hook": "uninstall_hook",
    "installable": True,
}
