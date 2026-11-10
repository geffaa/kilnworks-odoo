# Milestones — Kilnworks on Odoo

Estimasi jujur: MVP ±22–26 hari kerja paruh waktu (±5–6 minggu), lebih dari target 1–2 minggu karena isinya enam modul. Dipotong agar tetap bisa dipajang bertahap: setiap milestone menghasilkan satu modul yang bisa terbit sebagai catalog Upwork sendiri.

## M1 — Fondasi repo + data demo (±3 hari)
- [x] `docker-compose.yml` (odoo:18.0, postgres:16), `odoo.conf`, `Makefile` (`up`, `demo`, `test MOD=`, `shell`)
- [x] Submodule OCA terkunci: `server-ux`, `purchase-workflow`, `sale-workflow`, `queue` (cabang 18.0); install di DB kosong dan catat hasilnya (uji asumsi A1)
- [x] `.pre-commit-config.yaml` (ruff, pylint-odoo, prettier xml), `setup.cfg`
- [x] `addons/kw_demo`: perusahaan Kilnworks (IDR, l10n_id, Asia/Jakarta), 4 user + grup, 18 produk dengan varian glasir, 6 vendor, 14 pelanggan B2B, 40 PO/SO 90 hari (master data XML `noupdate`; transaksi dibuat `post_init_hook` dengan seed acak tetap, berjalan setelah chart Indonesia dimuat)
- [x] GitHub Actions: lint + `odoo --test-enable --stop-after-init -i kw_demo`
- [x] README kerangka (EN) + label "synthetic data"
- **Fitur:** F1, F11 (sebagian)
- **Hasil (2026-11-10):** 6 tes lulus; lint bersih; `tools/smoke.py` login 4 user di browser tanpa error console. Bug yang ketemu saat smoke: pricelist USD, jatuh tempo tanpa payment term, produk tanpa PPN — semuanya diperbaiki dan dikunci tes. Asumsi A1 terbukti: 4 modul OCA ada di 18.0. CI ditulis tapi belum jalan (repo belum di-push).
- **Verifikasi:** `make demo` dari nol berhasil; CI hijau; install ulang tidak menggandakan data.

## M2 — kw_approval (±4 hari)
- [ ] Field `kw_amount_company`, `kw_max_discount` + tes konversi USD
- [ ] Data `tier.definition` (PO > 25 jt L1→L2, PO > 100 jt L2, SO diskon > 10%) dengan `sale_tier_validation`
- [ ] Pengalihan self-approve + pesan chatter
- [ ] `kw.approval.delegation` (model, view, constraint melingkar) + perluasan pencarian reviewer + `acted_on_behalf_of_id`
- [ ] Cron SLA 24 jam (`escalated_at`), aktivitas + template email
- [ ] Menu Kilnworks Ops › Approvals (action `tier.review` milik saya + delegasi), Delegations
- [ ] Tes semua kasus TECH-SPEC §8 + tur S01→S02 (setelah M5 tur diperluas)
- **Fitur:** F2, F3
- **Verifikasi:** skenario PO Rp 48.600.000 berjalan sesuai IA alur A di demo; CI hijau.

## M3 — kw_shopify (±5 hari)
- [ ] Hari 1: buat Shopify dev store + custom app (uji A2); mock Flask GraphQL di `tools/mocks/shopify.py`
- [ ] Model store/product.map/event + view + grup
- [ ] Controller webhook (HMAC, idempotensi, 1 MB limit) + `HttpCase`
- [ ] Job `process` order → SO (`kw_channel=shopify`), status needs_mapping, `action_retry`
- [ ] Push stok debounced + mutation `inventorySetQuantities` + penanganan throttle
- [ ] Order dibatalkan → SO batal bila belum dikirim
- [ ] Client action OWL Shopify Console (S05/S06) sesuai mockup
- **Fitur:** F4
- **Verifikasi:** order dari dev store muncul sebagai SO < 1 menit; kirim webhook duplikat dengan curl → tetap satu SO; tes hijau dengan mock.

## M4 — payment_midtrans (±3 hari)
- [ ] Daftar sandbox Midtrans (uji A3); verifikasi Midtrans memang tidak ada di core 18 (A4)
- [ ] Modul provider (data `payment.provider`, field key, ikon, method VA/QRIS)
- [ ] Snap token + redirect; route return & notification; signature SHA512
- [ ] Pemetaan 6 status + tes notifikasi ganda
- **Fitur:** F5
- **Verifikasi:** invoice demo dibayar via sandbox → invoice Paid; tes hijau.

## M5 — kw_rest_api + kw_ops_dashboard + kw_reports (±6 hari)
- [ ] `kw.api.key` (hash, prefix, tampil sekali), scope, dekorator auth + rate bucket
- [ ] Endpoint products/stock/orders/partners + serializer eksplisit + spec OpenAPI statis
- [ ] Webhook keluar: endpoint, delivery, job kirim + jadwal retry, Resend
- [ ] `kw.ops.dashboard.get_data` + client action OWL S01 (segmented periode, state kosong/loading/error)
- [ ] Field HS code/karton + laporan packing list & delivery slip batch (QWeb)
- [ ] Tes TECH-SPEC §8 untuk tiga modul
- **Fitur:** F6, F7, F8, F9
- **Verifikasi:** `curl` dengan key scope kurang → 403; dashboard < 1,5 dtk; PDF packing list 3 karton benar.

## M6 — kw_firing_batch v16→v18 + rilis (±4 hari)
- [ ] Tulis modul v16 asli di DB v16 (container `odoo:16.0`), tag `kw_firing_batch-16.0`
- [ ] Commit migrasi terpisah (manifest, views, Python, OWL, `pre-migrate.py`) + `docs/MIGRATION-16-18.md`
- [ ] Uji upgrade: DB v16 berisi 30 batch → OpenUpgrade 17 → 18 → script modul; catat hasil dan kendala
- [ ] Demo online (putuskan VPS vs Tunnel), akun reviewer read-only, reset harian
- [ ] Screenshot per modul, GIF 20 dtk per catalog, video walkthrough 3–4 menit
- [ ] `docs/CASE-STUDY.md`, README final, repo publik `geffaa/kilnworks-odoo`
- [ ] Draf 6 Upwork Project Catalog (judul, deskripsi, paket, FAQ) di `docs/UPWORK-CATALOG.md`
- **Fitur:** F10, F11
- **Verifikasi:** semua tes hijau di CI; demo dibuka dari jaringan lain; catalog draf siap tempel.

## P2 (setelah MVP, ±8 hari)
- [ ] M7 `kw_coretax`: konfigurasi + perluasan `l10n_id_efaktur_coretax` core — F12
- [ ] M8 `kw_connector_base` + `kw_woocommerce` — F13
- [ ] M9 fulfillment & resi ke Shopify, portal B2B, landed cost ekspor — F14–F16

## P3
- [ ] Asisten data Groq read-only (F17), prakiraan tanah liat (F18), port Odoo 19 (F19), PWA scan batch (F20)

## Definisi selesai (product)
Repo publik bersih + README + demo online (atau alasan ditunda) + screenshot + video + `docs/CASE-STUDY.md` + draf catalog Upwork.
