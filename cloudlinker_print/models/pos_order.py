from odoo import _, models
from odoo.exceptions import UserError
from ..services import CloudLinkerApiError


class PosOrder(models.Model):
    _name = "pos.order"
    _inherit = ["pos.order", "cloudlinker.mixin"]

    def _cloudlinker_default_report(self):
        return self.env.ref("point_of_sale.action_report_pos_receipt", raise_if_not_found=False)

    def _cloudlinker_job_title(self) -> str:
        return f"POS Receipt {self.name or self.id}"

    def action_cloudlinker_print_receipt(self):
        return self.action_cloudlinker_print_wizard("pos_receipt")
