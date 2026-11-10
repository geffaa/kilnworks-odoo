# Kilnworks Demo Company (`kw_demo`)

Creates the synthetic company every other Kilnworks module is shown on: Kilnworks Stoneware, a stoneware
maker in Kasongan, Bantul. All names, addresses and numbers are made up.

What it installs:
- Company in IDR with the Indonesian chart of accounts (`l10n_id`), timezone Asia/Jakarta.
- Four users with role groups: `ratna` (owner), `dimas` (production and purchasing), `sekar` (B2B sales),
  `bayu` (e-commerce ops). Each password equals the login; local demos only.
- 18 finished products (`KW-…` SKUs) and 6 raw materials with vendor prices.
- 90 days of history ending on the install date: 14 purchase orders (received), 26 B2B sales orders
  (delivered, invoiced, most older invoices paid, recent ones still quotations).
- Stock levels and minimums chosen so five products sit below minimum.

The history is generated once by `post_init_hook` with a fixed random seed, so every fresh database matches.
