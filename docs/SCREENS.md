# Screens — Kilnworks on Odoo

Semua layar berada di dalam Odoo 18 backend (chrome Odoo dipertahankan). Mode Impeccable: hampir semuanya **Operate**; mockup harus terasa native Odoo, karena itu yang dinilai klien.

| ID | Layar | Peran | Mode | Fitur PRD | Mockup? |
|---|---|---|---|---|---|
| S01 | Ops Dashboard (OWL client action) | Ratna, Bayu | Read | F8 | **ya** |
| S02 | Purchase Order form + panel tier approval | Dimas, Ratna | Operate | F2, F3 | **ya** |
| S03 | Inbox Approvals (list lintas model) | Ratna, Sekar | Operate | F2, F3 | tidak (list Odoo standar) |
| S04 | Quotation dengan tier diskon | Sekar | Operate | F2 | tidak |
| S05 | Shopify Console (OWL client action) | Bayu | Operate | F4 | **ya** (digabung S06) |
| S06 | Sync Log / detail event + Retry | Bayu | Operate | F4 | ya (panel di S05) |
| S07 | Halaman pembayaran invoice → Midtrans Snap | Pelanggan B2B | Operate | F5 | tidak (halaman portal core + Snap) |
| S08 | PDF Packing list ekspor | Bayu | Read | F9 | tidak (PDF QWeb, dibuat di M5) |
| S09 | API Keys & Webhook deliveries | Admin | Operate | F6, F7 | tidak |
| S10 | Delegations | Ratna | Operate | F3 | tidak |
| S11 | Firing Batch form | Dimas | Operate | F10 | tidak |

## S01 — Ops Dashboard
- **Tujuan:** dalam 10 detik tahu apa yang perlu ditangani hari ini.
- **Konteks:** pagi hari di laptop (Ratna juga di ponsel, layout menyusun satu kolom).
- **Isi (urutan):** (1) perlu tindakan: approval tertunda dengan umur dan pemilik; event sinkron gagal; (2) omzet per kanal periode ini vs sebelumnya (B2B IDR, Shopify USD dikonversi); (3) stok di bawah minimum; (4) invoice jatuh tempo.
- **Aksi:** ganti periode (7/30/90 hari, segmented), klik baris → record; "Open Sync Log".
- **State:** kosong (DB baru: "Belum ada order. Hubungkan toko Shopify di Configuration › Stores"), loading (skeleton per blok), error RPC (pesan + coba lagi), angka panjang (Rp 1.284.650.000 tetap muat).
- **Data contoh (synthetic):** PO/2026/0418 Sumber Lempung Godean Rp 48.600.000, menunggu 26 jam; S/2026/1187 Teras Kopi Jakal diskon 15%; SKU KW-MUG-350-SAGE needs_mapping.

## S02 — Purchase Order + tier
- **Tujuan:** melihat siapa yang harus menyetujui, menyetujui atau menolak dengan alasan.
- **Konteks:** desktop, beberapa kali seminggu.
- **Isi:** status bar (Draft → Waiting Validation → Purchase Order), banner "Menunggu persetujuan", tabel tier (urutan, reviewer, atas nama, status, waktu), baris PO, total, chatter berisi histori pengalihan self-approve.
- **Aksi:** Approve / Reject (dengan komentar), Request Validation (pembuat), Confirm terkunci.
- **State:** belum diminta, menunggu L1, ditolak (komentar), disetujui semua, total berubah setelah approval (banner reset).
- **Data contoh:** 2.400 kg tanah liat Godean @ Rp 14.500, 60 kg glasir celadon @ Rp 180.000, kardus ekspor 400 pcs @ Rp 7.500 = Rp 48.600.000 (vendor non-PKP, tanpa PPN).

## S03 — Inbox Approvals
- List `tier.review` milik saya + yang didelegasikan, kolom dokumen, jumlah, umur, atas nama; aksi massal tidak ada (persetujuan harus disengaja). State kosong: "Tidak ada yang menunggu persetujuan Anda".

## S04 — Quotation diskon
- Form SO standar; baris diskon > 10% memicu banner tier dan Confirm terkunci.

## S05/S06 — Shopify Console + Sync Log
- **Tujuan:** memastikan semua order Shopify masuk dan stok terkirim; memperbaiki yang gagal.
- **Konteks:** Bayu, pagi dan setelah kampanye, desktop.
- **Isi:** status toko (domain, versi API, webhook terdaftar, push stok terakhir), hitungan event 24 jam per state, tabel event (waktu, topic, order Shopify, state, SO), panel detail event terpilih (error, payload ringkas, langkah perbaikan).
- **Aksi:** filter state, Retry event, Create mapping (membuka form mapping dengan SKU terisi), Push stock now.
- **State:** toko belum terhubung, semua sehat, ada needs_mapping, failed karena throttle (retry otomatis terjadwal), payload panjang.
- **Data contoh:** #KW1042 orders/create 09:14 done → S/2026/1203; #KW1043 needs_mapping SKU KW-MUG-350-SAGE; inventory push 18 item 09:20.

## S07 — Pembayaran Midtrans
- Portal invoice core menampilkan provider Midtrans; Snap menangani VA/QRIS. State: pending (VA dibuat), settlement, expire.

## S08 — Packing list
- PDF A4: header eksportir, consignee, per karton (no., isi, qty, berat bersih/kotor, dimensi), HS code per produk, batch pembakaran per lot, total.

## S09 — API Keys & Webhooks
- List key (prefix, scope, terakhir dipakai, kedaluwarsa); key penuh ditampilkan sekali saat dibuat. List delivery dengan state dan tombol Resend.

## S10 — Delegations
- List + form: dari, ke, tanggal (date picker Odoo), alasan; validasi melingkar ditampilkan sebagai error form.

## S11 — Firing Batch
- Form: tungku, tanggal, suhu puncak (°C), durasi, state, lot terkait, defect rate.

Mockup yang dipilih: **S01, S02, S05+S06**: tiga mekanisme khas (ringkasan lintas modul, approval bertingkat, pipa integrasi yang bisa diperbaiki).
