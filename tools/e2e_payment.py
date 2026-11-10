"""Pay the demo's open invoice end to end: portal -> Midtrans (mock) -> signed notification -> paid.

Run after `make demo` (resets are not needed afterwards; the next `make reset` restores it).
"""

import subprocess
import sys

from playwright.sync_api import sync_playwright


def psql(sql):
    return subprocess.run(
        ["docker", "compose", "exec", "-T", "db", "psql", "-U", "odoo", "kilnworks", "-tAc", sql],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()


link = psql("select value from ir_config_parameter where key='kw_demo.payment_link'")
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome")
    page = browser.new_page(viewport={"width": 1280, "height": 900})
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(link)
    page.locator("a:has-text('Pay Now'), button:has-text('Pay Now')").first.click()
    page.locator("text=BCA").first.click()
    page.locator("button[name=o_payment_submit_button]").first.click()
    page.wait_for_selector("button.pay", timeout=20000)  # the mock's payment page
    page.click("button.pay")
    page.wait_for_url("**/my/invoices/**", timeout=20000)
    page.wait_for_selector("text=Paid", timeout=20000)
    browser.close()

state = psql(
    "select m.payment_state from payment_transaction t join account_invoice_transaction_rel r "
    "on r.transaction_id = t.id join account_move m on m.id = r.invoice_id "
    "where t.state = 'done' order by t.id desc limit 1"
)
print(f"invoice payment_state={state} console_errors={errors}")
sys.exit(0 if state in ("paid", "in_payment") and not errors else 1)
