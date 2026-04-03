from odoo import models


class SaleOrder(models.Model):
    _name = "sale.order"
    _inherit = ["sale.order", "cloudlinker.mixin"]

    def _cloudlinker_default_report(self):
        return self.env.ref("sale.action_report_saleorder", raise_if_not_found=False)

    def _cloudlinker_job_title(self) -> str:
        return f"Quotation {self.name or self.id}"

    def action_cloudlinker_print_quotation(self):
        return self.action_cloudlinker_print_wizard("quotation")
