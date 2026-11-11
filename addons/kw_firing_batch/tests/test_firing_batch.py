from odoo.exceptions import UserError
from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestFiringBatch(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.kiln = cls.env["kw.kiln"].create(
            {"name": "Gas kiln 1", "kiln_type": "gas", "capacity_pcs": 420}
        )
        cls.mug = cls.env["product.product"].create(
            {"name": "Celadon mug", "type": "consu", "is_storable": True}
        )

    def _batch(self, **vals):
        return self.env["kw.firing.batch"].create(dict({"kiln_id": self.kiln.id}, **vals))

    def test_sequence_and_display_name(self):
        batch = self._batch(peak_temp=1280)
        self.assertTrue(batch.name.startswith("FB/"))
        self.assertEqual(batch.display_name, f"{batch.name} · Gas kiln 1 · 1280 °C")

    def test_defect_rate(self):
        batch = self._batch(
            line_ids=[(0, 0, {"product_id": self.mug.id, "qty_loaded": 200, "qty_good": 186})]
        )
        self.assertEqual(batch.defect_rate, 7.0)

    def test_close_needs_temperature(self):
        batch = self._batch()
        batch.action_start()
        with self.assertRaises(UserError):
            batch.action_done()
        batch.peak_temp = 1275
        batch.action_done()
        self.assertEqual(batch.state, "done")
