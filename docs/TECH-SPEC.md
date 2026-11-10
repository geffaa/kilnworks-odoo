# Tech Spec — Kilnworks on Odoo

## 1. Arsitektur

```
             Shopify (dev store)             Midtrans Snap (sandbox)        Aplikasi gudang / klien API
               │  webhooks (HMAC)  ▲ GraphQL      │ notif (SHA512)  ▲ redirect     │ Bearer key      ▲ webhook (HMAC)
               ▼                   │              ▼                 │               ▼                 │
┌──────────────────────────── Odoo 18 Community (odoo:18.0 container) ─────────────────────────────────────┐
│ controllers: /kw_shopify/webhook/<id>   /payment/midtrans/*   /api/v1/*                                  │
│ models: kw_approval · kw_shopify · payment_midtrans · kw_rest_api · kw_ops_dashboard · kw_reports ·      │
│         kw_firing_batch · kw_demo                                                                        │
│ OCA: base_tier_validation · purchase_tier_validation · sale_tier_validation · queue_job                  │
│ queue_job runner (channel root.kw_shopify, root.kw_webhook)        cron: SLA approval, retry webhook     │
└──────────────────────────────────────────────┬───────────────────────────────────────────────────────────┘
                                               ▼
                                   PostgreSQL 16 (container)
```

Alasan stack: pasar meminta Odoo 17/18 + Python + PostgreSQL + OWL; Community 18 gratis dan cukup untuk semua fitur MVP, dan memakai OCA menunjukkan kebiasaan senior (reuse modul komunitas).

## 2. Stack & paket
| Bagian | Pilihan | Fungsi |
|---|---|---|
| Platform | Odoo 18.0 Community (image resmi `odoo:18.0`) | ERP inti |
| Database | PostgreSQL 16 | |
| Frontend | OWL 2 (bawaan Odoo 18), SCSS Odoo, QWeb | Client action, widget, laporan |
| Antrean | OCA `queue_job` (18.0) | Webhook Shopify, push stok, webhook keluar |
| Approval | OCA `base_tier_validation`, `purchase_tier_validation`, `sale_tier_validation` | Engine tier |
| HTTP client | `requests` (sudah ada di image) | Shopify GraphQL, webhook keluar |
| Lint | pre-commit: ruff, pylint-odoo, prettier (+ plugin xml) | Gaya OCA |
| CI | GitHub Actions + service postgres | Lint + tes per modul |
| Mock | Flask kecil di `tools/mocks/` (Shopify GraphQL + Midtrans notif) | CI dan demo offline |

OCA ditambahkan sebagai git submodule terkunci ke commit tertentu di `oca/server-ux`, `oca/purchase-workflow`, `oca/sale-workflow`, `oca/queue`.

## 3. Data model
Hanya model baru/tambahan. Kolom sensitif ditandai 🔒 (`groups="base.group_system"`, tidak pernah dikirim ke klien JS).

**kw_approval**
- `kw.approval.delegation`: `delegator_id` (res.users), `delegate_id` (res.users), `date_from`, `date_to` (date), `active`, `reason`. Constraint: `delegator_id != delegate_id`; tidak ada delegasi aktif balik yang overlap (Python constraint). Fitur F3.
- Perluasan `tier.review`: `escalated_at` (datetime), `acted_on_behalf_of_id` (res.users). Fitur F2, F3.
- Perluasan `purchase.order` / `sale.order`: `kw_amount_company` (monetary terhitung, IDR) untuk perbandingan tier lintas mata uang; `kw_max_discount` (float, compute dari baris). Fitur F2.
- Data `tier.definition`: 3 rule (PO > 10 jt kepala produksi, PO > 25 jt owner, SO diskon > 10% owner).

**kw_shopify**
- `kw.shopify.store`: `name`, `shop_domain` (unik), `api_version` (char, default `2025-10`, perlu verifikasi versi aktif), 🔒`access_token`, 🔒`webhook_secret`, `location_gid`, `warehouse_id`, `pricelist_id` (USD), `active`, `last_stock_push_at`. F4.
- `kw.shopify.product.map`: `store_id`, `product_id`, `shopify_variant_gid`, `shopify_inventory_item_gid`, `sku`. Unik (`store_id`, `shopify_variant_gid`) dan (`store_id`, `product_id`). F4.
- `kw.shopify.event`: `store_id`, `webhook_id` (unik per store, idempotensi), `topic`, `payload` (json), `state` (received/queued/done/needs_mapping/failed), `error`, `sale_order_id`, `attempts`, `received_at`. Indeks (`state`, `received_at`). F4, F8.
- Perluasan `sale.order`: `kw_channel` (selection: b2b/shopify), `kw_shopify_order_gid`. F4, F8.

**payment_midtrans**
- Perluasan `payment.provider`: `code` + selection `midtrans`, 🔒`midtrans_server_key`, `midtrans_client_key`, `midtrans_merchant_id`. F5.
- Perluasan `payment.transaction`: `midtrans_snap_token`, `midtrans_transaction_status`, `midtrans_payment_type`. F5.

**kw_rest_api**
- `kw.api.key`: `name`, `user_id` (user teknis), `key_prefix` (8 char, ditampilkan), 🔒`key_hash` (sha256), `scope_ids` (m2m `kw.api.scope`), `expires_at`, `last_used_at`, `active`. F6.
- `kw.api.scope`: `code` (unik: `products:read`, `stock:read`, `orders:read`, `orders:write`, `partners:read`). F6.
- `kw.api.rate.bucket`: `key_id`, `window_start` (datetime menit), `count`. Unik (`key_id`, `window_start`); dibersihkan cron harian. F6.
- `kw.webhook.endpoint`: `name`, `url`, `event_codes` (char list), 🔒`secret`, `active`. F7.
- `kw.webhook.delivery`: `endpoint_id`, `event_code`, `delivery_uid` (uuid, unik), `payload` (json), `state` (pending/sent/retrying/failed), `attempts`, `next_attempt_at`, `last_status_code`, `last_error`. F7.

**kw_firing_batch**
- `kw.firing.batch`: `name` (sequence FB/2026/0001), `kiln_id`, `fired_on` (date), `peak_temp_c` (integer; v16: `kiln_temp`), `duration_h`, `state` (planned/firing/cooled/rejected), `lot_ids` (o2m `stock.lot`), `defect_rate` (float). F10, F9.
- `kw.kiln`: `name`, `type` (gas/electric), `capacity_pcs`. F10.
- Perluasan `stock.lot`: `firing_batch_id`. F9, F10.

**kw_reports**
- Perluasan `product.template`: `kw_hs_code` (char, mis. 6912.00), `kw_carton_qty`, `kw_carton_weight_kg`. F9.
- Perluasan `stock.package` (core): dipakai sebagai karton; tidak ada model baru. F9.

**kw_ops_dashboard**: tanpa tabel; model abstrak `kw.ops.dashboard` dengan method `get_data`. F8.

## 4. API / route
| Method | Path | Akses | Fitur |
|---|---|---|---|
| POST | `/kw_shopify/webhook/<int:store_id>` | publik, HMAC `X-Shopify-Hmac-Sha256` (base64 HMAC-SHA256 body mentah) | F4 |
| GET | `/payment/midtrans/return` | publik | F5 |
| POST | `/payment/midtrans/notification` | publik, verifikasi `signature_key` | F5 |
| GET | `/api/v1/products` | key + `products:read` | F6 |
| GET | `/api/v1/stock` | key + `stock:read` | F6 |
| GET | `/api/v1/orders`, `/api/v1/orders/<id>` | key + `orders:read` | F6 |
| POST | `/api/v1/orders` | key + `orders:write` | F6 |
| GET | `/api/v1/partners` | key + `partners:read` | F6 |
| GET | `/api/v1/docs` | publik (spec OpenAPI statis) | F6 |
| RPC | `kw.ops.dashboard.get_data` | grup `kw_ops.group_user` | F8 |
| RPC | `kw.shopify.event.action_retry` | grup `kw_ops.group_manager` | F4 |

Idempotensi: Shopify per `X-Shopify-Webhook-Id` (unik di DB, `INSERT ... ON CONFLICT DO NOTHING` lewat SQL atau tangkap `UniqueViolation` di savepoint); Midtrans per `transaction_id` + status (transisi state Odoo sudah idempoten jika state sama); webhook keluar per `delivery_uid` dikirim sebagai header `X-Kw-Delivery`.

## 5. Logika inti

**Tier lintas mata uang dan larangan self-approve (`kw_approval`).** `tier.definition` OCA mengevaluasi domain/ekspresi Python. Kami mendefinisikan rule pada `kw_amount_company` (amount_total dikonversi ke mata uang perusahaan pada `date_order`) agar PO USD tidak lolos ambang. Override `_validate_tier` / pembuatan review: jika reviewer = `create_uid`, review dialihkan ke reviewer tier berikutnya dan pesan chatter ditulis. Delegasi: perluas pencarian reviewer (`_get_reviewers` / `reviewer_ids`) agar menyertakan delegate aktif; saat delegate menyetujui, `acted_on_behalf_of_id` diisi. Nama hook OCA yang tepat diverifikasi terhadap kode 18.0 di M2.

**Pipa Shopify.** Controller: baca body mentah, hitung HMAC, bandingkan dengan `hmac.compare_digest`, simpan `kw.shopify.event` (unik `webhook_id`), `with_delay(channel='root.kw_shopify').process()`, jawab 200. Job: parse order → cari partner (email) atau buat → baris dari `product.map` per SKU; satu SKU hilang → `needs_mapping` (tanpa SO setengah jadi). Push stok: override `stock.quant` `_apply_inventory`/`write` memanggil `_kw_shopify_mark_dirty(product_ids)`; job debounced (identity_key per store) mengumpulkan produk kotor dan mengirim satu mutation `inventorySetQuantities` per ≤ 100 item. Tangani throttle GraphQL (`extensions.cost`) dengan retry `RetryableJobError`.

**Midtrans.** Ikuti pola provider core (mis. `payment_razorpay`): `_get_specific_rendering_values` membuat Snap token via `POST /snap/v1/transactions` (Basic auth server key) dan mengarahkan ke `redirect_url`; `_get_tx_from_notification_data` + `_process_notification_data` memetakan `transaction_status` (`capture`/`settlement` → done, `pending` → pending, `deny`/`cancel`/`expire` → cancel/error).

**REST API.** Dekorator `@kw_api_route(scope='stock:read')` → autentikasi key (prefix lookup + `hmac.compare_digest` hash), rate bucket (upsert per menit), `request.update_env(user=key.user_id)` sehingga record rules berlaku, serialisasi lewat skema eksplisit per resource (bukan `read()` mentah, agar field sensitif tidak bocor).

**Migrasi v16 → v18.** Tag v16 berisi modul asli. Commit terpisah: (1) manifest version + assets, (2) views `attrs`/`states` → `invisible`/`readonly`, `tree` → `list`, (3) Python: `name_get` → `_compute_display_name`, `@api.model_create_multi`, (4) JS legacy widget → komponen OWL, (5) `migrations/18.0.1.0.0/pre-migrate.py` rename kolom (`ALTER TABLE ... RENAME COLUMN kiln_temp TO peak_temp_c` bila kolom lama ada). Core dimigrasi dengan OpenUpgrade dua lompatan (16→17→18); langkah dicatat di `docs/MIGRATION-16-18.md`.

## 6. Integrasi pihak ketiga
| Layanan | Untuk | Batasan | Biaya | Sandbox demo |
|---|---|---|---|---|
| Shopify Admin GraphQL | Order, stok, produk | Throttle berbasis cost; versi API dirilis per kuartal (perlu verifikasi versi aktif) | Dev store Partner gratis (perlu verifikasi) | Dev store + mock Flask untuk CI |
| Midtrans Snap | Pembayaran invoice IDR | Sandbox dan production terpisah | Sandbox gratis; MDR produksi perlu verifikasi | Sandbox + mock notifikasi |
| OCA modules | Tier validation, queue | AGPL-3; pin commit | Gratis | — |
| VPS demo | Demo online | 4 GB RAM disarankan untuk Odoo + PG | Perlu verifikasi | Cloudflare Tunnel sebagai alternatif |

## 7. Keamanan
- Grup: `kw_ops.group_user` (lihat dashboard, inbox), `kw_ops.group_manager` (retry sinkron, mapping, kelola API key), `base.group_system` (secret).
- Record rules: user teknis API hanya membaca perusahaan sendiri; delegate hanya melihat review yang didelegasikan.
- Secret: field `groups` restricted + tidak ada di `get_views` untuk non-admin; di demo online diisi kredensial sandbox saja.
- Webhook masuk: verifikasi tanda tangan sebelum menulis apa pun; body maksimum 1 MB.
- `sudo()` hanya di controller publik setelah verifikasi, dengan komentar alasan.
- Audit: chatter (`mail.thread`) di store, endpoint, API key; semua aksi approval tercatat.
- Demo online: akun reviewer read-only (grup tanpa write), DB direset tiap malam.

## 8. Strategi tes
| Modul | Tes wajib |
|---|---|
| kw_approval | PO 48,6 jt → 2 review berurutan; self-approve dialihkan; PO USD dikonversi; delegasi aktif/kedaluwarsa; constraint delegasi melingkar; cron SLA hanya sekali |
| kw_shopify | HMAC valid/invalid (`HttpCase`); webhook duplikat; SKU hilang → needs_mapping → retry sukses; debounce stok mengirim satu mutation (mock `requests`) |
| payment_midtrans | signature valid/invalid; pemetaan 6 status; notifikasi ganda |
| kw_rest_api | scope kurang → 403; key dicabut → 401; rate limit → 429; record rule mencegah kebocoran; retry webhook terjadwal benar |
| kw_ops_dashboard | `get_data` pada DB kosong dan DB demo; tes QUnit/Hoot untuk komponen periode |
| kw_reports | render PDF packing list (`_render_qweb_pdf`) tanpa error; total berat |
| kw_firing_batch | tes modul di v18 + tes migrasi: fixture kolom lama → pre-migrate → nilai pindah |
| Tur | 1 tur `HttpCase.start_tour` untuk alur S01 → S02 approve |

Milestone selesai bila CI hijau untuk modul milestone itu dan semua modul sebelumnya.

## 9. Deploy & lingkungan
- **Lokal:** `docker compose up` (odoo:18.0 di port 8069 internal, dipetakan ke **8069**; cek bentrok port dengan proyek lain di mesin user), postgres:16 volume bernama. `make demo` = buat DB `kilnworks` + `-i kw_demo --without-demo=False`.
- **Env:** `SHOPIFY_*`, `MIDTRANS_*` hanya dibaca oleh skrip seed `make sandbox` yang mengisi record (bukan di kode modul).
- **Demo online (M6):** VPS kecil atau mesin lokal + Cloudflare Tunnel; Nginx proxy; reset DB harian dari dump; backup harian.
- **Seed:** synthetic, berlabel di README; tidak ada data orang nyata.
