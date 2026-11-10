{
    "name": "Kilnworks Ops",
    "summary": "App menu and role groups shared by the Kilnworks modules",
    "version": "18.0.1.0.0",
    "category": "Operations",
    "author": "Kilnworks demo (synthetic)",
    "website": "https://github.com/geffaa/kilnworks-odoo",
    "license": "LGPL-3",
    "depends": ["base", "mail"],
    "data": [
        "security/kw_ops_security.xml",
        "views/menus.xml",
    ],
    "application": True,
    "installable": True,
}
