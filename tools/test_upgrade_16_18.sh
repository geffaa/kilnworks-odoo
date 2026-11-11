#!/usr/bin/env bash
# Full upgrade rehearsal for kw_firing_batch: a 16.0 database with 30 firing
# batches goes through OpenUpgrade 17.0 and 18.0, then the module's own
# migration script. Prints what survived. See docs/MIGRATION-16-18.md.
#
#   tools/test_upgrade_16_18.sh          # everything runs in throwaway containers
set -euo pipefail
cd "$(dirname "$0")/.."
root=$PWD
work=$root/.upgrade                # inside $HOME so Colima can mount it
net=kwup-$$
db=upgrade
mkdir -p "$work"

cleanup() {
  docker rm -f "$net-db" >/dev/null 2>&1 || true
  docker network rm "$net" >/dev/null 2>&1 || true
  rm -rf "$work/addons16" "$work/addons18"
}
trap cleanup EXIT

say() { printf '\n== %s\n' "$*"; }

for v in 17.0 18.0; do
  [ -d "$work/OpenUpgrade-$v" ] || git clone -q --depth 1 -b "$v" https://github.com/OCA/OpenUpgrade.git "$work/OpenUpgrade-$v"
done

# 16.0 module from the tag, 18.0 module from the working tree.
rm -rf "$work/addons16" "$work/addons18"
mkdir -p "$work/addons16" "$work/addons18"
git archive kw_firing_batch-16.0 addons/kw_firing_batch | tar -x -C "$work/addons16" --strip-components=1
cp -R addons/kw_firing_batch "$work/addons18/"

docker network create "$net" >/dev/null
docker run -d --name "$net-db" --network "$net" -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo \
  -e POSTGRES_DB=postgres postgres:15 >/dev/null
until docker exec "$net-db" pg_isready -U odoo >/dev/null 2>&1; do sleep 1; done

odoo() { # odoo <version> <extra docker args...> -- <odoo args...>
  local v=$1; shift
  local dargs=()
  while [ "$1" != "--" ]; do dargs+=("$1"); shift; done; shift
  docker run --rm -i --network "$net" -u root -e HOST="$net-db" -e USER=odoo -e PASSWORD=odoo \
    -v "$work":/work ${dargs[@]+"${dargs[@]}"} "odoo:$v" sh -c '
      pip install -q --break-system-packages openupgradelib >/dev/null 2>&1 || pip install -q openupgradelib >/dev/null 2>&1
      exec su odoo -s /bin/sh -c "odoo --db_host=$HOST --db_user=$USER --db_password=$PASSWORD $*"' -- "$@"
}

say "16.0: install kw_firing_batch and seed 30 batches"
odoo 16.0 -- -d $db --addons-path=/work/addons16,/usr/lib/python3/dist-packages/odoo/addons \
  -i kw_firing_batch --without-demo=all --stop-after-init --log-level=warn
docker run --rm -i --network "$net" -e HOST="$net-db" -e USER=odoo -e PASSWORD=odoo -v "$work":/work odoo:16.0 \
  odoo shell -d $db --no-http \
  --addons-path=/work/addons16,/usr/lib/python3/dist-packages/odoo/addons --log-level=warn <<'PY'
import datetime, random
random.seed(16)
kilns = env["kw.kiln"].create([{"name": "Gas kiln 1", "kiln_type": "gas"}, {"name": "Electric kiln", "kiln_type": "electric"}])
mug = env["product.product"].create({"name": "Celadon mug", "type": "product"})
for i in range(30):
    loaded = random.randint(120, 400)
    b = env["kw.firing.batch"].create({
        "kiln_id": kilns[i % 2].id,
        "fired_on": datetime.date(2023, 1, 1) + datetime.timedelta(days=i * 12),
        "kiln_temp": random.randint(1180, 1310),
        "duration_h": round(random.uniform(9, 14), 1),
        "line_ids": [(0, 0, {"product_id": mug.id, "qty_loaded": loaded, "qty_good": loaded - random.randint(2, 30)})],
    })
    if i < 26:
        b.action_start(); b.action_done()
env["ir.filters"].create({"name": "Hot firings", "model_id": "kw.firing.batch", "domain": "[('kiln_temp', '>', 1280)]"})
env.cr.commit()
print("SEED", env["kw.firing.batch"].search_count([]), sum(env["kw.firing.batch"].search([]).mapped("kiln_temp")))
PY

say "17.0: OpenUpgrade (kw_firing_batch has no 17.0 code, its tables wait)"
odoo 17.0 -- -d $db -u all --stop-after-init --log-level=warn --load=base,web,openupgrade_framework \
  --upgrade-path=/work/OpenUpgrade-17.0/openupgrade_scripts/scripts \
  --addons-path=/work/OpenUpgrade-17.0,/usr/lib/python3/dist-packages/odoo/addons

say "18.0: OpenUpgrade + kw_firing_batch 18.0.1.0.0 migration"
odoo 18.0 -- -d $db -u all --stop-after-init --log-level=info --load=base,web,openupgrade_framework \
  --upgrade-path=/work/OpenUpgrade-18.0/openupgrade_scripts/scripts \
  --addons-path=/work/addons18,/work/OpenUpgrade-18.0,/usr/lib/python3/dist-packages/odoo/addons \
  2>&1 | grep -E "kw_firing_batch|ERROR|CRITICAL" || true

say "Result on 18.0"
docker run --rm -i --network "$net" -e HOST="$net-db" -e USER=odoo -e PASSWORD=odoo -v "$work":/work odoo:18.0 \
  odoo shell -d $db --no-http \
  --addons-path=/work/addons18,/usr/lib/python3/dist-packages/odoo/addons --log-level=warn <<'PY'
B = env["kw.firing.batch"]
mod = env["ir.module.module"].search([("name", "=", "kw_firing_batch")])
batches = B.search([])
print("MODULE", mod.state, mod.latest_version)
print("BATCHES", len(batches), "with temperature", len(batches.filtered("peak_temp")), "sum", sum(batches.mapped("peak_temp")))
print("STATES", {s: B.search_count([("state", "=", s)]) for s in ("draft", "in_kiln", "done")})
print("DISPLAY", batches[:1].display_name)
print("FILTER", env["ir.filters"].search([("model_id", "=", "kw.firing.batch")]).domain)
print("OLD_COLUMN", bool(env.cr.execute("SELECT 1 FROM information_schema.columns WHERE table_name='kw_firing_batch' AND column_name='kiln_temp'") or env.cr.fetchone()))
PY
