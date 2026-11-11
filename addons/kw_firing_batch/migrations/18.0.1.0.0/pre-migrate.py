"""16.0 -> 18.0: kiln_temp became peak_temp.

Runs before the module's models load, so renaming the column keeps every
recorded temperature instead of letting the ORM add an empty peak_temp
and drop kiln_temp.
"""
import logging

_logger = logging.getLogger(__name__)


def _column_exists(cr, table, column):
    cr.execute(
        "SELECT 1 FROM information_schema.columns WHERE table_name = %s AND column_name = %s",
        (table, column),
    )
    return bool(cr.fetchone())


def migrate(cr, version):
    if not version or not _column_exists(cr, "kw_firing_batch", "kiln_temp"):
        return
    if _column_exists(cr, "kw_firing_batch", "peak_temp"):
        return
    cr.execute("ALTER TABLE kw_firing_batch RENAME COLUMN kiln_temp TO peak_temp")
    cr.execute(
        "UPDATE ir_model_fields SET name = 'peak_temp' WHERE model = 'kw.firing.batch' AND name = 'kiln_temp'"
    )
    cr.execute(
        "UPDATE ir_model_data SET name = 'field_kw_firing_batch__peak_temp' "
        "WHERE module = 'kw_firing_batch' AND name = 'field_kw_firing_batch__kiln_temp'"
    )
    # Tracking values and saved filters point at the field by name.
    cr.execute(
        "UPDATE ir_filters SET domain = replace(domain, 'kiln_temp', 'peak_temp'), "
        "context = replace(context, 'kiln_temp', 'peak_temp') WHERE model_id = 'kw.firing.batch'"
    )
    cr.execute("SELECT count(*) FROM kw_firing_batch WHERE peak_temp IS NOT NULL")
    _logger.info("kw_firing_batch: kiln_temp -> peak_temp, %s batches kept their temperature", cr.fetchone()[0])
