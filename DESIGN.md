# DESIGN — Kilnworks on Odoo

Ditulis dari mockup yang sudah jadi (`mockups/`, generator `tools/mockups/build.py`, CSS `mockups/kilnworks-ds.css`).

## Keputusan arah
**Native Odoo 18 Community + satu lapisan identitas Kilnworks.** Produk ini dinilai klien Odoo dari satu hal: apakah modul terasa seperti bagian dari Odoo. Karena itu chrome host (navbar ungu `#71639e` seperti Odoo 18 Community asli, dikoreksi setelah membandingkan dengan instance M1; breadcrumb, control panel, status bar berpanah, form sheet, chatter di kanan) dan tokennya (primary Community `#71639e`, badge Bootstrap, system font stack) dipertahankan. Identitas sendiri hanya muncul di dalam client action custom, lewat dua warna glasir: **celadon** `#5f8f7b` (Shopify, ikon toko, keadaan kosong) dan **clay** `#a5673f` (seri B2B). Ini berbeda dari produk portfolio lain (Roster, Relay, Sukha, dst.) yang punya dunia visual sendiri. Di sini *menahan diri adalah keputusan desainnya*.

Elemen yang diingat: **pita "perlu tindakan"** di dashboard. Satu panel dua kolom dengan angka besar (approval dan event sinkron), dan setiap barisnya bisa diklik ke record asli.

## Token
| Token | Nilai | Pakai |
|---|---|---|
| `--o-brand` | #71639e | tombol primary, tab aktif, segmented terpilih (host) |
| `--o-ink` / `-2` / `-3` | #1f2328 / #4a5059 / #636a74 | teks; semua ≥ 4.5:1 di putih |
| `--o-bg` / `--o-surface` | #f2f3f5 / #fff | dasar webclient / panel & sheet |
| `--o-success/warning/danger/info` (+ `-bg`) | lihat CSS | badge state, alert |
| `--kw-celadon` / `-ink` / `-soft` | #5f8f7b / #2f5a49 / #e6efeb | lapisan Kilnworks: Shopify, empty state |
| `--kw-clay` | #a5673f | seri B2B di grafik, avatar owner |
| Tipe | 12 / 13 / 14 / 16 / 20 / 26 px | skala Odoo; body 14 |
| Spasi | 4 / 8 / 12 / 16 / 24 / 32 / 48 | |
| Radius | 4 (kontrol) / 6 (popover) / 8 (panel) | |

Mode terang saja. Dipakai di kantor dan gudang pada siang hari, dan backend Odoo Community default terang.

## Komponen
- **Panel**: border 1px, radius 8, tanpa shadow. Header 48px dengan judul 16/600 + hitungan abu.
- **List**: gaya `o_list_view`. Header 13/600, baris hover `#f8f9fa`, baris terpilih `--o-brand-soft`, angka tabular dan rata kanan.
- **Tier steps**: daftar bernomor (urutan memang bermakna), dot kuning untuk tier aktif, catatan pengalihan/eskalasi dengan ikon Lucide.
- **Segmented** (`role=radiogroup`): periode dashboard dan filter state Sync Log, dengan hitungan di dalam tombol.
- **Detail event**: `dl` dua kolom, kotak perbaikan kuning yang menyebut masalah dan cara memulihkan, timeline, dan payload JSON mono (mono hanya untuk data).
- **Form custom**: pemilih Many2one/listbox, kalender range, dan checkbox digambar sendiri di mockup. Di modul nyata dipakai komponen OWL Odoo (`Dropdown`, `DateTimeInput`, `CheckBox`), tidak ada kontrol native.
- **State**: skeleton, empty (ikon celadon + langkah berikutnya), dan alert error dengan tautan "Try again".

## Ikon & gambar
Lucide resmi (lucide-static) lewat `kit.py`, stroke 1.75. Tidak ada foto: ini permukaan kerja di dalam ERP. Foto produk stoneware baru diperlukan nanti untuk data demo `product.template` (sumber dan lisensi akan dicatat di `mockups/IMAGES.md` saat M1).

## Review (2026-11-10)
- Screenshot 1440 dan 390 untuk 5 halaman ada di `.impeccable/review/`. Console bersih, tidak ada scroll horizontal.
- `impeccable detect`: tersisa 8 temuan yang diterima dengan alasan:
  - `flat-type-hierarchy` (14→16): mengikuti skala Odoo; hierarki dibawa oleh bobot.
  - `cramped-padding` pada segmented (inset 2px memang desainnya), pita perlu tindakan (tabel menempel ke tepi seperti list Odoo), dan kotak search.
- Kontras `.out` di kalender sudah diperbaiki.
