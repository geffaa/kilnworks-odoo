# PRD — Kilnworks on Odoo

Status: draft · Tanggal: 2026-11-10 · Sumber: riset pasar Upwork / Jobstreet / Glints / Kalibrr (chat 2026-11-09)

## 1. Ringkasan
Portfolio Senior Odoo Developer berupa satu instalasi **Odoo 18 Community** untuk bisnis fiktif *Kilnworks Stoneware* (Kasongan, Bantul; synthetic), berisi enam modul custom yang masing-masing menjawab satu jenis pekerjaan Odoo yang paling sering dicari di Upwork: modul custom/approval, integrasi Shopify, payment gateway, REST API, dashboard/laporan, dan migrasi versi. Repo publik, demo online, tes otomatis, dan video membuat setiap modul bisa dipajang sebagai satu Upwork Project Catalog.

## 2. Masalah
- User (freelancer) belum punya bukti kerja Odoo, sementara lowongan senior di Indonesia meminta 4–5+ tahun dan ≥5 implementasi ([Kalibrr KAITECH](https://www.kalibrr.id/id-ID/c/pt-kai-teknologi-aplikatif-kaitech/jobs/264913/odoo-senior-developer)), dan klien Upwork meminta portfolio proyek Odoo ([Upwork job](https://www.upwork.com/freelance-jobs/apply/Odoo-ERP-Developer-Certified-Service-Industry-Focus_~021982645574611858610)).
- Demo Odoo yang umum di portfolio freelancer adalah screenshot konfigurasi standar: tidak menunjukkan kode, tes, atau keputusan teknis.
- Klien Upwork paling sering meminta customization + integrasi API (payment, e-commerce, portal pajak) dan migrasi versi ([Upwork Senior Odoo](https://www.upwork.com/freelance-jobs/apply/Senior-Odoo-ERP-Consultant-Developer-Remote_~022067701916205256359/), [HMRC VAT Odoo 18](https://www.upwork.com/freelance-jobs/apply/Odoo-Enterprise-Developer-Needed-HMRC-VAT-Integration_~022072242815817555384/)).

## 3. Tujuan & metrik sukses
- Enam modul berjalan di Odoo 18 Community, terpasang bersih dari database kosong (`-i kw_demo`).
- Setiap modul punya tes Odoo (`TransactionCase`/`HttpCase`) yang lulus di GitHub Actions.
- Enam Upwork Project Catalog terbit dalam 3 minggu setelah M6; target: ≥3 undangan/balasan proposal Odoo dalam 30 hari setelah terbit (sinyal pasar, bukan janji).
- Demo online bisa dibuka reviewer dengan akun read-only.
- **Non-goal:** menjadi produk yang dijual di Odoo Apps Store; mendukung Enterprise; mendukung multi-company kompleks.

## 4. Persona & konteks

**Reviewer (klien Upwork / tech lead perekrut)**: membuka catalog atau repo 3–5 menit di laptop. Ingin melihat: apakah modul terasa native, kode mengikuti pedoman OCA, ada tes, tahu batas core vs OCA. Frustrasi: demo yang hanya screenshot, kode yang meng-override method core tanpa `super()`.

**Pengguna fiktif di dalam demo (synthetic)**: Ratna (owner, approver L2, sering di lapangan, cek dari ponsel), Dimas (kepala produksi, buat PO bahan baku mingguan), Sekar (sales B2B, buat quotation harian), Bayu (ops e-commerce, memantau sinkron Shopify tiap pagi). Mereka membentuk alur yang dinilai reviewer.

**User sendiri**: harus bisa menjelaskan setiap modul dalam panggilan klien dan menjadikannya titik awal pekerjaan nyata.

## 5. Asumsi
| # | Asumsi | Risiko jika salah |
|---|---|---|
| A1 | OCA `base_tier_validation`, `purchase_tier_validation`, `sale_tier_validation`, `queue_job` tersedia untuk 18.0 | Terverifikasi M1 (2026-11-10) |
| A2 | Shopify Partner development store gratis bisa dipakai untuk demo dan GraphQL Admin API | Sedang: fallback ke mock server Shopify (tetap dibuat untuk CI) |
| A3 | Midtrans sandbox gratis dan Snap API tersedia untuk akun baru | Sedang: fallback mock notifikasi |
| A4 | Midtrans tidak ada di core Odoo 18 | Rendah: kalau ada, ganti ke provider lain yang tidak ada di core |
| A5 | Demo online cukup di VPS kecil (2 vCPU / 4 GB) | Sedang: biaya bulanan perlu verifikasi |
| A6 | User belum punya pengalaman Odoo produksi; katalog dan README menyebut ini sebagai *demo build* | **Tinggi** bila dilanggar: klaim palsu merusak reputasi Upwork |
| A7 | ~~Format Coretax XML perlu dicari~~ Terjawab: Odoo 18 core sudah punya `l10n_id_efaktur_coretax` | Rendah |

## 6. Scope
- **MVP:** F1–F11 (lihat [FEATURE-MAP.md](FEATURE-MAP.md)).
- **Nanti:** F12–F16 (P2), F17–F20 (P3).
- **Bukan tujuan:** payment Stripe (core sudah ada), engine approval dari nol, fitur Enterprise, data pelanggan nyata.

## 7. User stories
- **F2** Sebagai Dimas, saya ingin PO > Rp 25 jt otomatis meminta persetujuan bertingkat, supaya pembelian besar tidak lolos tanpa owner.
- **F2** Sebagai Sekar, saya ingin quotation dengan diskon > 10% meminta persetujuan owner, supaya margin terjaga tanpa menunggu chat.
- **F3** Sebagai Ratna, saya ingin mendelegasikan approval selama cuti, supaya PO tidak macet.
- **F3** Sebagai Ratna, saya ingin diingatkan jika approval tertahan > 24 jam.
- **F4** Sebagai Bayu, saya ingin order Shopify masuk sebagai sale order dalam < 1 menit, dan stok Odoo terdorong ke Shopify, supaya tidak oversell.
- **F4** Sebagai Bayu, saya ingin melihat event yang gagal dan mencoba ulang satu per satu.
- **F5** Sebagai pelanggan B2B, saya ingin membayar invoice lewat VA/QRIS dari link email.
- **F6/F7** Sebagai developer aplikasi gudang, saya ingin API JSON dengan API key ber-scope dan webhook bertanda tangan.
- **F8** Sebagai Ratna, saya ingin satu layar berisi order per kanal, approval tertunda, stok kritis, dan kegagalan sinkron.
- **F9** Sebagai Bayu, saya ingin mencetak packing list ekspor yang menyebut batch pembakaran.
- **F10** Sebagai reviewer, saya ingin melihat bagaimana modul v16 dimigrasi ke v18 lewat commit dan catatan diff.

## 8. Fitur MVP secara detail

### F1 — Data demo (`kw_demo`)
Seed synthetic: 1 perusahaan (IDR, l10n_id), 18 produk (mug, piring, mangkuk, set; varian glasir), 6 vendor (tanah liat, glasir, kardus), 14 pelanggan B2B, 4 user demo dengan grup sesuai peran, 40 PO/SO historis 90 hari.
- Ketika database kosong di-install dengan `-i kw_demo`, maka semua modul MVP ikut terpasang dan dashboard menampilkan angka tanpa error.
- Ketika di-install ulang, maka tidak ada record ganda (data XML ber-`noupdate`).
- Layar: semua.

### F2 — Approval PO & diskon (`kw_approval`)
Memakai OCA `tier.definition`. Modul menambahkan: definisi data (PO > Rp 25 jt → L1 lalu L2; PO > Rp 100 jt → L2 wajib; SO diskon baris > 10% → owner), larangan menyetujui dokumen buatan sendiri (dialihkan ke reviewer tier berikutnya), dan tombol aksi di Inbox.
- Ketika PO Rp 48.600.000 di-*Request Validation*, maka dibuat 2 `tier.review` berurutan dan PO tidak bisa di-confirm sebelum keduanya approved.
- Ketika pembuat PO adalah reviewer L1, maka review L1 dialihkan ke owner dan chatter mencatat alasannya.
- Ketika baris SO diskon 15%, maka tombol Confirm terkunci sampai owner approve.
- Ketika reviewer menolak dengan komentar, maka dokumen kembali ke draft dan komentar tampil di chatter.
- Edge: total PO berubah setelah approval → validasi direset; mata uang USD dikonversi ke IDR sebelum dibandingkan.
- Layar: S02, S03, S04.

### F3 — Delegasi & SLA
Model `kw.approval.delegation` (dari, ke, tanggal mulai/akhir). Cron per jam mengecek review `pending` > 24 jam kerja.
- Ketika Ratna punya delegasi aktif ke Sekar, maka review baru untuk Ratna juga dapat diproses Sekar dan tercatat "atas nama Ratna".
- Ketika review pending > 24 jam, maka dibuat aktivitas ke approver dan email ke owner, sekali per review (tidak berulang tiap jam).
- Edge: delegasi melingkar (A→B, B→A) ditolak oleh constraint; delegasi ke diri sendiri ditolak.
- Layar: S04, S10.

### F4 — Konektor Shopify (`kw_shopify`)
`kw.shopify.store` (domain, token terenkripsi di `ir.config_parameter`/field `groups`-restricted, webhook secret), `kw.shopify.product.map`, `kw.shopify.event`. Webhook controller `/kw_shopify/webhook/<store_id>`; job `queue_job` memproses. Push stok: hook `stock.quant` → job debounced 60 detik per produk.
- Ketika webhook `orders/create` dengan HMAC valid diterima, maka respon 200 dalam < 1 detik dan sale order tercipta oleh job.
- Ketika webhook yang sama dikirim ulang (ID sama), maka tidak ada sale order ganda.
- Ketika HMAC tidak valid, maka respon 401 dan event tidak disimpan.
- Ketika SKU tidak terpetakan, maka event berstatus `needs_mapping`, order tidak dibuat, dan tombol Retry aktif setelah mapping dibuat.
- Ketika stok on-hand produk terpetakan berubah, maka kuantitas tersedia terkirim ke Shopify dalam ≤ 2 menit (satu panggilan GraphQL untuk banyak perubahan).
- Edge: rate limit Shopify (HTTP 429 / throttle GraphQL) → job retry dengan backoff; order dibatalkan di Shopify → SO dibatalkan bila belum dikirim.
- Layar: S05, S06.

### F5 — Midtrans (`payment_midtrans`)
Provider baru: `code = 'midtrans'`, Server Key/Client Key, mode sandbox. Redirect ke Snap, route notifikasi `/payment/midtrans/notification`.
- Ketika pelanggan membuka link invoice dan memilih Midtrans, maka diarahkan ke Snap dengan `order_id` = referensi transaksi Odoo dan nominal IDR tanpa desimal.
- Ketika notifikasi `settlement` dengan `signature_key` = SHA512(order_id+status_code+gross_amount+server_key) diterima, maka transaksi `done` dan invoice paid.
- Ketika signature salah, maka 403 dan transaksi tidak berubah.
- Ketika notifikasi sama diterima dua kali, maka hasilnya tetap satu pembayaran.
- Edge: status `pending`, `expire`, `deny`, `cancel` dipetakan ke state transaksi Odoo.
- Layar: S07.

### F6 — REST API (`kw_rest_api`)
Route JSON `/api/v1/...`, auth header `Authorization: Bearer <key>`; `kw.api.key` menyimpan hash (bukan plaintext), scope, user teknis, kedaluwarsa. Pagination cursor, error format `{error:{code,message}}`, rate limit sederhana per key (60 req/menit, in-DB bucket).
- Ketika key dengan scope `stock:read` memanggil `GET /api/v1/stock`, maka 200 dengan stok per produk dan lokasi.
- Ketika key yang sama memanggil `POST /api/v1/orders`, maka 403 `insufficient_scope`.
- Ketika key dicabut, maka panggilan berikutnya 401.
- Ketika melebihi 60 req/menit, maka 429 dengan header `Retry-After`.
- Edge: record yang tidak boleh dibaca user teknis (record rules) tidak bocor.
- Layar: S09 (konfigurasi), dokumentasi OpenAPI statis di `/api/v1/docs`.

### F7 — Webhook keluar
`kw.webhook.endpoint` (URL, event, secret), `kw.webhook.delivery` (payload, status, percobaan). Header `X-Kw-Signature: sha256=<hmac>`.
- Ketika SO di-confirm, maka delivery `order.confirmed` dibuat dan dikirim oleh job.
- Ketika endpoint gagal (non-2xx/timeout 10 dtk), maka retry pada 1, 5, 30 menit, 2, 6 jam lalu `failed`.
- Ketika admin klik Resend, maka payload yang sama dikirim dengan ID delivery yang sama.
- Layar: S09.

### F8 — Dashboard Ops (`kw_ops_dashboard`)
OWL client action, data dari satu RPC `kw.ops.dashboard.get_data(period)`. Isi: omzet & order per kanal (Shopify/B2B), approval tertunda (dengan umur), 8 produk di bawah min stok, event sinkron gagal 24 jam, invoice jatuh tempo.
- Ketika periode diganti (7/30/90 hari), maka angka diperbarui tanpa reload halaman.
- Ketika klik baris approval, maka membuka record terkait di form standar dengan breadcrumb utuh.
- Ketika user tanpa grup Ops membuka menu, maka menu tidak terlihat.
- Edge: tanpa data → tiap blok menampilkan keadaan kosong yang menjelaskan cara mengisinya.
- Layar: S01.

### F9 — Laporan QWeb (`kw_reports`)
Packing list ekspor (per karton: isi, berat bersih/kotor, dimensi, HS code), delivery slip dengan batch pembakaran per lot.
- Ketika picking keluar dengan 3 karton dicetak, maka PDF memuat 3 blok karton dan total berat cocok dengan jumlah baris.
- Ketika produk tidak punya HS code, maka tombol cetak memberi peringatan sebelum PDF dibuat.
- Layar: S08.

### F10 — Migrasi `kw_firing_batch` v16 → v18
Repo memuat tag `kw_firing_batch-16.0` (modul asli, views `attrs`, `tree`, widget legacy) lalu commit migrasi: `attrs` → ekspresi `invisible/readonly`, `tree` → `list`, `name_get` → `_compute_display_name`, aset legacy → OWL, `migrations/18.0.1.0.0/pre-migrate.py` yang mengganti nama kolom `kiln_temp` → `peak_temp_c`.
- Ketika database v16 berisi 30 batch di-upgrade (OpenUpgrade untuk core + script modul), maka 30 batch utuh dengan suhu di kolom baru.
- Ketika tes modul dijalankan di v18, maka semua lulus.
- Layar: S11 (form batch). Dokumen: `docs/MIGRATION-16-18.md`.

### F11 — Infrastruktur repo
Docker Compose (odoo:18.0 + postgres:16), `addons/` (custom) + `oca/` (git submodule terkunci), pre-commit (ruff, pylint-odoo, prettier untuk XML/JS), GitHub Actions menjalankan `odoo --test-enable -i <modul> --stop-after-init`, README bahasa Inggris dengan diagram, demo online.
- Ketika PR dibuka, maka CI menjalankan lint + tes semua modul dan gagal bila ada tes merah.
- Ketika reviewer menjalankan `docker compose up` lalu `make demo`, maka Odoo siap di `localhost:8069` dengan data demo dalam < 5 menit di laptop biasa (perlu verifikasi pada mesin user).

## 9. User flow
Alur utama (reviewer menonton video atau mengklik demo):
1. Login sebagai Ratna → **S01 Dashboard**: 3 approval tertunda, 2 event Shopify gagal.
2. Klik approval PO tanah liat → **S02 PO form** dengan panel tier → Approve.
3. Kembali → **S03 Inbox Approvals** → setujui diskon quotation kafe.
4. Klik blok sinkron gagal → **S05 Shopify Console** → **S06 Sync Log** event `needs_mapping` → buat mapping → Retry → sale order tercipta.
5. Buka picking → cetak **S08 Packing list**.
6. Buka invoice B2B → link pembayaran → **S07 Midtrans checkout** (sandbox) → invoice paid.
7. **S09 API Keys & Webhooks** → tampilkan delivery webhook `order.confirmed`.
8. **S11 Firing Batch** → tunjukkan riwayat migrasi di repo.

Alur sekunder: Dimas buat PO (S02) → Request Validation; Ratna atur delegasi (S10) sebelum cuti; Sekar buat quotation diskon (S04).

## 10. Kebutuhan non-fungsional
- **Keamanan:** token Shopify, Server Key Midtrans, dan secret webhook hanya terbaca grup `base.group_system`; API key disimpan sebagai hash; semua webhook masuk diverifikasi tanda tangan sebelum disimpan; tidak ada `sudo()` tanpa komentar alasan.
- **Kualitas kode:** pedoman OCA (manifest, struktur folder, i18n `.pot`), pylint-odoo bersih, tidak meng-override method core tanpa `super()`.
- **Performa:** dashboard < 1,5 dtk pada data demo; webhook Shopify menjawab < 1 dtk (proses berat di job).
- **Aksesibilitas:** komponen OWL custom memakai elemen semantik Odoo, fokus keyboard terlihat, kontras AA.
- **Lokalisasi:** IDR untuk B2B, USD untuk Shopify, zona waktu Asia/Jakarta; string bisa diterjemahkan (`_()`/`_t`), terjemahan `id.po` untuk modul custom.
- **Keandalan:** semua handler webhook idempoten; job retry dengan backoff; backup DB demo harian di VPS.

## 11. Risiko & pertanyaan terbuka
| Risiko | Uji termurah lebih dulu |
|---|---|
| OCA 18.0 belum lengkap untuk `sale_tier_validation` atau `queue_job` | M1: tambahkan submodule, install di DB kosong, jalankan tes OCA |
| Shopify dev store/token butuh verifikasi Partner | M3 hari 1: buat dev store; kalau terhambat, mock server dulu |
| Midtrans sandbox butuh verifikasi bisnis | M4 hari 1: daftar sandbox; mock notifikasi sebagai cadangan |
| Lingkup terlalu besar untuk paruh waktu | Milestone mandiri; catalog bisa terbit per modul setelah milestone-nya selesai |

Pertanyaan terbuka: VPS demo (Hetzner/DO/lokal + Cloudflare Tunnel) diputuskan di M6.

## 12. Distribusi & monetisasi
- **Repo:** github.com/geffaa/kilnworks-odoo (publik), README per modul.
- **Upwork Project Catalog (6):** "Custom Odoo 18 module with multi-level approvals", "Odoo ↔ Shopify integration (orders, stock, webhooks)", "Custom payment gateway for Odoo (Midtrans/any REST gateway)", "REST API & webhooks for Odoo", "Odoo dashboards and QWeb reports", "Odoo custom module migration (v14–v17 → v18)". Tiap catalog: GIF 20 dtk, tautan ke folder modul, paket Basic/Standard/Premium.
- **Kejujuran:** semua materi menyebut "demo build on a synthetic company"; tidak ada klaim klien.
- **Pasar lokal:** CV/Glints/Jobstreet menyorot Python, ORM, OWL, PostgreSQL, tes, dan pemahaman alur procure-to-pay & order-to-cash.
