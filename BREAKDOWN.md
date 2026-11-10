# Kilnworks on Odoo — Breakdown

Portfolio Senior Odoo Developer: satu instalasi **Odoo 18 Community** untuk produsen stoneware fiktif *Kilnworks* (Kasongan; data synthetic) yang menjual global lewat Shopify dan B2B lokal. Instalasi ini memuat enam modul custom yang memperluas core dan OCA. Tiap modul menjawab satu jenis pekerjaan Odoo yang paling sering diminta di Upwork, dan tiap modul menjadi satu Upwork Project Catalog.

## Fitur MVP
| Modul | Isi | Catalog |
|---|---|---|
| `kw_demo` | Perusahaan + seed synthetic | — |
| `kw_approval` | Tier PO & diskon di atas OCA, larangan self-approve, delegasi, SLA 24 jam | Custom module |
| `kw_shopify` | Webhook HMAC idempoten, order → SO lewat `queue_job`, push stok, Sync Log + retry | Shopify integration |
| `payment_midtrans` | Provider Snap baru, notifikasi SHA512 | Payment gateway |
| `kw_rest_api` | `/api/v1` ber-scope, rate limit, webhook keluar bertanda tangan | REST API |
| `kw_ops_dashboard` + `kw_reports` | Dashboard OWL, packing list ekspor & delivery slip per batch | Dashboards & reports |
| `kw_firing_batch` | Ditulis di v16, dimigrasi ke v18 dengan commit + script | Migration |

Ditambah Docker, tes per modul, CI, demo online, dan video. Estimasi: ±5–6 minggu paruh waktu.

## Asumsi berisiko
- **A1**: modul OCA 18.0 (`sale_tier_validation`, `queue_job`) tersedia. Diuji pertama di M1.
- **A6**: semua materi wajib menyebut "demo build". Klaim proyek klien dilarang.
- A2/A3: dev store Shopify dan sandbox Midtrans bisa didapat. Tersedia cadangan mock server.

## Desain
Native Odoo 18: chrome Odoo dipertahankan. Komponen custom memakai token Odoo, ditambah satu lapisan identitas Kilnworks (warna glasir celadon) hanya di dalam client action. Mockup: S01 Dashboard, S02 PO + approval, S05 Shopify Console. Lihat [DESIGN.md](DESIGN.md).

## File
- [PRODUCT.md](PRODUCT.md)
- [docs/PRD.md](docs/PRD.md) · [docs/TECH-SPEC.md](docs/TECH-SPEC.md) · [docs/MILESTONES.md](docs/MILESTONES.md)
- [docs/FEATURE-MAP.md](docs/FEATURE-MAP.md) · [docs/IA.md](docs/IA.md) · [docs/SCREENS.md](docs/SCREENS.md)
- [mockups/index.html](mockups/index.html) · [DESIGN.md](DESIGN.md)
