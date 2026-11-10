# Information Architecture — Kilnworks on Odoo

Produk ini hidup **di dalam Odoo 18 backend**. Navigasi utama (app switcher, menu atas, breadcrumb, control panel, chatter) milik Odoo dan tidak diganti. Keputusan IA di sini mengatur di mana modul custom menempel dan bagaimana alurnya menyambung.

## Peran & permukaan

| Peran (synthetic) | Siapa | Permukaan utama |
|---|---|---|
| Owner / Approver L2 | Ratna Wibisono, pemilik | Inbox approval, Dashboard Ops |
| Purchasing / Approver L1 | Dimas Pratama, kepala produksi | Purchase, Firing Batches |
| Sales B2B | Sekar Ayuningtyas | Sales, Invoices, link pembayaran Midtrans |
| Ops e-commerce | Bayu Santoso | Shopify Console, Inventory |
| Integrator eksternal | Developer aplikasi gudang / klien | REST API `/api/v1`, webhook keluar (tanpa UI Odoo) |
| Pelanggan B2B (P2) | Kafe "Teras Kopi Jakal" | Portal Odoo |

## Peta modul (semua fase)

```
Odoo app switcher
├── Kilnworks Ops            (kw_ops_dashboard)       ← app baru, ikon sendiri
│   ├── Dashboard            OWL client action                       P1
│   ├── Approvals            inbox lintas model (PO, SO)             P1
│   ├── Shopify              Console · Product Map · Sync Log        P1  (WooCommerce P2)
│   ├── Firing Batches       kw_firing_batch                         P1
│   ├── Ask Ops              asisten data                            P3
│   └── Configuration        Approval Rules · Delegations · API Keys · Webhooks · Stores
├── Purchase  (core)  + tombol "Request Validation", panel tier       P1
├── Sales     (core)  + tier diskon                                   P1
├── Invoicing (core)  + Midtrans payment link · ekspor Coretax (P2)
├── Inventory (core)  + laporan packing list & delivery slip batch    P1
└── Website/Portal (core) + portal B2B                                P2
```

Keputusan: satu app **Kilnworks Ops** sebagai rumah semua permukaan custom, sementara perluasan pada dokumen core (PO, SO, invoice, picking) tetap di app core-nya. Alasan: pengguna Odoo mencari PO di Purchase, bukan di app baru; tapi pekerjaan lintas model (inbox approval, sinkron, dashboard) butuh satu tempat. Trade-off: dua jalur masuk ke approval (dari PO langsung dan dari inbox), yang diterima karena keduanya membuka record yang sama.

## Alur end-to-end

### A. Procure → Pay (bahan baku)
1. Dimas membuat PO tanah liat Rp 48.600.000 (Purchase) → klik **Request Validation**.
2. Rule: > Rp 10 jt butuh kepala produksi, > Rp 25 jt ditambah owner. Pembuat tidak boleh menyetujui PO sendiri, jadi tier L1 milik Dimas dialihkan ke owner (ditulis di chatter).
3. Ratna sedang cuti → delegasi ke Sekar (berlaku 10–14 Nov) → muncul di Inbox Approvals Sekar.
4. Lewat 24 jam tanpa aksi → cron eskalasi, aktivitas + email ke owner.
5. Disetujui → Confirm Order → Receipt → Vendor Bill (core).

### B. Shopify order → Ship → Settle (D2C global)
1. Webhook `orders/create` masuk → verifikasi HMAC → simpan event (idempoten per `X-Shopify-Webhook-Id`) → job antrean.
2. Job membuat `sale.order` (kanal Shopify, USD), mapping SKU → `product.product`; SKU tak dikenal → status *needs mapping* di Sync Log.
3. Delivery dibuat, packing list ekspor dicetak (QWeb) dengan nomor batch pembakaran.
4. Stok berubah → job push `inventorySetQuantities` ke Shopify.
5. P2: fulfillment + resi dikirim balik ke Shopify.

### C. B2B quote → Invoice → Midtrans
1. Sekar membuat quotation 120 cangkir untuk kafe, diskon 15% → tier diskon (> 10%) minta owner.
2. Confirm → Invoice → **Send & Print** berisi link pembayaran Midtrans Snap.
3. Notifikasi Midtrans → verifikasi `signature_key` → transaksi `done` → invoice paid.
4. P2: ekspor Coretax XML.

### D. Integrasi eksternal
1. Admin membuat API key ber-scope (`stock:read`, `orders:read`) untuk aplikasi gudang.
2. Aplikasi memanggil `/api/v1/stock?location=WH/Stock`.
3. Stok turun di bawah min → webhook `stock.low` bertanda tangan ke URL aplikasi; gagal → retry bertahap, tampil di log.

### E. Firing batch (dan kisah migrasinya)
1. Batch pembakaran dibuat (tungku, suhu puncak, tanggal) → lot produk jadi ditautkan ke batch.
2. Delivery slip menampilkan batch. Riwayat repo: modul ini lahir di v16, dimigrasi ke v18 (commit terpisah per jenis perubahan).

## Keputusan navigasi
- **Tidak mengganti chrome Odoo.** Menu, breadcrumb, control panel, dan chatter adalah kontrak UX yang dikenali pengguna Odoo; klien Upwork menilai apakah modul *terasa native*.
- Client action custom (Dashboard, Shopify Console) memakai komponen OWL di dalam layout Odoo (`Layout` + control panel), bukan halaman berdiri sendiri.
- Status kesehatan sinkron muncul di dua tempat: kartu di Dashboard (ringkas) dan Sync Log (detail + retry). Tidak ada notifikasi popup; kegagalan menjadi aktivitas untuk Bayu.
