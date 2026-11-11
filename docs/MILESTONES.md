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
- [x] Field `kw_amount_company`, `kw_max_discount` + tes konversi USD
- [x] Data `tier.definition` (PO > 25 jt L1→L2, PO > 100 jt L2, SO diskon > 10%) dengan `sale_tier_validation`
- [x] Pengalihan self-approve + pesan chatter
- [x] `kw.approval.delegation` (model, view, constraint melingkar) + perluasan pencarian reviewer + `acted_on_behalf_of_id`
- [x] Cron SLA 24 jam (`escalated_at`), aktivitas + template email
- [x] Menu Kilnworks Ops › Approvals (action `tier.review` milik saya + delegasi), Delegations
- [x] Tes semua kasus TECH-SPEC §8 (tur S01→S02 dipindah ke M5 bersama dashboard)
- **Fitur:** F2, F3
- **Hasil (2026-11-10):** 22 tes `kw_approval` + 2 `kw_ops` + 7 `kw_demo` lulus. Modul fondasi `kw_ops` ditambahkan (app + grup peran) agar aturan tier tidak bergantung pada user demo. E2E browser: Sekar (delegate) memvalidasi PO Rp 48,6 jt → tercatat atas nama Ratna. Temuan: (1) OCA memberi nomor tier dari `sequence` definisi **terbesar**, jadi definisi kepala produksi = 20, owner = 10; (2) OCA tidak punya bypass untuk perubahan state, jadi riwayat demo ditulis dengan aturan dinonaktifkan sementara; (3) OCA mengunci baris saat validasi berjalan, sehingga logika "reset bila total berubah" tidak diperlukan; (4) cap waktu pending tertimpa oleh tulisan ulang status oleh OCA, diperbaiki + tes regresi. Aturan PO diubah ke 10 jt / 25 jt (aturan 100 jt lama tumpang tindih). Komentar wajib saat reject belum diaktifkan (`has_comment`).
- **Verifikasi:** skenario PO Rp 48.600.000 berjalan sesuai IA alur A di demo; CI hijau.

## M3 — kw_shopify (±5 hari)
- [ ] Hari 1: buat Shopify dev store + custom app (uji A2) — **ditunda atas permintaan user; semua berjalan di mock**
- [x] Mock GraphQL (stdlib, service Docker `shopify-mock`) di `tools/mocks/shopify_mock.py` + pengirim webhook bertanda tangan `tools/mocks/send_order.py`
- [x] Model store/product.map/event + view + grup
- [x] Controller webhook (HMAC, idempotensi, 1 MB limit) + `HttpCase`
- [x] Job `process` order → SO (`kw_channel=shopify`), status needs_mapping, `action_retry`
- [x] Push stok debounced + mutation `inventorySetQuantities` + penanganan throttle
- [x] Order dibatalkan → SO batal bila belum dikirim
- [x] Client action OWL Shopify Console (S05/S06) sesuai mockup
- **Fitur:** F4
- **Hasil (2026-11-10):** 18 tes `kw_shopify` (webhook lewat HTTP sungguhan: HMAC valid/salah, redelivery, 404, 413; order → SO USD tanpa PPN; order ganda; pelanggan dicocokkan email; SKU hilang → needs_mapping → mapping → retry; batal sebelum/sesudah kirim; push stok: debounce jadi 1 job, payload GraphQL, 429/THROTTLED retryable, userErrors). E2E dengan job runner asli: `send_order.py --repeat` → satu event + `duplicate_count=1`, SO tercipta; push stok 18 item diterima mock. Konsol OWL lulus di 1440 dan 390 px tanpa error console. Demo berisi 40 order Shopify (30 hari) termasuk #KW1043 (SKU KW-MUG-350-SAGE belum dipetakan) dan pembatalan #KW1031 setelah dikirim. Belum: uji dengan dev store Shopify asli (A2), versi API `2025-10` dan argumen `ignoreCompareQuantity` perlu verifikasi terhadap dokumentasi Shopify saat dev store tersedia; ongkir dan pajak Shopify belum diimpor (P2).
- **Verifikasi:** order dari dev store muncul sebagai SO < 1 menit; kirim webhook duplikat dengan curl → tetap satu SO; tes hijau dengan mock.

## M4 — payment_midtrans (±3 hari)
- [ ] Daftar sandbox Midtrans (uji A3) — **ditunda; berjalan di mock `tools/mocks/midtrans_mock.py`**
- [x] Verifikasi Midtrans tidak ada di core 18 (A4): terbukti, image `odoo:18.0` hanya punya adyen, aps, asiapay, authorize, buckaroo, custom, demo, flutterwave, mercado_pago, mollie, nuvei, paypal, razorpay, stripe, worldline, xendit
- [x] Modul provider (data `payment.provider`, field key, ikon, method VA/QRIS)
- [x] Snap token + redirect; route return & notification; signature SHA512
- [x] Pemetaan 6 status + tes notifikasi ganda
- **Fitur:** F5
- **Hasil (2026-11-10):** 14 tes `payment_midtrans` (request Snap: URL, Basic auth, `gross_amount` integer, `enabled_payments` sesuai metode; referensi aman untuk Midtrans; endpoint produksi saat `enabled`; pesan error Snap; pemetaan status; kartu `capture` + fraud review; nomor VA; sinkron dari Status API; notifikasi via HTTP: settlement, ganda, signature salah 403, jumlah tidak cocok 403, order tak dikenal 403) + tes demo bahwa transaksi selesai melunasi invoice. E2E browser `tools/e2e_payment.py`: portal invoice → BCA VA → halaman mock → notifikasi bertanda tangan → invoice `paid`, tanpa error console. Temuan: (1) halaman return memanggil Status API karena notifikasi tidak menjangkau localhost dan query string tidak bisa dipercaya; (2) bila `payment_midtrans` terpasang sebelum `account_payment`, payment method akuntansi tidak terbuat — demo memanggil ulang `_setup_provider`; (3) Odoo 18 butuh akun Outstanding Receipts pada payment method line agar pembayaran berjurnal dan bisa dicocokkan ke invoice. Belum: uji sandbox Midtrans asli; karakter yang diizinkan untuk `order_id` perlu verifikasi; refund ditangani manual (P2).
- **Verifikasi:** invoice demo dibayar via sandbox → invoice Paid; tes hijau.

## M5 — kw_rest_api + kw_ops_dashboard + kw_reports (±6 hari)
- [x] `kw.api.key` (hash, prefix, tampil sekali), scope, dekorator auth + rate bucket
- [x] Endpoint products/stock/orders/partners + serializer eksplisit + spec OpenAPI statis
- [x] Webhook keluar: endpoint, delivery, job kirim + jadwal retry, Resend
- [x] `kw.ops.dashboard.get_data` + client action OWL S01 (segmented periode, state kosong/loading/error)
- [x] Field HS code/karton + laporan packing list & delivery slip batch (QWeb)
- [x] Tes TECH-SPEC §8 untuk tiga modul
- **Fitur:** F6, F7, F8, F9
- **Hasil (2026-11-10):** 17 tes `kw_rest_api` (hash-only key, rotasi, revoke/expired, scope, rate limit 61st → 429, quotation via POST sebagai user key, record rule mencegah kebocoran, pagination cursor, OpenAPI; webhook: signature HMAC, jadwal retry 1/5/30 mnt/2/6 jam lalu `failed`, timeout, resend dengan id sama, `stock.low` hanya saat melewati batas), 4 tes `kw_reports` (karton per units-per-carton, total, blokir tanpa HS code, render), 4 tes `kw_ops_dashboard`, dan **tour browser S01→S02 sungguhan** (image kini membawa Chromium headless dari Playwright karena paket chromium di Ubuntu hanya stub snap; sebelumnya tour diam-diam di-skip). Live: `curl` dengan key demo, 403/401, order Shopify → webhook `order.confirmed` bertanda tangan diterima mock (200). Dashboard 1440/390 tanpa error/overflow. Riwayat demo diratakan ke 60 hari agar perbandingan periode masuk akal. Perubahan desain: webhook gagal tidak melempar `RetryableJobError` (rollback akan menghapus catatan percobaan); job berikutnya dijadwalkan eksplisit. Delivery slip per batch pembakaran dipindah ke M6 bersama `kw_firing_batch`. CI kini menjalankan tes lewat image yang sama dan menilai dari baris hasil Odoo.
- **Verifikasi:** `curl` dengan key scope kurang → 403; dashboard < 1,5 dtk; PDF packing list 3 karton benar.

## M6 — kw_firing_batch v16→v18 + rilis (±4 hari)
- [x] Tulis modul v16 asli di DB v16 (container `odoo:16.0`), tag `kw_firing_batch-16.0`
- [x] Commit migrasi terpisah (manifest, views, Python, OWL, `pre-migrate.py`) + `docs/MIGRATION-16-18.md`
- [ ] Uji upgrade: DB v16 berisi 30 batch → OpenUpgrade 17 → 18 → script modul; catat hasil dan kendala
- [ ] Demo online (putuskan VPS vs Tunnel), akun reviewer read-only, reset harian
- [x] Screenshot per modul, GIF per catalog, video walkthrough (2½ menit, teks Inggris; direkam lokal)
- [ ] `docs/CASE-STUDY.md`, README final, repo publik `geffaa/kilnworks-odoo`
- [x] Draf 6 Upwork Project Catalog (judul, deskripsi, paket, FAQ) di `docs/UPWORK-CATALOG.md`
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
