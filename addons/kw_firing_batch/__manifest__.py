{
    "name": "Kilnworks Firing Batches",
    "summary": "Kiln firing batches: temperature, duration, load and yield",
    "version": "18.0.1.0.0",
    "category": "Manufacturing",
    "author": "Kilnworks demo (synthetic)",
    "website": "https://github.com/geffaa/kilnworks-odoo",
    "license": "LGPL-3",
    "depends": ["stock", "mail"],
    "data": [
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "views/kw_kiln_views.xml",
        "views/kw_firing_batch_views.xml",
        "report/delivery_slip.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "kw_firing_batch/static/src/js/temperature_field.js",
            "kw_firing_batch/static/src/xml/temperature_field.xml",
        ],
    },
    "installable": True,
}
