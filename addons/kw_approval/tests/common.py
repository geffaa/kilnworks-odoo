from odoo import Command
from odoo.tests import TransactionCase, new_test_user


class KwApprovalCase(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))
        groups = "base.group_user,purchase.group_purchase_user,sales_team.group_sale_salesman"
        cls.lead = new_test_user(
            cls.env, "kw_lead", groups=groups + ",kw_ops.group_production_lead", name="Lead"
        )
        cls.owner = new_test_user(
            cls.env,
            "kw_owner",
            groups=groups + ",kw_ops.group_manager,purchase.group_purchase_manager",
            name="Owner",
        )
        cls.buyer = new_test_user(cls.env, "kw_buyer", groups=groups, name="Buyer")
        cls.delegate = new_test_user(cls.env, "kw_delegate", groups=groups, name="Delegate")
        # Only our test users approve: drop anyone else the groups picked up (admin, demo).
        for xmlid, keep in (
            ("kw_ops.group_production_lead", cls.lead | cls.owner),
            ("kw_ops.group_manager", cls.owner),
        ):
            group = cls.env.ref(xmlid)
            group.users = [Command.set(keep.ids)]
        cls.vendor = cls.env["res.partner"].create({"name": "CV Sumber Lempung Godean"})
        cls.customer = cls.env["res.partner"].create({"name": "Teras Kopi Jakal"})
        cls.clay = cls.env["product.product"].create(
            {
                "name": "Stoneware clay",
                "type": "consu",
                "standard_price": 14500,
                "list_price": 20000,
            }
        )
        cls.idr = cls.env.ref("base.IDR")
        cls.idr.active = True
        cls.env.company.currency_id = cls.idr  # only safe because the test db has no entries

    def _po(self, amount, user=None, currency=None):
        user = user or self.lead
        vals = {
            "partner_id": self.vendor.id,
            "order_line": [
                Command.create(
                    {
                        "product_id": self.clay.id,
                        "product_qty": 1,
                        "price_unit": amount,
                        "taxes_id": False,
                    }
                )
            ],
        }
        if currency:
            vals["currency_id"] = currency.id
        return self.env["purchase.order"].with_user(user).create(vals)
