from odoo import models


class StockPicking(models.Model):
    _name = "stock.picking"
    _inherit = ["stock.picking", "cloudlinker.mixin"]

    def _cloudlinker_default_report(self):
        return self.env.ref("stock.action_report_delivery", raise_if_not_found=False)

    def _cloudlinker_job_title(self) -> str:
        return f"Picking {self.name or self.id}"

    def action_cloudlinker_print_picking(self):
        return self.action_cloudlinker_print_wizard("picking")

    def action_cloudlinker_print_shipping_label(self):
        return self.action_cloudlinker_print_wizard("shipping_label")
