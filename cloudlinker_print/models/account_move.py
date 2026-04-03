from odoo import _, api, models


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "cloudlinker.mixin"]

    def _cloudlinker_default_report(self):
        return self.env.ref("account.account_invoices", raise_if_not_found=False)

    def _cloudlinker_job_title(self) -> str:
        return f"Invoice {self.name or self.id}"

    def action_cloudlinker_print_invoice(self):
        """Button action: open wizard to print this invoice via CloudLinker."""
        return self.action_cloudlinker_print_wizard("invoice")

    @api.model
    def _cloudlinker_auto_print_on_post(self):
        """Called after _post() when auto-print is enabled."""
        ICP = self.env["ir.config_parameter"].sudo()
        if ICP.get_param("cloudlinker_print.auto_print"):
            for move in self:
                try:
                    move.cloudlinker_print("invoice")
                except Exception:
                    pass  # Don't block posting if print fails

    def action_post(self):
        res = super().action_post()
        self._cloudlinker_auto_print_on_post()
        return res
