"""Log in as each demo user, open the main lists, and fail on console errors. Screenshots go to docs/screenshots/."""

import pathlib
import sys

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8069"
out = pathlib.Path(__file__).resolve().parents[1] / "docs/screenshots"
out.mkdir(parents=True, exist_ok=True)
checks = [
    ("ratna", "/odoo/action-purchase.purchase_rfq", "purchase"),
    ("sekar", "/odoo/action-sale.action_orders", "sales"),
    ("ratna", "/odoo/action-stock.action_orderpoint_replenish", "replenishment"),
    ("ratna", "/odoo/action-account.action_move_out_invoice_type", "invoices"),
]
bad = 0
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    for login, path, name in checks:
        ctx = b.new_context(viewport={"width": 1440, "height": 900})
        pg = ctx.new_page()
        errs = []
        pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
        pg.goto(BASE + "/web/login")
        pg.fill("#login", login)
        pg.fill("#password", login)
        pg.click("button[type=submit]")
        pg.wait_for_url("**/odoo**")
        pg.goto(BASE + path)
        pg.wait_for_selector(".o_list_renderer", timeout=20000)
        pg.wait_for_timeout(800)
        # Empty lists render fake sample rows inside .o_view_sample_data; those do not count.
        rows = 0 if pg.locator(".o_view_sample_data").count() else pg.locator(".o_data_row").count()
        pg.screenshot(path=str(out / f"m1-{name}.png"))
        print(f"{login:6} {name:14} rows={rows} console_errors={errs}")
        bad += bool(errs) or rows == 0
        ctx.close()
    b.close()
sys.exit(1 if bad else 0)
