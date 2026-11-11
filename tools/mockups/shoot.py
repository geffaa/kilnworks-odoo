"""Screenshot every mockup at desktop (1440) and phone (390); report console errors and horizontal overflow."""

import pathlib

from playwright.sync_api import sync_playwright

root = pathlib.Path(__file__).resolve().parents[2]
out = root / ".impeccable/review"
out.mkdir(parents=True, exist_ok=True)
pages = ["index", "dashboard", "purchase-order", "shopify", "components"]
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome")
    for w, tag in ((1440, "desktop"), (390, "mobile")):
        ctx = b.new_context(viewport={"width": w, "height": 900}, device_scale_factor=1)
        for name in pages:
            pg = ctx.new_page()
            errs = []
            pg.on("console", lambda m: errs.append(m.text) if m.type == "error" else None)
            pg.goto((root / "mockups" / f"{name}.html").as_uri())
            pg.wait_for_timeout(150)
            ov = pg.evaluate("document.documentElement.scrollWidth - window.innerWidth")
            pg.screenshot(path=str(out / f"{name}-{tag}.png"), full_page=True)
            print(f"{name:15} {tag:7} overflow={ov} errors={errs}")
            pg.close()
    b.close()
