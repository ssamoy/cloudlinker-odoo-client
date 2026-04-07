from odoo import _, api, fields, models
from odoo.exceptions import UserError
from ..services import CloudLinkerService, CloudLinkerApiError


class CloudLinkerLoginWizard(models.TransientModel):
    _name = "cloudlinker.login.wizard"
    _description = "CloudLinker Login"

    email = fields.Char(string="Email", required=True)
    password = fields.Char(string="Password", required=True)

    def action_login(self):
        self.ensure_one()
        ICP = self.env["ir.config_parameter"].sudo()
        base_url = ICP.get_param("cloudlinker_print.base_url", "https://cloudlinker.eu/api")

        try:
            result = CloudLinkerService.login(base_url, self.email, self.password)
        except CloudLinkerApiError as exc:
            raise UserError(str(exc)) from exc

        ICP.set_param("cloudlinker_print.organization_id", result["organization_id"])
        ICP.set_param("cloudlinker_print.api_key", result["api_key"])

        plan_name = result.get("plan", {}).get("name", "") if result.get("plan") else ""
        org_name = result.get("organization_name", "")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("CloudLinker"),
                "message": _("Connected as '%s'. Credentials saved.") % org_name,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
