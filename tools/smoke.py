"""Log in as each demo user, open the main screens, and fail on console errors or wrong row counts.

Screenshots go to docs/screenshots/. Run against `make demo` on localhost:8069.
"""

import pathlib
import sys

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8069"
out = pathlib.Path(__file__).resolve().parents[1] / "docs/screenshots"
out.mkdir(parents=True, exist_ok=True)

# login, path, screenshot name, expected rows (None = any non-zero)
checks = [
    ("ratna", "/odoo/action-purchase.purchase_rfq", "purchase", None),
    ("sekar", "/odoo/action-sale.action_orders", "sales", None),
    # Odoo's replenishment filter depends on forecast timing, so only require rows here; the
    # dashboard's "below minimum" count is computed from on-hand stock and checked in tests.
    ("ratna", "/odoo/action-stock.action_orderpoint_replenish", "replenishment", None),
    ("ratna", "/odoo/action-account.action_move_out_invoice_type", "invoices", None),
    ("ratna", "/odoo/action-kw_approval.tier_review_action_inbox", "approvals", 3),
    # Sekar is Ratna's delegate this week: she sees the two purchase reviews, not her own quote.
    ("sekar", "/odoo/action-kw_approval.tier_review_action_inbox", "approvals-delegate", 2),
]


def login(browser, user):
    ctx = browser.new_context(viewport={"width": 1440, "height": 900})
    pg = ctx.new_page()
    errs = []
    pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
    pg.goto(BASE + "/web/login")
    pg.fill("#login", user)
    pg.fill("#password", user)
    pg.click("button[type=submit]")
    pg.wait_for_url("**/odoo**")
    return ctx, pg, errs


def count_rows(pg):
    pg.wait_for_selector(".o_list_renderer", timeout=20000)
    pg.wait_for_timeout(800)
    # Empty lists render fake sample rows inside .o_view_sample_data; those do not count.
    if pg.locator(".o_view_sample_data").count():
        return 0
    return pg.locator(".o_data_row").count()


bad = 0
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    for user, path, name, expected in checks:
        ctx, pg, errs = login(browser, user)
        pg.goto(BASE + path)
        rows = count_rows(pg)
        pg.screenshot(path=str(out / f"{name}.png"))
        ok = not errs and rows > 0 and (expected is None or rows == expected)
        print(f"{user:6} {name:19} rows={rows:<3} errors={errs} {'ok' if ok else 'FAIL'}")
        bad += not ok
        if name == "approvals":
            # Open the escalated purchase order from the inbox, as the demo video does.
            pg.locator(".o_data_row", has_text="48,600,000").first.click()
            pg.wait_for_selector(".o_form_view .o_form_sheet")
            pg.wait_for_timeout(1200)
            pg.screenshot(path=str(out / "approval-po.png"), full_page=True)
            ok = not errs
            print(f"{user:6} {'approval-po':19} errors={errs} {'ok' if ok else 'FAIL'}")
            bad += not ok
        ctx.close()
    # The dashboard and the Shopify console are client actions, not lists.
    for width, tag in ((1440, "desktop"), (390, "mobile")):
        ctx, pg, errs = login(browser, "ratna")
        pg.set_viewport_size({"width": width, "height": 900})
        pg.goto(BASE + "/odoo/action-kw_ops_dashboard.action_dashboard")
        pg.wait_for_selector(".kw_dash .kw_attn", timeout=20000)
        pg.wait_for_timeout(800)
        overflow = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
        pg.screenshot(path=str(out / f"dashboard-{tag}.png"), full_page=True)
        ok = not errs and overflow <= 0
        print(
            f"{'ratna':6} {'dashboard-' + tag:19} overflow={overflow:<3} errors={errs} {'ok' if ok else 'FAIL'}"
        )
        bad += not ok
        ctx.close()
    ctx, pg, errs = login(browser, "bayu")
    pg.goto(BASE + "/odoo/action-kw_shopify.kw_shopify_console_action")
    pg.wait_for_selector(".kw_store_strip", timeout=20000)
    pg.wait_for_timeout(800)
    rows = pg.locator(".kw_table tbody tr").count()
    pg.screenshot(path=str(out / "shopify-console.png"), full_page=True)
    ok = not errs and rows > 0
    print(
        f"{'bayu':6} {'shopify-console':19} rows={rows:<3} errors={errs} {'ok' if ok else 'FAIL'}"
    )
    bad += not ok
    ctx.close()
    browser.close()
sys.exit(1 if bad else 0)
