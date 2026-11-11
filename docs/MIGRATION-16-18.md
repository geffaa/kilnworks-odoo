# kw_firing_batch: Odoo 16 → 18

`kw_firing_batch` was first written for Odoo 16 and then migrated to 18 (a demo of a typical version-jump job).
Both versions are in git history, so the diff can be reviewed directly:

```bash
git diff kw_firing_batch-16.0 -- addons/kw_firing_batch
```

| Step | Proof |
| --- | --- |
| 16.0 module installs and its tests pass on `odoo:16.0` | `tools/test_legacy16.sh` |
| 18.0 module installs and its tests pass on Odoo 18 | `make test MOD=kw_firing_batch` |
| A 16.0 database with data goes through OpenUpgrade 17 → 18 and the module migration | `tools/test_upgrade_16_18.sh` |

## What changed

| Area | 16.0 | 18.0 | Why |
| --- | --- | --- | --- |
| Field read-only state | `states={"done": [("readonly", True)]}` on fields | `readonly="state == 'done'"` in the view | 17.0 removed `states=` on fields |
| View modifiers | `attrs="{'invisible': [...]}"`, `states="draft"` on buttons | `invisible="state != 'draft'"`, `required="..."` | 17.0 removed `attrs`/`states`; modifiers are Python expressions |
| List views | `<tree>`, `view_mode="tree,form"` | `<list>`, `view_mode="list,form"` | 18.0 rename. XML ids kept (`..._view_tree`) so the upgrade updates the existing views instead of leaving orphans |
| Chatter | `<div class="oe_chatter">` with two fields | `<chatter/>` | 18.0 tag |
| Record label | `name_get()` | `_compute_display_name()` with `@api.depends` | `name_get` was deprecated in 17.0 and removed in 18.0 |
| Create | `@api.model def create(self, vals)` | `@api.model_create_multi def create(self, vals_list)` | Single-record create logs a warning since 17.0; batch create is the norm |
| Product type in tests | `type="product"` | `type="consu", is_storable=True` | 18.0 merged storable products into goods with a flag |
| OWL field | Class added to the `fields` registry, value from `props.value`, `owl="1"` on the template | Descriptor `{...integerField, component}`, value from `props.record.data[props.name]`, static `template` | 17.0 field API |
| Field name | `kiln_temp` | `peak_temp` | Clearer name; renamed in `migrations/18.0.1.0.0/pre-migrate.py` so data survives |

## The migration script

`migrations/18.0.1.0.0/pre-migrate.py` runs before the 18.0 models load. Without it, the ORM would create an
empty `peak_temp` column and the recorded temperatures would be lost when `kiln_temp` is dropped. The script:

1. renames the column `kiln_temp` → `peak_temp` (skips if already done, so it can run twice);
2. renames the `ir.model.fields` row and its xmlid, so tracking history still points to the field;
3. rewrites saved filters (`ir.filters`) that mention the old name.

## Upgrade rehearsal

`tools/test_upgrade_16_18.sh` runs everything in throwaway containers:

1. `odoo:16.0`: install the module from the `kw_firing_batch-16.0` tag, seed 30 batches (26 done, 4 draft) and a saved filter.
2. `odoo:17.0` + OpenUpgrade 17.0: `-u all`. The module has no 17.0 code, so it is skipped and its tables wait untouched.
   This is the usual route for a custom module skipping a version.
3. `odoo:18.0` + OpenUpgrade 18.0 + the 18.0 module: `-u all`. Core is migrated, then `pre-migrate.py` runs for the module.
4. Checks: module state and version, 30 batches, every temperature kept (sum equal to the seed), states, display name,
   saved filter, old column gone.

### Findings

- Odoo 17 logs `Since 17.0, the "attrs" and "states" attributes are no longer used` for the 16.0 views still stored
  in the database while the module waits. Expected: those views are rewritten when the 18.0 module is upgraded.
- Odoo 17 reports `inconsistent states ... ['kw_firing_batch']` because the module code is missing at that step. Expected.
- The PyPI release of `openupgradelib` is older than OpenUpgrade 18.0 needs
  (`no attribute 'add_inherits_parent_xmlids'`). Use the OCA git version. Its setup needs git and
  `setuptools_scm`, which the Odoo images lack, so the script puts it on `PYTHONPATH` instead of installing it.
- On macOS with Colima, only folders under `$HOME` can be mounted into containers; the scripts keep their work files in the repo.

### Result

Run on 2026-11-11 (`odoo:16.0` → OpenUpgrade 17.0 → OpenUpgrade 18.0):

| Check | Seeded on 16.0 | After upgrade to 18.0 |
| --- | --- | --- |
| Module | `kw_firing_batch` 16.0.1.0.0 | installed, 18.0.1.0.0 |
| Batches | 30 | 30 |
| Batches with a temperature | 30 (`kiln_temp`) | 30 (`peak_temp`) |
| Sum of temperatures | 37,513 | 37,513 |
| States | 26 done, 4 draft | 26 done, 4 draft |
| Display name | (`name_get`) | `FB/2026/0030 · Electric kiln · 1289 °C` (`_compute_display_name`) |
| Saved filter | `[('kiln_temp', '>', 1280)]` | `[('peak_temp', '>', 1280)]` |
| Old column `kiln_temp` | present | gone |

No data was lost and the module needed no manual step after the upgrade.
