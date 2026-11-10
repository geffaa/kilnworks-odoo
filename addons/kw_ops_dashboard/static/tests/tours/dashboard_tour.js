/** @odoo-module **/
import { registry } from "@web/core/registry";

// S01 -> S02: from the dashboard, open the escalated purchase order and see the approval controls.
registry.category("web_tour.tours").add("kw_dashboard_to_po", {
    steps: () => [
        { trigger: ".kw_dash .kw_attn", content: "Dashboard loaded" },
        { trigger: ".kw_dash tr:contains('48,600,000')", content: "Open the escalated PO", run: "click" },
        { trigger: ".o_form_view .o_field_widget[name='name']:contains('PO/')", content: "Purchase order opened" },
        { trigger: ".o_form_view button:contains('Validate')", content: "Approval controls are shown" },
    ],
});
