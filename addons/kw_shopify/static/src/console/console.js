/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

const STATE_BADGE = {
    done: "text-bg-success",
    needs_mapping: "text-bg-warning",
    failed: "text-bg-danger",
    queued: "text-bg-info",
    ignored: "text-bg-secondary",
};

export class ShopifyConsole extends Component {
    static template = "kw_shopify.Console";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.notification = useService("notification");
        this.state = useState({
            loading: true,
            error: false,
            filter: "attention",
            data: null,
            selectedId: null,
        });
        this.filters = [
            { key: "all", label: _t("All") },
            { key: "attention", label: _t("Needs a look") },
            { key: "done", label: _t("Done") },
        ];
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.error = false;
        try {
            this.state.data = await this.orm.call("kw.shopify.store", "get_console_data", [], {
                state_filter: this.state.filter,
                event_id: this.state.selectedId,
            });
            const selected = this.state.data.selected;
            this.state.selectedId = selected ? selected.id : null;
        } catch (error) {
            this.state.error = error.message || _t("The console could not be loaded.");
        } finally {
            this.state.loading = false;
        }
    }

    badge(state) {
        return STATE_BADGE[state] || "text-bg-secondary";
    }

    time(value, withSeconds = false) {
        if (!value) {
            return "";
        }
        // Server values are UTC, either "YYYY-MM-DD HH:MM:SS" or isoformat() from the event log.
        const dt = deserializeDateTime(value.replace("T", " ").slice(0, 19));
        return dt.toFormat(withSeconds ? "HH:mm:ss" : "HH:mm");
    }

    payloadText(excerpt) {
        return JSON.stringify(excerpt, null, 2);
    }

    async setFilter(key) {
        this.state.filter = key;
        this.state.selectedId = null;
        await this.load();
    }

    async select(eventId) {
        this.state.selectedId = eventId;
        await this.load();
    }

    async retry(eventId) {
        await this.orm.call("kw.shopify.event", "action_retry", [[eventId]]);
        this.notification.add(_t("Queued again."), { type: "info" });
        await this.load();
    }

    async mapSku(eventId) {
        const action = await this.orm.call("kw.shopify.event", "action_map_sku", [[eventId]]);
        await this.action.doAction(action, { onClose: () => this.load() });
    }

    async pushStock() {
        const store = this.state.data.store;
        const action = await this.orm.call("kw.shopify.store", "action_push_stock_now", [[store.id]]);
        await this.action.doAction(action);
    }

    openSaleOrder(id) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "sale.order",
            res_id: id,
            views: [[false, "form"]],
        });
    }

    openMap() {
        this.action.doAction("kw_shopify.kw_shopify_product_map_action", {
            additionalContext: { default_store_id: this.state.data.store.id },
        });
    }

    openStore() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "kw.shopify.store",
            res_id: this.state.data.store.id,
            views: [[false, "form"]],
        });
    }
}

registry.category("actions").add("kw_shopify.console", ShopifyConsole);
