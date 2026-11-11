// Odoo 18: fields register a descriptor object; the value comes from the record.
import { registry } from "@web/core/registry";
import { IntegerField, integerField } from "@web/views/fields/integer/integer_field";

export class TemperatureField extends IntegerField {
    static template = "kw_firing_batch.TemperatureField";

    get tone() {
        const value = this.props.record.data[this.props.name] || 0;
        if (!value) return "";
        if (value < 1200) return "text-warning"; // bisque / earthenware range
        if (value > 1300) return "text-danger"; // beyond stoneware glazes
        return "text-success";
    }
}

registry.category("fields").add("kw_temperature", {
    ...integerField,
    component: TemperatureField,
});
