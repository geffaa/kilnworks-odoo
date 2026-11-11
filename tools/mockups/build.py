"""Build static mockups for Kilnworks on Odoo (synthetic data).

Usage: LUCIDE_DIR=<lucide-static>/icons python3 tools/mockups/build.py
Icons come from the shared portfolio kit (official Lucide via lucide-static).
"""

import pathlib
import sys

sys.path.insert(0, str(pathlib.Path.home() / "Project/portfolio-roadmap/design-system/tools"))
from kit import Icons  # noqa: E402

OUT = pathlib.Path(__file__).resolve().parents[2] / "mockups"


def page(title, body, ic, active=None, crumbs_app="Kilnworks Ops"):
    menu = [
        ("Dashboard", "dashboard.html"),
        ("Approvals", "#"),
        ("Shopify", "shopify.html"),
        ("Firing Batches", "#"),
        ("Configuration", "#"),
    ]
    if crumbs_app == "Purchase":
        menu = [
            ("Orders", "purchase-order.html"),
            ("Products", "#"),
            ("Reporting", "#"),
            ("Configuration", "#"),
        ]
    items = "".join(
        f'<li><a href="{h}"{" aria-current=\"page\"" if n == active else ""}>{n}</a></li>'
        for n, h in menu
    )
    nav = f"""<header class="o-navbar">
  <button class="o-apps" aria-label="Home menu">{ic("layout-grid")}</button>
  <button class="o-apps o-burger" aria-label="Open menu">{ic("menu")}</button>
  <span class="o-appname">{crumbs_app}</span>
  <nav aria-label="{crumbs_app} menu"><ul class="o-menu">{items}</ul></nav>
  <div class="o-systray">
    <button aria-label="Messages, 3 unread">{ic("message-square")}<span class="o-badge-count">3</span></button>
    <button aria-label="Activities, 5 due">{ic("clock")}<span class="o-badge-count">5</span></button>
    <span class="o-company">Kilnworks Stoneware</span>
    <span class="o-avatar" role="img" aria-label="Ratna Wibisono">RW</span>
  </div>
</header>"""
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} · Kilnworks on Odoo</title>
<link rel="stylesheet" href="kilnworks-ds.css"></head>
<body>
{ic.sprite()}
{nav}
{body}
</body></html>"""


# ---------------------------------------------------------------- dashboard
def dashboard():
    ic = Icons()
    weeks = ["13 Oct", "20 Oct", "27 Oct", "3 Nov", "10 Nov"]
    b2b = [38.1, 46.7, 41.2, 52.6, 5.65]  # Rp million, sums to 184.25
    shp = [33.9, 35.2, 40.6, 39.8, 6.9]  # Rp million (USD converted), sums to 156.4
    W, H, pad_l, pad_b, top = 640, 220, 40, 26, 10
    vmax = 60
    plot_h = H - pad_b - top
    group_w = (W - pad_l) / len(weeks)
    bar_w = 22
    bars = []
    for g in (0, 20, 40, 60):
        y = top + plot_h - g / vmax * plot_h
        bars.append(
            f'<line x1="{pad_l}" x2="{W}" y1="{y:.1f}" y2="{y:.1f}" stroke="#eceef1"/>'
            f'<text x="{pad_l - 8}" y="{y + 4:.1f}" text-anchor="end">{g}</text>'
        )
    for i, wk in enumerate(weeks):
        cx = pad_l + group_w * i + group_w / 2
        for j, (v, col) in enumerate(((b2b[i], "var(--kw-clay)"), (shp[i], "var(--kw-celadon)"))):
            h = v / vmax * plot_h
            x = cx - bar_w - 1 + j * (bar_w + 2)
            label = ("B2B" if j == 0 else "Shopify") + f" week of {wk}: Rp {v:.1f} million"
            bars.append(
                f'<rect x="{x:.1f}" y="{top + plot_h - h:.1f}" width="{bar_w}" height="{h:.1f}" rx="2" '
                f'fill="{col}"><title>{label}</title></rect>'
            )
        bars.append(
            f'<text x="{cx:.1f}" y="{H - 8}" text-anchor="middle">{wk}{" *" if i == 4 else ""}</text>'
        )
    chart = (
        f'<svg class="chart" viewBox="0 0 {W} {H}" role="img" aria-label="Weekly revenue by channel, '
        f'last 30 days, in Rp million">{"".join(bars)}</svg>'
    )

    approvals = [
        (
            "PO/2026/0418",
            "Sumber Lempung Godean",
            "Purchase · tier 1 of 2",
            "Rp 48,600,000",
            "26 h",
            True,
            "You",
        ),
        (
            "S/2026/1184",
            "Teras Kopi Jakal",
            "Discount 15% · owner",
            "Rp 20,945,700",
            "5 h",
            False,
            "You",
        ),
        (
            "PO/2026/0419",
            "UD Glasir Tirta Mulya",
            "Purchase · tier 1 of 1",
            "Rp 18,300,000",
            "2 h",
            False,
            "You",
        ),
    ]
    arows = "".join(
        f'<tr><td><a href="purchase-order.html">{n}</a><span class="sub">{p}</span></td>'
        f'<td class="hide-sm">{k}</td><td class="r num">{a}</td>'
        f'<td class="r"><span class="age{" late" if late else ""}">{age}</span></td></tr>'
        for n, p, k, a, age, late, _ in approvals
    )
    sync = [
        (
            "#KW1043",
            "orders/create",
            "Needs mapping",
            "b-warning",
            "SKU KW-MUG-350-SAGE has no Odoo product",
            "09:17",
        ),
        (
            "#KW1044",
            "orders/create",
            "Retrying",
            "b-info",
            "Shopify throttled the call · next try 09:31",
            "09:26",
        ),
    ]
    srows = "".join(
        f'<tr><td><a href="shopify.html">{o}</a><span class="sub">{t}</span></td>'
        f'<td><span class="badge {cls}">{s}</span><span class="sub">{why}</span></td>'
        f'<td class="r num muted">{tm}</td></tr>'
        for o, t, s, cls, why, tm in sync
    )
    stock = [
        ("Celadon mug 350 ml", "KW-MUG-350-CEL", 42, 120, "mid"),
        ("Speckled dinner plate 27 cm", "KW-PLT-270-SPK", 18, 80, ""),
        ("Ash-glaze ramen bowl", "KW-BWL-900-ASH", 9, 60, ""),
        ("Espresso cup 90 ml, sand", "KW-ESP-090-SND", 64, 150, "mid"),
        ("Pour-over dripper, iron red", "KW-DRP-002-IRR", 11, 40, ""),
    ]
    strows = "".join(
        f'<tr><td>{n}<span class="sub mono">{s}</span></td>'
        f'<td class="r num">{q} <span class="muted">/ {m}</span></td>'
        f'<td class="hide-sm"><div class="stockbar" role="img" aria-label="{round(q / m * 100)}% of minimum">'
        f'<i class="{c}" style="width:{min(100, q / m * 100):.0f}%"></i></div></td></tr>'
        for n, s, q, m, c in stock
    )
    inv = [
        ("INV/2026/00391", "Teras Kopi Jakal", "Rp 21,420,000", "12 Nov", "Link sent", "b-info"),
        (
            "INV/2026/00377",
            "Wisma Lereng Merapi",
            "Rp 64,800,000",
            "Overdue 3 d",
            "No payment",
            "b-danger",
        ),
        (
            "INV/2026/00385",
            "Kedai Seduh Pakem",
            "Rp 8,910,000",
            "15 Nov",
            "VA pending",
            "b-warning",
        ),
    ]
    invrows = "".join(
        f'<tr><td>{n}<span class="sub">{c}</span></td><td class="r num">{a}</td>'
        f'<td class="r"><span class="num">{d}</span><span class="sub"><span class="badge {cls}">{s}</span></span></td></tr>'
        for n, c, a, d, s, cls in inv
    )

    body = f"""<div class="o-cp">
  <div class="o-bc"><span class="cur">Dashboard</span></div>
  <div class="o-cp-right">
    <div class="seg" role="radiogroup" aria-label="Period">
      <button role="radio" aria-checked="false">7 days</button>
      <button role="radio" aria-checked="true">30 days</button>
      <button role="radio" aria-checked="false">90 days</button>
    </div>
    <button class="btn btn-ghost btn-icon" aria-label="Refresh">{ic("refresh-cw")}</button>
  </div>
</div>
<main class="o-content">
  <div class="dash">
    <div class="span-12 attn" aria-label="Needs attention">
      <section>
        <div class="attn-h"><span class="big">3</span><h2>approvals waiting</h2>
          <a class="end" href="#">Open inbox</a></div>
        <div class="tbl-wrap"><table class="o-list"><caption class="sr-only">Approvals waiting</caption>
          <thead><tr><th>Document</th><th class="hide-sm">Rule</th><th class="r">Amount</th><th class="r">Waiting</th></tr></thead>
          <tbody>{arows}</tbody></table></div>
      </section>
      <section>
        <div class="attn-h"><span class="big">2</span><h2>Shopify events need a look</h2>
          <a class="end" href="shopify.html">Open sync log</a></div>
        <div class="tbl-wrap"><table class="o-list"><caption class="sr-only">Sync events needing attention</caption>
          <thead><tr><th>Order</th><th>State</th><th class="r">Received</th></tr></thead>
          <tbody>{srows}</tbody></table></div>
        <p class="panel-f muted">45 of 47 events in the last 24 h were processed. Stock pushed at 09:20 (18 items).</p>
      </section>
    </div>

    <section class="panel span-7" aria-labelledby="rev-h">
      <div class="panel-h"><h2 id="rev-h">Revenue by channel</h2><span class="count">11 Oct – 10 Nov 2026</span></div>
      <div class="panel-b">
        <div class="channel">
          <div><div class="k"><span class="key" style="background:var(--kw-clay)"></span>B2B · 23 orders</div>
            <div class="v num">Rp 184,250,000</div><div class="d up num">+13.8% vs previous 30 days</div></div>
          <div><div class="k"><span class="key" style="background:var(--kw-celadon)"></span>Shopify · 212 orders</div>
            <div class="v num">US$ 9,842</div><div class="d down num">−4.1% · ≈ Rp 156,400,000</div></div>
        </div>
        {chart}
        <p class="synthetic">Rp million per week. * Week in progress. USD converted at the company rate on each order date. Synthetic data.</p>
      </div>
    </section>

    <section class="panel span-5" aria-labelledby="stk-h">
      <div class="panel-h"><h2 id="stk-h">Below minimum stock</h2><span class="count">5 of 18 products</span>
        <div class="end"><a href="#" class="btn btn-sm btn-ghost">Replenish</a></div></div>
      <div class="tbl-wrap"><table class="o-list"><caption class="sr-only">Products below minimum</caption>
        <thead><tr><th>Product</th><th class="r">On hand / min</th><th class="hide-sm"></th></tr></thead>
        <tbody>{strows}</tbody></table></div>
    </section>

    <section class="panel span-7" aria-labelledby="inv-h">
      <div class="panel-h"><h2 id="inv-h">B2B invoices due</h2><span class="count">Midtrans payment links</span></div>
      <div class="tbl-wrap"><table class="o-list"><caption class="sr-only">Invoices due</caption>
        <thead><tr><th>Invoice</th><th class="r">Amount</th><th class="r">Due</th></tr></thead>
        <tbody>{invrows}</tbody></table></div>
    </section>

    <section class="panel span-5" aria-labelledby="st-h">
      <div class="panel-h"><h2 id="st-h">Block states</h2><span class="count">how each block behaves</span></div>
      <div class="panel-b" style="display:grid;gap:var(--s4)">
        <div aria-hidden="true"><div class="skel" style="width:60%"></div><div class="skel" style="width:90%;margin-top:8px"></div>
          <div class="skel" style="width:75%;margin-top:8px"></div><p class="synthetic" style="margin:6px 0 0">Loading</p></div>
        <div class="empty" style="padding:var(--s3) 0">{ic("store")}<h3>No orders yet</h3>
          <p>Connect a Shopify store in Configuration › Stores, or confirm a B2B quotation.</p></div>
        <div class="alert alert-warning" style="margin:0">{ic("triangle-alert")}<div>Couldn't load revenue: the server took too long.
          <a href="#">Try again</a></div></div>
      </div>
    </section>
  </div>
  <p class="synthetic" style="margin-top:var(--s4)">Kilnworks is a synthetic company. Every name, amount and order on this page is made up for the demo.</p>
</main>"""
    return page("Dashboard", body, ic, active="Dashboard")


# ---------------------------------------------------------------- purchase order
def purchase_order():
    ic = Icons()
    lines = [
        ("Stoneware clay, Godean, 25 kg sack", "2,400.00 kg", "14,500.00", "34,800,000.00"),
        ("Celadon glaze base, dry", "60.00 kg", "180,000.00", "10,800,000.00"),
        ("Export carton 5-ply, 40×30×30 cm", "400.00 Units", "7,500.00", "3,000,000.00"),
    ]
    lrows = "".join(
        f'<tr><td>{p}</td><td class="r num">{q}</td><td class="r num">{u}</td>'
        f'<td class="r num hide-sm">—</td><td class="r num">Rp {s}</td></tr>'
        for p, q, u, s in lines
    )
    body = f"""<div class="o-cp">
  <div class="o-bc"><a href="#">Requests for Quotation</a><span class="sep">/</span><span class="cur">PO/2026/0418</span></div>
  <div class="o-cp-right"><span class="o-pager">4 / 12 <button class="btn btn-ghost btn-icon btn-sm" aria-label="Previous">{ic("chevron-left")}</button>
    <button class="btn btn-ghost btn-icon btn-sm" aria-label="Next">{ic("chevron-right")}</button></span></div>
</div>
<div class="o-form-wrap">
  <main class="o-form-main">
    <div class="o-statusbar">
      <div class="o-cp-actions">
        <button class="btn btn-primary" aria-disabled="true" title="Waiting for validation">Confirm Order</button>
        <button class="btn btn-secondary">Send by Email</button>
        <button class="btn btn-secondary">Print RFQ</button>
        <button class="btn btn-secondary">Cancel</button>
      </div>
      <div class="o-status" aria-label="Status">
        <span>RFQ</span><span>RFQ Sent</span><span aria-current="step">Waiting Validation</span><span>Purchase Order</span>
      </div>
    </div>
    <div class="alert alert-warning" role="status">{ic("shield-alert")}<div><b>This order needs 2 approvals before it can be confirmed.</b>
      Amount Rp 48,600,000 is above the Rp 25,000,000 limit, so the owner approves after the production lead. Tier 1 has waited 26 hours and was escalated to you.</div></div>
    <div class="o-sheet">
      <div class="o-title"><small>Purchase Order</small><h1>PO/2026/0418</h1></div>
      <div class="o-groups">
        <div>
          <div class="o-field"><label>Vendor</label><div class="val"><a href="#">CV Sumber Lempung Godean</a></div></div>
          <div class="o-field"><label>Vendor Reference</label><div class="val">SLG/INV/11-026</div></div>
          <div class="o-field"><label>Currency</label><div class="val">IDR</div></div>
        </div>
        <div>
          <div class="o-field"><label>Order Deadline</label><div class="val num">11/12/2026 10:00</div></div>
          <div class="o-field"><label>Expected Arrival</label><div class="val num">11/14/2026</div></div>
          <div class="o-field"><label>Buyer</label><div class="val">Dimas Pratama</div></div>
        </div>
      </div>

      <div class="o-notebook">
        <div class="o-tabs" role="tablist">
          <button role="tab" aria-selected="false">Products</button>
          <button role="tab" aria-selected="true">Validation <span class="tab-count">2 pending</span></button>
          <button role="tab" aria-selected="false">Other Information</button>
        </div>
        <div role="tabpanel">
          <ol class="tier-steps">
            <li><span class="step-dot now">1</span>
              <div><div class="who">Head of production → Ratna Wibisono</div>
                <div class="note">{ic("corner-down-right")} Redirected: Dimas Pratama created this order and cannot approve it.</div>
                <div class="note">{ic("bell-ring")} Escalated 11/10 09:00 after 24 working hours. Sekar Ayuningtyas may act for you (delegation 11/10–11/14).</div></div>
              <span class="badge b-warning">Waiting · 26 h</span></li>
            <li><span class="step-dot">2</span>
              <div><div class="who">Owner · Ratna Wibisono</div><div class="note">Starts after tier 1 is approved.</div></div>
              <span class="badge b-muted">Not started</span></li>
          </ol>
          <div class="decision">
            <button class="btn btn-primary">{ic("check")}Approve tier 1</button>
            <button class="btn btn-danger-ghost">{ic("x")}Reject…</button>
            <span class="synthetic">Approving both tiers yourself is allowed for the owner; each is recorded separately.</span>
          </div>
        </div>
      </div>

      <h2 style="font-size:var(--fs-lg);margin:var(--s6) 0 var(--s2)">Products</h2>
      <div class="tbl-wrap"><table class="o-list"><caption class="sr-only">Order lines</caption>
        <thead><tr><th>Product</th><th class="r">Quantity</th><th class="r">Unit Price</th><th class="r hide-sm">Taxes</th><th class="r">Amount</th></tr></thead>
        <tbody>{lrows}</tbody></table></div>
      <div class="totals"><span>Untaxed Amount:</span><span class="num">Rp 48,600,000.00</span>
        <span>Taxes:</span><span class="num">Rp 0.00</span>
        <span class="t">Total:</span><span class="t num">Rp 48,600,000.00</span></div>
      <p class="synthetic">Vendor is not VAT-registered (non-PKP), so no tax applies. Synthetic data.</p>
    </div>
  </main>
  <aside class="o-chatter" aria-label="Chatter">
    <div class="o-chatter-top"><button class="btn btn-primary btn-sm">Send message</button><button class="btn btn-secondary btn-sm">Log note</button>
      <button class="btn btn-secondary btn-sm">{ic("clock", "icon icon-sm")}Activities</button></div>
    <div class="o-day">Today</div>
    <div class="msg"><span class="o-avatar av-bot">OB</span><div><div class="h"><b>OdooBot</b><span>09:00</span></div>
      <p>Tier 1 validation has waited more than 24 working hours. Escalated to Ratna Wibisono.</p></div></div>
    <div class="o-day">Yesterday</div>
    <div class="msg"><span class="o-avatar av-bot">OB</span><div><div class="h"><b>OdooBot</b><span>07:12</span></div>
      <p>Tier 1 reviewer changed from Dimas Pratama to Ratna Wibisono: the creator of a document cannot approve it.</p></div></div>
    <div class="msg"><span class="o-avatar av-d">DP</span><div><div class="h"><b>Dimas Pratama</b><span>07:12</span></div>
      <p>Clay for the December glaze run. Price is up Rp 500/kg from October, still below Bantul suppliers.</p>
      <div class="track">Status: RFQ Sent → Waiting Validation</div></div></div>
    <div class="msg"><span class="o-avatar av-d">DP</span><div><div class="h"><b>Dimas Pratama</b><span>Nov 8</span></div>
      <p>RFQ sent to CV Sumber Lempung Godean.</p></div></div>
  </aside>
</div>"""
    return page("PO/2026/0418", body, ic, active="Orders", crumbs_app="Purchase")


# ---------------------------------------------------------------- shopify console
def shopify():
    ic = Icons()
    ev = [
        ("09:26", "#KW1044", "orders/create", "Retrying", "b-info", "—", False),
        ("09:17", "#KW1043", "orders/create", "Needs mapping", "b-warning", "—", True),
        ("09:14", "#KW1042", "orders/create", "Done", "b-success", "S/2026/1203", False),
        ("09:02", "#KW1031", "orders/cancelled", "Done", "b-success", "S/2026/1189", False),
        ("08:47", "#KW1041", "orders/create", "Done", "b-success", "S/2026/1202", False),
        ("08:31", "#KW1040", "orders/create", "Done", "b-success", "S/2026/1201", False),
        ("07:55", "#KW1039", "orders/create", "Done", "b-success", "S/2026/1200", False),
        ("06:10", "#KW1038", "orders/create", "Done", "b-success", "S/2026/1199", False),
    ]
    rows = "".join(
        f'<tr{" aria-selected=\"true\"" if sel else ""}><td class="num muted">{t}</td><td><b>{o}</b>'
        f'<span class="sub">{tp}</span></td><td><span class="badge {cls}">{s}</span></td>'
        f'<td class="hide-sm">{so if so == "—" else f"<a href=\"#\">{so}</a>"}</td></tr>'
        for t, o, tp, s, cls, so, sel in ev
    )
    payload = (
        '{\n  <span class="pk">"name"</span>: <span class="ps">"#KW1043"</span>,\n'
        '  <span class="pk">"currency"</span>: <span class="ps">"USD"</span>,\n'
        '  <span class="pk">"total_price"</span>: <span class="ps">"118.00"</span>,\n'
        '  <span class="pk">"customer"</span>: { <span class="pk">"email"</span>: <span class="ps">"m.okafor@example.com"</span> },\n'
        '  <span class="pk">"line_items"</span>: [\n'
        '    { <span class="pk">"sku"</span>: <span class="ps">"KW-MUG-350-SAGE"</span>, <span class="pk">"quantity"</span>: <span class="pn">4</span>, <span class="pk">"price"</span>: <span class="ps">"24.00"</span> },\n'
        '    { <span class="pk">"sku"</span>: <span class="ps">"KW-PLT-210-SPK"</span>, <span class="pk">"quantity"</span>: <span class="pn">1</span>, <span class="pk">"price"</span>: <span class="ps">"22.00"</span> }\n'
        "  ]\n}"
    )
    body = f"""<div class="o-cp">
  <div class="o-bc"><span class="cur">Shopify</span></div>
  <div class="o-cp-right">
    <button class="btn btn-secondary">{ic("upload")}Push stock now</button>
    <button class="btn btn-ghost btn-icon" aria-label="Store settings">{ic("settings")}</button>
  </div>
</div>
<main class="o-content">
  <div class="store-strip">
    <span class="store-mark">{ic("store")}</span>
    <div><div style="font-weight:600">kilnworks-studio.myshopify.com</div>
      <div class="store-facts"><span><span class="ok-dot"></span><b>Connected</b></span><span>API <b>2025-10</b></span>
        <span>Webhooks <b>4 of 4</b> registered</span><span>Stock push <b>09:20</b>, 18 items</span><span>Location <b>WH/Stock</b></span></div></div>
    <a class="btn btn-ghost" href="#">{ic("link")}Product map · 34 SKUs</a>
  </div>
  <div class="console">
    <section class="panel" aria-labelledby="ev-h">
      <div class="panel-h"><h2 id="ev-h">Sync log</h2><span class="count">last 24 hours</span></div>
      <div class="filters">
        <div class="seg" role="radiogroup" aria-label="Filter by state">
          <button role="radio" aria-checked="false">All <span class="n">47</span></button>
          <button role="radio" aria-checked="true">Needs a look <span class="n">2</span></button>
          <button role="radio" aria-checked="false">Done <span class="n">45</span></button>
        </div>
        <div class="search" role="search">{ic("search", "icon icon-sm")}<span>Search order or SKU</span></div>
      </div>
      <div class="tbl-wrap"><table class="o-list"><caption class="sr-only">Webhook events</caption>
        <thead><tr><th>Received</th><th>Order</th><th>State</th><th class="hide-sm">Sale order</th></tr></thead>
        <tbody>{rows}</tbody></table></div>
      <p class="panel-f muted">Showing the 2 that need a look plus the latest done. Duplicate deliveries are ignored by webhook ID (3 today).</p>
    </section>

    <section class="panel detail" aria-labelledby="dt-h">
      <div class="panel-h"><h2 id="dt-h">#KW1043</h2><span class="badge b-warning">Needs mapping</span>
        <div class="end"><button class="btn btn-sm btn-ghost" aria-label="Close detail">{ic("x", "icon icon-sm")}</button></div></div>
      <div class="panel-b">
        <dl>
          <dt>Topic</dt><dd>orders/create</dd>
          <dt>Webhook ID</dt><dd class="mono">b54557e4-bdd9-4b37-8a5f-bf7d70bcd043</dd>
          <dt>Signature</dt><dd>{ic("shield-check", "icon icon-sm")} HMAC valid</dd>
          <dt>Order total</dt><dd class="num">US$ 118.00 · 2 lines</dd>
          <dt>Attempts</dt><dd>1 · stopped, waiting for a fix</dd>
        </dl>
        <div class="fix"><h3>SKU KW-MUG-350-SAGE has no Odoo product</h3>
          <p>No sale order was created, so nothing is half-imported. Map the SKU, then retry. The sage glaze was added in Shopify on Nov 9.</p></div>
        <div class="decision" style="border-top:0;padding-top:0">
          <button class="btn btn-primary">{ic("link")}Map SKU</button>
          <button class="btn btn-secondary" aria-disabled="true" title="Map the SKU first">{ic("rotate-cw")}Retry</button>
        </div>
        <ul class="timeline" aria-label="Event history">
          <li><time>09:17:04</time><span>Received, signature checked, stored</span></li>
          <li><time>09:17:05</time><span>Queued on channel root.kw_shopify</span></li>
          <li><time>09:17:06</time><span>Stopped: 1 of 2 SKUs unmapped</span></li>
        </ul>
        <pre class="payload" aria-label="Payload excerpt">{payload}</pre>
      </div>
    </section>
  </div>
  <p class="synthetic" style="margin-top:var(--s4)">Synthetic data. Store, customers and orders are made up for the demo.</p>
</main>"""
    return page("Shopify", body, ic, active="Shopify")


# ---------------------------------------------------------------- components
def components():
    ic = Icons()
    days = []
    # November 2026 starts on a Sunday; grid starts Monday
    days += [f'<button class="out" tabindex="-1">{d}</button>' for d in range(26, 32)]
    for d in range(1, 31):
        cls = []
        if d in (10, 14):
            cls.append("edge")
        elif 10 < d < 14:
            cls.append("range")
        if d == 10:
            cls.append("today")
        sel = ' aria-pressed="true"' if d in (10, 14) else ""
        days.append(
            f'<button class="{" ".join(cls)}"{sel} aria-label="November {d}, 2026">{d}</button>'
        )
    cal = "".join(days[:42])
    body = f"""<div class="o-cp"><div class="o-bc"><span class="cur">Components</span></div></div>
<main class="o-content">
  <p class="muted" style="max-width:70ch;margin-top:0">Open states of the custom controls used in the client actions. In the real modules these are
  Odoo's own OWL components (Dropdown, DateTimeInput, CheckBox) so they inherit keyboard support; the segmented control is a Kilnworks component with role="radiogroup".</p>
  <div class="comp-grid">
    <section class="panel"><div class="panel-h"><h2>Many2one / select</h2></div><div class="panel-b">
      <div class="combo"><button class="combo-btn" aria-haspopup="listbox" aria-expanded="true">Sekar Ayuningtyas {ic("chevron-down")}</button>
        <ul class="listbox" role="listbox" aria-label="Delegate to">
          <li role="option" aria-selected="false">Dimas Pratama <span class="muted">Production</span></li>
          <li role="option" aria-selected="true" class="active">Sekar Ayuningtyas <span class="muted">Sales</span></li>
          <li role="option" aria-selected="false">Bayu Santoso <span class="muted">E-commerce</span></li>
        </ul></div></div></section>
    <section class="panel"><div class="panel-h"><h2>Date range</h2><span class="count">Delegation</span></div><div class="panel-b">
      <div class="cal" role="dialog" aria-label="Choose delegation dates">
        <div class="cal-h"><button class="btn btn-ghost btn-icon btn-sm" aria-label="Previous month">{ic("chevron-left")}</button>
          November 2026<button class="btn btn-ghost btn-icon btn-sm" aria-label="Next month">{ic("chevron-right")}</button></div>
        <div class="cal-g"><span class="dow">Mo</span><span class="dow">Tu</span><span class="dow">We</span><span class="dow">Th</span>
          <span class="dow">Fr</span><span class="dow">Sa</span><span class="dow">Su</span>{cal}</div></div></div></section>
    <section class="panel"><div class="panel-h"><h2>Checkbox</h2><span class="count">API key scopes</span></div><div class="panel-b">
      <div role="group" aria-label="Scopes">
        <div class="check"><span class="box" role="checkbox" aria-checked="true" tabindex="0">{ic("check")}</span>products:read</div>
        <div class="check"><span class="box" role="checkbox" aria-checked="true" tabindex="0">{ic("check")}</span>stock:read</div>
        <div class="check"><span class="box" role="checkbox" aria-checked="false" tabindex="0"></span>orders:write</div>
      </div></div></section>
    <section class="panel"><div class="panel-h"><h2>Segmented · badges</h2></div><div class="panel-b" style="display:grid;gap:var(--s4)">
      <div class="seg" role="radiogroup" aria-label="Period"><button role="radio" aria-checked="true">7 days</button>
        <button role="radio" aria-checked="false">30 days</button><button role="radio" aria-checked="false">90 days</button></div>
      <div style="display:flex;gap:6px;flex-wrap:wrap"><span class="badge b-success">Done</span><span class="badge b-warning">Needs mapping</span>
        <span class="badge b-info">Retrying</span><span class="badge b-danger">Failed</span><span class="badge b-muted">Not started</span></div>
      <div style="display:flex;gap:8px;flex-wrap:wrap"><button class="btn btn-primary">Approve</button><button class="btn btn-secondary">Retry</button>
        <button class="btn btn-danger-ghost">Reject…</button><button class="btn btn-primary" aria-disabled="true">Confirm Order</button></div>
    </div></section>
  </div>
</main>"""
    return page("Components", body, ic)


def index():
    ic = Icons()
    items = [
        (
            "S01",
            "dashboard.html",
            "Ops Dashboard",
            "Approvals, sync failures, revenue by channel, low stock, invoices due",
        ),
        (
            "S02",
            "purchase-order.html",
            "Purchase order with tier validation",
            "OCA tiers, creator redirect, escalation, delegation, chatter",
        ),
        (
            "S05",
            "shopify.html",
            "Shopify console and sync log",
            "Webhook events, needs-mapping fix, retry, payload",
        ),
        (
            "—",
            "components.html",
            "Components",
            "Open states of select, date range, checkbox, segmented control",
        ),
    ]
    li = "".join(
        f'<li><a href="{h}"><span class="id">{i}</span><span><b>{t}</b><span class="d">{d}</span></span>{ic("chevron-right")}</a></li>'
        for i, h, t, d in items
    )
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Kilnworks on Odoo · Mockups</title><link rel="stylesheet" href="kilnworks-ds.css"></head><body>{ic.sprite()}
<main class="idx"><h1>Kilnworks on Odoo</h1>
<p>Mockups of the custom surfaces in an Odoo 18 Community portfolio build. Odoo's own chrome is kept so the modules read as native.
Kilnworks Stoneware is a synthetic company; all data is made up.</p>
<ul class="idx-list">{li}</ul></main></body></html>"""


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    for name, fn in [
        ("dashboard", dashboard),
        ("purchase-order", purchase_order),
        ("shopify", shopify),
        ("components", components),
        ("index", index),
    ]:
        (OUT / f"{name}.html").write_text(fn())
    print("built", OUT)
