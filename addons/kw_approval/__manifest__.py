{
    "name": "Kilnworks Approvals",
    "summary": "Purchase and discount approvals on OCA tier validation: no self-approval, "
    "delegation, SLA escalation",
    "version": "18.0.1.0.0",
    "category": "Purchases",
    "author": "Kilnworks demo (synthetic)",
    "website": "https://github.com/geffaa/kilnworks-odoo",
    "license": "AGPL-3",
    "depends": [
        "kw_ops",
        "resource",
        "purchase_tier_validation",
        "sale_tier_validation",
    ],
    "data": [
        "security/ir.model.access.csv",
        "security/kw_approval_security.xml",
        "data/tier_definition.xml",
        "data/ir_cron.xml",
        "views/kw_approval_delegation_views.xml",
        "views/tier_review_views.xml",
        "views/tier_definition_views.xml",
        "views/menus.xml",
    ],
    "installable": True,
}
