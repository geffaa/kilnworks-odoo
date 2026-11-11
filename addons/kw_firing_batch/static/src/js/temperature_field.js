/** @odoo-module **/
// Odoo 16 field registration: the component class goes straight into the registry.
import { registry } from "@web/core/registry";
import { IntegerField } from "@web/views/fields/integer/integer_field";

export class TemperatureField extends IntegerField {
    get tone() {
        const value = this.props.value || 0;
        if (!value) return "";
        if (value < 1200) return "text-warning";   // bisque / earthenware range
        if (value > 1300) return "text-danger";    // beyond stoneware glazes
        return "text-success";
    }
}
TemperatureField.template = "kw_firing_batch.TemperatureField";

registry.category("fields").add("kw_temperature", TemperatureField);
