/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { deserializeDateTime } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";

const CHART = { width: 640, height: 220, left: 40, bottom: 26, top: 10, barWidth: 22 };

export class OpsDashboard extends Component {
    static template = "kw_ops_dashboard.Dashboard";
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ period: 30, data: null, loading: true, error: false });
        this.periods = [
            { value: 7, label: _t("7 days") },
            { value: 30, label: _t("30 days") },
            { value: 90, label: _t("90 days") },
        ];
        onWillStart(() => this.load());
    }

    async load() {
        this.state.loading = true;
        this.state.error = false;
        try {
            this.state.data = await this.orm.call("kw.ops.dashboard", "get_data", [], {
                period: this.state.period,
            });
        } catch (error) {
            this.state.error = error.message || _t("The dashboard could not be loaded.");
        } finally {
            this.state.loading = false;
        }
    }

    async setPeriod(value) {
        this.state.period = value;
        await this.load();
    }

    time(value) {
        return value ? deserializeDateTime(value).toFormat("HH:mm") : "";
    }

    badge(state) {
        return { needs_mapping: "text-bg-warning", failed: "text-bg-danger", queued: "text-bg-info" }[state] ||
            "text-bg-secondary";
    }

    /** Grouped bars per bucket, scaled to the largest value rounded up to a nice step. */
    get chart() {
        const series = this.state.data.revenue.series;
        const max = Math.max(1, ...series.flatMap((s) => [s.b2b, s.shopify]));
        const step = max > 100 ? 50 : max > 40 ? 20 : max > 10 ? 10 : max > 4 ? 2 : 1;
        const top = Math.ceil(max / step) * step;
        const plotHeight = CHART.height - CHART.bottom - CHART.top;
        const groupWidth = (CHART.width - CHART.left) / Math.max(series.length, 1);
        const barWidth = Math.min(CHART.barWidth, groupWidth / 2 - 4);
        const y = (v) => CHART.top + plotHeight - (v / top) * plotHeight;
        const grid = [];
        for (let v = 0; v <= top + 1e-9; v += step) {
            grid.push({ y: y(v), label: String(v) });
        }
        const groups = series.map((s, i) => {
            const cx = CHART.left + groupWidth * i + groupWidth / 2;
            return {
                label: s.label + (s.partial ? " *" : ""),
                cx,
                bars: [
                    { x: cx - barWidth - 1, value: s.b2b, cls: "kw_bar_b2b", name: "B2B" },
                    { x: cx + 1, value: s.shopify, cls: "kw_bar_shopify", name: "Shopify" },
                ].map((b) => ({ ...b, y: y(b.value), h: (b.value / top) * plotHeight, w: barWidth })),
            };
        });
        return { ...CHART, grid, groups, labelY: CHART.height - 8, anyPartial: series.some((s) => s.partial) };
    }

    async openReview(id) {
        const action = await this.orm.call("tier.review", "action_kw_open_document", [[id]]);
        await this.action.doAction(action);
    }

    openInbox() {
        this.action.doAction("kw_approval.tier_review_action_inbox");
    }

    openSync() {
        this.action.doAction("kw_shopify.kw_shopify_console_action");
    }

    openRecord(model, id) {
        this.action.doAction({ type: "ir.actions.act_window", res_model: model, res_id: id, views: [[false, "form"]] });
    }

    openReplenishment() {
        this.action.doAction("stock.action_orderpoint_replenish");
    }
}

registry.category("actions").add("kw_ops_dashboard.dashboard", OpsDashboard);
