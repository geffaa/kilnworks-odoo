#!/usr/bin/env bash
# Install and test addons/kw_firing_batch on Odoo 16 in throwaway containers.
# Used to prove the pre-migration module really worked on 16.0 (see docs/MIGRATION-16-18.md).
set -euo pipefail
cd "$(dirname "$0")/.."
net=kw16-$$
docker network create "$net" >/dev/null
cleanup() { docker rm -f "$net-db" >/dev/null 2>&1 || true; docker network rm "$net" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker run -d --name "$net-db" --network "$net" -e POSTGRES_USER=odoo -e POSTGRES_PASSWORD=odoo \
  -e POSTGRES_DB=postgres postgres:15 >/dev/null
until docker exec "$net-db" pg_isready -U odoo >/dev/null 2>&1; do sleep 1; done
addons_dir=$(mktemp -d "$PWD/.legacy16.XXXX") && cp -R addons/kw_firing_batch "$addons_dir"/
docker run --rm --network "$net" -e HOST="$net-db" -e USER=odoo -e PASSWORD=odoo -v "$addons_dir":/mnt/extra-addons:ro odoo:16.0 \
  odoo -d legacy16 \
  --addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons \
  -i kw_firing_batch --test-tags=/kw_firing_batch --test-enable --stop-after-init --without-demo=all \
  --log-level=test 2>&1 | tee "${LOG:-/dev/null}" | grep -E "tests when|ERROR|CRITICAL|FAIL" || true
rm -rf "$addons_dir"
