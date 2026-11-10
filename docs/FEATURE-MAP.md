# Feature Map — Kilnworks on Odoo

Portfolio Senior Odoo Developer. Bisnis fiktif (synthetic): **Kilnworks Stoneware**, produsen peralatan makan stoneware di Kasongan, Bantul. Kanal: Shopify (D2C global, USD), B2B lokal ke kafe dan hotel (IDR, invoice + Midtrans), pembelian bahan baku (tanah liat, glasir, kardus ekspor). Platform: **Odoo 18 Community**.

Prinsip scope: jangan menulis ulang yang sudah ada di core atau OCA. Senior Odoo developer dinilai dari kemampuan **memperluas** modul yang ada dengan rapi, bukan menyalinnya.

## Riset: apa yang sudah ada

| Kebutuhan | Sudah ada di core / OCA / Apps Store | Celah yang diisi portfolio | Sumber |
|---|---|---|---|
| Approval berjenjang | OCA `base_tier_validation` + `purchase_tier_validation` (18.0). Butuh development untuk model baru, tier diatur di Settings > Technical | Diskon sales (`sale.order`), delegasi saat cuti, SLA + eskalasi, inbox approval terpadu | [apps.odoo.com base_tier_validation 18.0](https://apps.odoo.com/apps/modules/18.0/base_tier_validation), [purchase_tier_validation](https://apps.odoo.com/apps/modules/18.0/purchase_tier_validation) |
| Konektor Shopify | Puluhan modul pihak ketiga 18.0: webhook HMAC, push stok berkala ~15 menit, order → sale order, desain berbasis antrean | Konektor kecil yang bisa dibaca: GraphQL Admin API, webhook HMAC idempoten, `queue_job`, log sinkron yang bisa di-retry | [Elsner shopify_connector_odoo18](https://apps.odoo.com/apps/modules/18.0/shopify_connector_odoo18), [KSRO](https://apps.odoo.com/apps/modules/18.0/shopify_connector_ksro), [ET](https://apps.odoo.com/apps/modules/18.0/et_shopify_connector) |
| Payment gateway | Core 18 punya Stripe, PayPal, Razorpay, Mollie, Xendit, dll. Midtrans tidak ditemukan di dokumentasi 18.x (perlu verifikasi) | `payment_midtrans` (Snap): contoh membangun provider dari nol lewat `payment.provider` | [Odoo 18.0 Online payments](https://www.odoo.com/documentation/18.0/applications/finance/payment_providers.html) |
| REST API | Core punya XML-RPC/JSON-RPC dan API key per user; tidak ada REST bergaya resource | `/api/v1` JSON resource, API key + scope, webhook keluar bertanda tangan | Odoo external API docs (perlu verifikasi versi 18) |
| Dashboard & laporan | Core punya Spreadsheet di Enterprise saja; Community punya graph/pivot | Dashboard OWL client action, laporan QWeb ekspor (packing list, delivery slip per batch) | — |
| Migrasi | OpenUpgrade (OCA) untuk modul standar | Migrasi **modul custom** v16 → v18 dengan riwayat commit dan migration script | [OCA/OpenUpgrade](https://github.com/OCA/OpenUpgrade) |
| Lokalisasi Indonesia | `l10n_id` core (CoA, PPN 12% non-luxury dengan DPP 11/12), `l10n_id_efaktur`, dan **`l10n_id_efaktur_coretax` sudah ada di Odoo 18 core** (terverifikasi di image `odoo:18.0`, 2026-11-10) | Bukan ekspor Coretax dari nol, melainkan konfigurasi + perluasan kecil (kode produk Coretax untuk stoneware, validasi NPWP pelanggan) | image `odoo:18.0` |

## Peta fitur per fase

Modul diberi prefix `kw_` kecuali provider payment (`payment_midtrans`, mengikuti konvensi Odoo).

### MVP (P1): enam modul yang menjadi enam catalog Upwork

| ID | Fitur | Modul | Catalog Upwork |
|---|---|---|---|
| F1 | Data perusahaan demo + seed synthetic (produk, BoM ringan, pelanggan, vendor) | `kw_demo` | (pendukung semua) |
| F2 | Approval PO berjenjang di atas OCA + approval diskon sales > 10% | `kw_approval` | Custom Odoo module development |
| F3 | Delegasi approver saat cuti + SLA 24 jam dengan eskalasi | `kw_approval` | (bagian F2) |
| F4 | Konektor Shopify: impor order, push stok, mapping produk, webhook HMAC, log + retry | `kw_shopify` | Odoo ↔ Shopify integration |
| F5 | Payment provider Midtrans Snap untuk invoice B2B, notifikasi bertanda tangan | `payment_midtrans` | Custom payment gateway |
| F6 | REST API `/api/v1` (products, stock, orders, partners) + API key ber-scope | `kw_rest_api` | Odoo REST API / mobile backend |
| F7 | Webhook keluar (order.confirmed, stock.low) dengan HMAC + retry | `kw_rest_api` | (bagian F6) |
| F8 | Dashboard operasional OWL (order per kanal, approval tertunda, stok kritis, kegagalan sinkron) | `kw_ops_dashboard` | Odoo dashboards & reports |
| F9 | Laporan QWeb: packing list ekspor, delivery slip dengan batch pembakaran | `kw_reports` | (bagian F8) |
| F10 | Modul `kw_firing_batch` versi 16 dimigrasi ke 18 + migration script + catatan diff | `kw_firing_batch` | Odoo version migration |
| F11 | Infrastruktur: Docker Compose, unit test per modul, GitHub Actions, README, demo online | repo | (bukti di semua catalog) |

### P2: kedalaman yang biasa diminta klien setelah MVP

| ID | Fitur | Modul |
|---|---|---|
| F12 | Konfigurasi `l10n_id_efaktur_coretax` core + perluasan kecil (kode produk, validasi NPWP) | `kw_coretax` |
| F13 | Konektor WooCommerce memakai lapisan connector yang sama (abstraksi `kw_connector_base`) | `kw_woocommerce` |
| F14 | Sinkron fulfillment + nomor resi kembali ke Shopify | `kw_shopify` |
| F15 | Portal B2B: pelanggan kafe melihat invoice, bayar Midtrans, unduh packing list | `kw_portal_b2b` |
| F16 | Multi-currency landed cost sederhana untuk ekspor (ongkir + bea) | `kw_landed_export` |

### P3: pembeda lanjutan

| ID | Fitur | Modul |
|---|---|---|
| F17 | Asisten "tanya data" di dashboard (LLM via Groq, read-only, query ORM terbatas) | `kw_ops_assistant` |
| F18 | Prakiraan kebutuhan tanah liat dari histori order (rata-rata bergerak, bukan ML berat) | `kw_forecast` |
| F19 | Port ke Odoo 19 + catatan perubahan API | semua |
| F20 | Aplikasi mobile kecil (PWA) untuk scan batch di gudang memakai REST API | repo terpisah |

## Yang sengaja tidak dibuat
- Payment Stripe (sudah ada di core).
- Engine approval dari nol (OCA sudah matang; menulis ulang adalah sinyal junior).
- Fitur Enterprise (Studio, Approvals app, Spreadsheet). Semua berjalan di Community.
