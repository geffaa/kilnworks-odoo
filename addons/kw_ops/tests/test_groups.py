from odoo.tests import TransactionCase, new_test_user, tagged


@tagged("post_install", "-at_install")
class TestGroups(TransactionCase):
    def test_owner_implies_lead_implies_user(self):
        owner = new_test_user(self.env, "kw_owner_g", groups="base.group_user,kw_ops.group_manager")
        self.assertTrue(owner.has_group("kw_ops.group_production_lead"))
        self.assertTrue(owner.has_group("kw_ops.group_user"))

    def test_app_hidden_without_group(self):
        outsider = new_test_user(self.env, "kw_outsider", groups="base.group_user")
        menus = self.env["ir.ui.menu"].with_user(outsider)._visible_menu_ids()
        self.assertNotIn(self.env.ref("kw_ops.menu_root").id, menus)
