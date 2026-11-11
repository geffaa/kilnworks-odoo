"""Record the demo: screenshots, one clip per Upwork catalog, and the parts of the walkthrough video.

Captions are English text drawn on the page. Run against a fresh `make reset` (the payment scene pays
an invoice). Output: docs/screenshots/*.png and media/clips/*.webm; tools/make_media.sh turns the
clips into GIFs and the walkthrough.

    python3 tools/capture.py              # every scene
    python3 tools/capture.py firing api   # some scenes
"""

import json
import pathlib
import shutil
import subprocess
import sys
import time

from playwright.sync_api import sync_playwright

BASE = "http://localhost:8069"
ROOT = pathlib.Path(__file__).resolve().parents[1]
SHOTS = ROOT / "docs/screenshots"
CLIPS = ROOT / "media/clips"
VIEW = {"width": 1440, "height": 900}
API_KEY = "kw_demo0001_UfT6pGQ2y0wq3m9hVbXk7cLr1sNaZ4eJ"  # synthetic demo key, local only

OVERLAY_JS = """
([text, step]) => {
  let root = document.getElementById('kw-cap');
  if (!root) {
    root = document.createElement('div');
    root.id = 'kw-cap';
    root.innerHTML = `
      <div class="kw-cap-tag">Kilnworks on Odoo 18 · demo build, synthetic data</div>
      <div class="kw-cap-box"><span class="kw-cap-step"></span><span class="kw-cap-text"></span></div>`;
    const css = document.createElement('style');
    css.textContent = `
      #kw-cap { position: fixed; inset: 0; pointer-events: none; z-index: 2147483647;
                font-family: Inter, -apple-system, 'Segoe UI', sans-serif; }
      #kw-cap .kw-cap-tag { position: absolute; bottom: 10px; left: 14px; padding: 4px 10px;
                border-radius: 999px; background: rgba(28,38,34,.72); color: #e7efe9; font-size: 12px; }
      #kw-cap .kw-cap-box { position: absolute; left: 50%; bottom: 28px; transform: translateX(-50%);
                max-width: 1040px; display: flex; gap: 12px; align-items: center; padding: 14px 22px;
                border-radius: 12px; background: rgba(24,32,29,.92); color: #fff; font-size: 21px;
                line-height: 1.35; box-shadow: 0 10px 30px rgba(0,0,0,.25); transition: opacity .25s; }
      #kw-cap .kw-cap-step { flex: none; padding: 3px 9px; border-radius: 6px; background: #7fa99b;
                color: #10201a; font-size: 14px; font-weight: 600; letter-spacing: .02em; }
      #kw-cap .kw-cap-step:empty { display: none; }`;
    document.head.appendChild(css);
    document.body.appendChild(root);
  }
  root.querySelector('.kw-cap-step').textContent = step || '';
  root.querySelector('.kw-cap-text').textContent = text;
  root.querySelector('.kw-cap-box').style.opacity = text ? 1 : 0;
}
"""

CARD_HTML = """
<html><body style="margin:0;height:100vh;display:grid;place-items:center;background:#1d2a25;
  font-family:Inter,-apple-system,'Segoe UI',sans-serif;color:#eef4f0">
  <div style="max-width:980px;padding:0 48px">
    <div style="font-size:18px;letter-spacing:.14em;text-transform:uppercase;color:#9cc2b4">{kicker}</div>
    <div style="font-size:64px;font-weight:700;line-height:1.08;margin:18px 0 22px">{title}</div>
    <div style="font-size:26px;line-height:1.45;color:#c9d8d1">{body}</div>
  </div></body></html>
"""


class Scene:
    def __init__(self, browser, name, user=None, headers=None):
        self.name = name
        self.dir = CLIPS / f".{name}"
        shutil.rmtree(self.dir, ignore_errors=True)
        # Log in outside the recording so clips start on the first screen, not the login page.
        state = None
        if user:
            login = browser.new_context(viewport=VIEW)
            pg = login.new_page()
            pg.goto(BASE + "/web/login")
            pg.fill("#login", user)
            pg.fill("#password", user)
            pg.click("button[type=submit]")
            pg.wait_for_url("**/odoo**")
            state = login.storage_state()
            login.close()
        self.ctx = browser.new_context(
            viewport=VIEW,
            record_video_dir=str(self.dir),
            record_video_size=VIEW,
            extra_http_headers=headers or {},
            storage_state=state,
        )
        self.pg = self.ctx.new_page()
        self.t0 = time.monotonic()
        self.start = None  # seconds into the clip where the first screen is ready
        self.errors = []
        self.pg.on(
            "console",
            lambda m: self.errors.append(m.text)
            if m.type == "error" and "404" not in m.text
            else None,
        )
        self._caption = ("", "")

    def say(self, text, step="", hold=2.6):
        if self.start is None:
            self.start = max(0.0, time.monotonic() - self.t0 - 0.4)
        self._caption = (text, step)
        self.pg.evaluate(OVERLAY_JS, [text, step])
        self.pg.wait_for_timeout(int(hold * 1000))

    def recaption(self):
        self.pg.evaluate(OVERLAY_JS, list(self._caption))

    def go(self, path, wait):
        self.pg.goto(BASE + path)
        self.pg.wait_for_selector(wait, timeout=30000)
        self.pg.wait_for_timeout(700)
        self.recaption()

    def shot(self, name, full=False):
        self.pg.evaluate(
            "document.getElementById('kw-cap') && (document.getElementById('kw-cap').style.display='none')"
        )
        self.pg.screenshot(path=str(SHOTS / f"{name}.png"), full_page=full)
        self.pg.evaluate(
            "document.getElementById('kw-cap') && (document.getElementById('kw-cap').style.display='')"
        )

    def card(self, kicker, title, body, hold=4.0):
        self.pg.set_content(CARD_HTML.format(kicker=kicker, title=title, body=body))
        if self.start is None:
            self.start = max(0.0, time.monotonic() - self.t0 - 0.1)
        self.pg.wait_for_timeout(int(hold * 1000))

    def close(self):
        video = self.pg.video
        self.ctx.close()
        target = CLIPS / f"{self.name}.webm"
        video.save_as(str(target))
        (CLIPS / f"{self.name}.json").write_text(json.dumps({"start": round(self.start or 0, 2)}))
        shutil.rmtree(self.dir, ignore_errors=True)
        status = "ok" if not self.errors else f"console errors: {self.errors}"
        print(f"{self.name:10} {target.relative_to(ROOT)} {status}")
        return not self.errors


def scene_intro(b):
    s = Scene(b, "intro")
    s.card(
        "Demo build · synthetic company",
        "Kilnworks on Odoo 18",
        "Six custom modules for a stoneware workshop that sells on Shopify and to local cafés:"
        " approvals, Shopify sync, a payment gateway, a REST API, dashboards and a 16 → 18 migration.",
        hold=6,
    )
    return s.close()


def scene_outro(b):
    s = Scene(b, "outro")
    s.card(
        "Code, tests and docs",
        "github.com/geffaa/kilnworks-odoo",
        "Odoo 18 Community · OCA where it exists · about 90 automated tests in CI."
        " Kilnworks, its customers and numbers are made up.",
        hold=6,
    )
    return s.close()


def scene_approval(b):
    s = Scene(b, "approval", "ratna")
    s.go("/odoo/action-kw_approval.tier_review_action_inbox", ".o_data_row")
    s.say("Ratna, the owner, opens her approval inbox.", "Approvals", 3)
    s.shot("approval-inbox")
    s.say(
        "Purchase orders above Rp 10 M need the production lead, above Rp 25 M the owner.",
        "Approvals",
        3.6,
    )
    s.pg.locator(".o_data_row", has_text="48,600,000").first.click()
    s.pg.wait_for_selector(".o_form_view .o_form_sheet")
    s.pg.wait_for_timeout(900)
    s.recaption()
    s.say("This Rp 48.6 M order needs the production lead first, then the owner.", "Approvals", 3.6)
    s.shot("approval-po")
    s.say(
        "Creators can never approve their own documents. Requests waiting over 24 working hours escalate.",
        "Approvals",
        3.8,
    )
    s.say(
        "When Ratna is away, her delegate approves and the log says “on behalf of Ratna”.",
        "Approvals",
        3.6,
    )
    s.say("Built on OCA tier validation, not a new approval engine.", "Approvals", 3)
    return s.close()


def scene_shopify(b):
    s = Scene(b, "shopify", "bayu")
    s.go("/odoo/action-kw_shopify.kw_shopify_console_action", ".kw_store_strip")
    s.say("Shopify orders arrive through signed webhooks and become sale orders.", "Shopify", 3.4)
    s.shot("shopify-console")
    s.say(
        "Each delivery is stored once. A Shopify retry is counted, not imported twice.",
        "Shopify",
        3.2,
    )
    s.pg.locator(".kw_table tbody tr", has_text="#KW1043").first.click()
    s.pg.wait_for_timeout(800)
    s.say(
        "Order #KW1043 has a SKU Odoo doesn't know yet. It waits instead of half-importing.",
        "Shopify",
        3.6,
    )
    s.pg.click("button:has-text('Map SKU')")
    s.pg.wait_for_selector(".modal #product_id_0")
    s.pg.wait_for_timeout(500)
    s.recaption()
    s.say("Map the new Shopify SKU to the Odoo product.", "Shopify", 1.6)
    s.pg.locator(".modal #product_id_0").press_sequentially("Sage mug", delay=70)
    s.pg.wait_for_timeout(900)
    s.pg.locator(".o-autocomplete--dropdown-menu li", has_text="Sage mug").first.click()
    s.pg.wait_for_timeout(900)
    s.pg.click(".modal button:has-text('Save')")
    s.pg.wait_for_selector(".modal", state="detached")
    s.pg.wait_for_timeout(700)
    s.say("Retry: the order is queued again and processed by the job runner.", "Shopify", 1.4)
    s.pg.locator(".kw_table tbody tr", has_text="#KW1043").first.click()
    s.pg.wait_for_timeout(500)
    s.pg.click("button:has-text('Retry')")
    for _ in range(20):
        s.pg.wait_for_timeout(1000)
        s.pg.reload()
        s.pg.wait_for_selector(".kw_store_strip")
        s.pg.wait_for_timeout(500)
        s.pg.locator(".kw_table tbody tr", has_text="#KW1043").first.click()
        if s.pg.locator(".kw_table tbody tr", has_text="#KW1043").filter(has_text="Done").count():
            break
    s.pg.wait_for_timeout(700)
    s.recaption()
    s.say(
        "Done: the sale order exists. Stock changes are pushed back to Shopify in batches.",
        "Shopify",
        3.8,
    )
    s.shot("shopify-mapped")
    return s.close()


def scene_payment(b):
    link = subprocess.run(
        [
            "docker",
            "compose",
            "exec",
            "-T",
            "db",
            "psql",
            "-U",
            "odoo",
            "kilnworks",
            "-tAc",
            "select value from ir_config_parameter where key='kw_demo.payment_link'",
        ],
        capture_output=True,
        text=True,
        check=True,
        cwd=ROOT,
    ).stdout.strip()
    s = Scene(b, "payment")
    s.pg.goto(link)
    s.pg.wait_for_timeout(900)
    s.say("A café opens its invoice from the payment link.", "Midtrans", 3)
    s.shot("payment-portal")
    s.pg.locator("a:has-text('Pay Now'), button:has-text('Pay Now')").first.click()
    s.pg.wait_for_timeout(900)
    s.recaption()
    s.say(
        "Midtrans is not in Odoo, so it is a payment provider written from scratch.",
        "Midtrans",
        3.4,
    )
    s.shot("payment-methods")
    s.pg.locator("text=BCA").first.click()
    s.say("The customer picks a BCA virtual account.", "Midtrans", 2.4)
    s.pg.locator("button[name=o_payment_submit_button]").first.click()
    s.pg.wait_for_selector("button.pay", timeout=20000)
    s.pg.wait_for_timeout(600)
    s.recaption()
    s.say("Midtrans payment page (a local mock in this demo).", "Midtrans", 3)
    s.pg.click("button.pay")
    s.pg.wait_for_url("**/my/invoices/**", timeout=20000)
    s.pg.wait_for_selector("text=Paid", timeout=20000)
    s.pg.wait_for_timeout(600)
    s.recaption()
    s.say(
        "The signed notification is checked for signature and amount. The invoice is paid.",
        "Midtrans",
        3.8,
    )
    s.shot("payment-paid")
    return s.close()


TERMINAL_HTML = """
<html><body style="margin:0;height:100vh;background:#18201d;font-family:'JetBrains Mono',Menlo,monospace;
  color:#dfe8e3;font-size:19px;line-height:1.55">
  <div style="padding:56px 72px">{body}</div></body></html>
"""


def _term(lines):
    import html

    out = []
    for kind, text in lines:
        color = {"cmd": "#9cc2b4", "ok": "#dfe8e3", "bad": "#e8a07a", "dim": "#7d8d86"}[kind]
        prefix = "$ " if kind == "cmd" else ""
        out.append(
            f'<div style="color:{color};white-space:pre-wrap">{prefix}{html.escape(text)}</div>'
        )
    return TERMINAL_HTML.format(body="".join(out))


def scene_api(b):
    import json

    s = Scene(b, "api")
    req = s.ctx.request
    auth = {"Authorization": f"Bearer {API_KEY}"}
    spec = req.get(BASE + "/api/v1/docs").json()
    routes = [
        f"{m.upper():5} /api/v1{p:16} scope {v.get('x-scope')}"
        for p, o in spec["paths"].items()
        for m, v in o.items()
    ]
    s.pg.set_content(
        _term(
            [("cmd", "curl localhost:8069/api/v1/docs   # OpenAPI 3.1")]
            + [("ok", r) for r in routes]
        )
    )
    s.say("A versioned REST API at /api/v1, documented with OpenAPI.", "REST API", 3.6)
    s.shot("api-docs")
    url = "/api/v1/stock?sku=KW-PLT-270-SPK"
    anon = req.get(BASE + url)
    ok = req.get(BASE + url, headers=auth)
    lines = [
        ("cmd", f"curl localhost:8069{url}"),
        ("bad", f"HTTP {anon.status} {json.dumps(anon.json())}"),
        ("dim", " "),
        ("cmd", f'curl -H "Authorization: Bearer kw_demo0001_…" localhost:8069{url}'),
        ("ok", f"HTTP {ok.status}"),
        ("ok", json.dumps(ok.json(), indent=2)),
    ]
    s.pg.set_content(_term(lines))
    s.say(
        "No key, no data. With a key: live stock, with Odoo's access rules applied.", "REST API", 4
    )
    s.shot("api-stock")
    s.say(
        "Keys are stored as hashes, with scopes, rotation, expiry and 60 requests a minute.",
        "REST API",
        3.6,
    )
    s.say(
        "Outgoing webhooks (order.confirmed, stock.low) are signed and retried for up to 6 hours.",
        "REST API",
        3.8,
    )
    return s.close()


def scene_dashboard(b):
    s = Scene(b, "dashboard", "ratna")
    s.go("/odoo/action-kw_ops_dashboard.action_dashboard", ".kw_dash .kw_attn")
    s.say("Monday morning numbers in one screen, inside Odoo Community.", "Dashboard", 3.4)
    s.shot("dashboard-desktop", full=True)
    s.say(
        "What needs attention first: approvals, failed syncs, low stock, invoices due.",
        "Dashboard",
        3.6,
    )
    s.pg.mouse.wheel(0, 600)
    s.pg.wait_for_timeout(700)
    s.say("Revenue by channel, compared with the previous period.", "Dashboard", 3.2)
    s.pg.mouse.wheel(0, 700)
    s.pg.wait_for_timeout(700)
    s.say(
        "Every number opens the records behind it. Built with OWL, covered by a browser test.",
        "Dashboard",
        3.6,
    )
    return s.close()


def scene_firing(b):
    s = Scene(b, "firing", "ratna")
    s.go("/odoo/action-kw_firing_batch.kw_firing_batch_action", ".o_data_row")
    s.say("Firing batches: a module first written for Odoo 16.", "Migration", 3.2)
    s.shot("firing-batches")
    s.say("Migrated to Odoo 18 in its own commit: views, Python API, OWL field.", "Migration", 3.6)
    s.pg.locator(".o_data_row", has_text="Done").first.click()
    s.pg.wait_for_selector(".o_form_view .o_form_sheet")
    s.pg.wait_for_timeout(900)
    s.recaption()
    s.say(
        "The temperature field was renamed. A migration script kept every recorded value.",
        "Migration",
        3.8,
    )
    s.shot("firing-batch-form")
    s.say(
        "Rehearsed on a copy: Odoo 16 database → OpenUpgrade 17 → 18 → module script.",
        "Migration",
        3.8,
    )
    return s.close()


SCENES = {
    "intro": scene_intro,
    "approval": scene_approval,
    "shopify": scene_shopify,
    "payment": scene_payment,
    "api": scene_api,
    "dashboard": scene_dashboard,
    "firing": scene_firing,
    "outro": scene_outro,
}

if __name__ == "__main__":
    SHOTS.mkdir(parents=True, exist_ok=True)
    CLIPS.mkdir(parents=True, exist_ok=True)
    wanted = sys.argv[1:] or list(SCENES)
    ok = True
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome")
        for name in wanted:
            ok &= SCENES[name](browser)
        browser.close()
    sys.exit(0 if ok else 1)
