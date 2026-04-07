from odoo import _, api, fields, models
from odoo.exceptions import UserError
from ..services import CloudLinkerService, CloudLinkerApiError


class CloudLinkerRegisterWizard(models.TransientModel):
    _name = "cloudlinker.register.wizard"
    _description = "CloudLinker Registration"

    email = fields.Char(string="Email", required=True)
    password = fields.Char(string="Password", required=True)
    firstname = fields.Char(string="First Name", required=True)
    lastname = fields.Char(string="Last Name", required=True)
    company = fields.Char(string="Company")
    plan_id = fields.Selection(
        selection="_get_plan_selection",
        string="Plan",
        required=True,
    )

    @api.model
    def _get_plan_selection(self):
        ICP = self.env["ir.config_parameter"].sudo()
        base_url = ICP.get_param("cloudlinker_print.base_url", "https://cloudlinker.eu/api")
        try:
            plans = CloudLinkerService.get_plans(base_url)
            return [(str(p["id"]), p["name"]) for p in plans]
        except CloudLinkerApiError:
            return []

    def action_register(self):
        self.ensure_one()
        ICP = self.env["ir.config_parameter"].sudo()
        base_url = ICP.get_param("cloudlinker_print.base_url", "https://cloudlinker.eu/api")

        try:
            result = CloudLinkerService.register(
                base_url,
                self.email,
                self.password,
                self.firstname,
                self.lastname,
                self.company or "",
                int(self.plan_id),
            )
        except CloudLinkerApiError as exc:
            raise UserError(str(exc)) from exc

        ICP.set_param("cloudlinker_print.organization_id", result["organization_id"])
        ICP.set_param("cloudlinker_print.api_key", result["api_key"])

        org_name = result.get("organization_name", "")

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("CloudLinker"),
                "message": _("Account created for '%s'. Credentials saved. You have a 30-day free trial.") % org_name,
                "type": "success",
                "sticky": False,
                "next": {"type": "ir.actions.act_window_close"},
            },
        }
