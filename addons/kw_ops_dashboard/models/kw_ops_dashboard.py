from datetime import timedelta

from odoo import api, fields, models
from odoo.tools.misc import format_amount, format_date

PERIODS = (7, 30, 90)


class KwOpsDashboard(models.AbstractModel):
    _name = "kw.ops.dashboard"
    _description = "Kilnworks Ops dashboard data"

    @api.model
    def get_data(self, period=30):
        period = period if period in PERIODS else 30
        today = fields.Date.context_today(self)
        start = today - timedelta(days=period - 1)
        return {
            "period": period,
            "range": f"{format_date(self.env, start)} – {format_date(self.env, today)}",
            "approvals": self._approvals(),
            "sync": self._sync(),
            "revenue": self._revenue(start, today, period),
            "low_stock": self._low_stock(),
            "invoices": self._invoices(today),
        }

    # -- needs attention ------------------------------------------------------------
    def _approvals(self):
        reviews = self.env["tier.review"].search(
            [("status", "=", "pending"), ("reviewer_ids", "in", self.env.uid)],
            order="kw_pending_since asc",
        )
        rows = []
        for review in reviews:
            doc = review._kw_document()
            if not doc:
                continue
            tiers = len(doc.review_ids)
            rows.append(
                {
                    "id": review.id,
                    "document": doc.display_name,
                    "partner": doc.partner_id.display_name if "partner_id" in doc else "",
                    "rule": review.name
                    if tiers == 1
                    else f"{review.name} · tier {review.sequence} of {tiers}",
                    "amount": format_amount(self.env, doc.amount_total, doc.currency_id)
                    if "amount_total" in doc
                    else "",
                    "waiting_hours": review.kw_waiting_hours,
                    "late": bool(review.kw_escalated_at),
                }
            )
        return {"count": len(rows), "rows": rows}

    def _sync(self):
        Event = self.env["kw.shopify.event"]
        since = fields.Datetime.now() - timedelta(hours=24)
        recent = Event.search([("received_at", ">=", since)])
        stuck = Event.search(
            [("state", "in", ("needs_mapping", "failed"))], order="received_at desc"
        )
        store = self.env["kw.shopify.store"].search([], limit=1)
        return {
            "count": len(stuck),
            "processed": len(recent.filtered(lambda e: e.state == "done")),
            "received": len(recent),
            "last_push": fields.Datetime.to_string(store.last_stock_push_at)
            if store.last_stock_push_at
            else False,
            "last_push_count": store.last_stock_push_count,
            "rows": [
                {
                    "id": e.id,
                    "order": e.order_name,
                    "topic": e.topic,
                    "state": e.state,
                    "state_label": dict(Event._fields["state"].selection)[e.state],
                    "why": e.error or "",
                    "received_at": fields.Datetime.to_string(e.received_at),
                }
                for e in stuck[:5]
            ],
        }

    # -- revenue --------------------------------------------------------------------
    def _orders(self, start, end):
        return self.env["sale.order"].search(
            [
                ("state", "=", "sale"),
                ("date_order", ">=", fields.Datetime.to_datetime(start)),
                ("date_order", "<", fields.Datetime.to_datetime(end + timedelta(days=1))),
            ]
        )

    def _company_amount(self, order):
        company = order.company_id
        return order.currency_id._convert(
            order.amount_untaxed, company.currency_id, company, order.date_order.date()
        )

    def _revenue(self, start, end, period):
        company = self.env.company
        orders = self._orders(start, end)
        previous = self._orders(start - timedelta(days=period), start - timedelta(days=1))
        channels = []
        for code, label in (("b2b", "B2B"), ("shopify", "Shopify")):
            mine = orders.filtered(lambda o, c=code: o.kw_channel == c)
            before = previous.filtered(lambda o, c=code: o.kw_channel == c)
            total = sum(self._company_amount(o) for o in mine)
            total_before = sum(self._company_amount(o) for o in before)
            native = mine[:1].currency_id or company.currency_id
            native_total = (
                sum(mine.mapped("amount_untaxed")) if native != company.currency_id else total
            )
            channels.append(
                {
                    "code": code,
                    "label": label,
                    "orders": len(mine),
                    "amount": format_amount(self.env, native_total, native),
                    "company_amount": format_amount(self.env, total, company.currency_id),
                    "foreign": native != company.currency_id,
                    "delta": round((total - total_before) / total_before * 100, 1)
                    if total_before
                    else None,
                }
            )
        # Buckets: days for a week, weeks (Monday start) otherwise.
        buckets = []
        if period == 7:
            for i in range(7):
                day = start + timedelta(days=i)
                buckets.append((day, day, format_date(self.env, day, date_format="EEE d")))
        else:
            cursor = start - timedelta(days=start.weekday())
            while cursor <= end:
                buckets.append(
                    (
                        max(cursor, start),
                        min(cursor + timedelta(days=6), end),
                        format_date(self.env, cursor, date_format="d MMM"),
                    )
                )
                cursor += timedelta(days=7)
        series = []
        for first, last, label in buckets:
            in_bucket = orders.filtered(lambda o, a=first, b=last: a <= o.date_order.date() <= b)
            series.append(
                {
                    "label": label,
                    "partial": last == end and (end - first).days < (0 if period == 7 else 6),
                    "b2b": round(
                        sum(self._company_amount(o) for o in in_bucket if o.kw_channel == "b2b")
                        / 1e6,
                        2,
                    ),
                    "shopify": round(
                        sum(self._company_amount(o) for o in in_bucket if o.kw_channel == "shopify")
                        / 1e6,
                        2,
                    ),
                }
            )
        return {
            "channels": channels,
            "series": series,
            "unit": f"{company.currency_id.symbol} million",
        }

    # -- stock and invoices ---------------------------------------------------------
    def _low_stock(self):
        rows = []
        orderpoints = self.env["stock.warehouse.orderpoint"].search([])
        for op in orderpoints:
            on_hand = op.product_id.with_context(location=op.location_id.id).qty_available
            if op.product_min_qty and on_hand < op.product_min_qty:
                rows.append(
                    {
                        "product_id": op.product_id.id,
                        "name": op.product_id.name,
                        "sku": op.product_id.default_code or "",
                        "on_hand": on_hand,
                        "minimum": op.product_min_qty,
                        "ratio": on_hand / op.product_min_qty,
                    }
                )
        rows.sort(key=lambda r: r["ratio"])
        return {"count": len(rows), "total": len(orderpoints), "rows": rows[:5]}

    def _invoices(self, today):
        moves = self.env["account.move"].search(
            [
                ("move_type", "=", "out_invoice"),
                ("state", "=", "posted"),
                ("payment_state", "in", ("not_paid", "partial")),
            ],
            order="invoice_date_due asc",
            limit=5,
        )
        rows = []
        for move in moves:
            overdue = (
                (today - move.invoice_date_due).days
                if move.invoice_date_due and move.invoice_date_due < today
                else 0
            )
            txs = move.transaction_ids.sorted("id") if "transaction_ids" in move else []
            last_tx = txs[-1:] if txs else None
            if last_tx and last_tx.state == "pending":
                status, tone = "VA pending", "warning"
            elif overdue:
                status, tone = "No payment", "danger"
            else:
                status, tone = "Open", "info"
            rows.append(
                {
                    "id": move.id,
                    "name": move.name,
                    "partner": move.partner_id.name,
                    "amount": format_amount(self.env, move.amount_residual, move.currency_id),
                    "due": f"Overdue {overdue} d"
                    if overdue
                    else format_date(self.env, move.invoice_date_due),
                    "overdue": bool(overdue),
                    "status": status,
                    "tone": tone,
                }
            )
        return {"rows": rows}
