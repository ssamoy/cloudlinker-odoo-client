from odoo import _, api, fields, models
from odoo.exceptions import UserError
from ..services import CloudLinkerService, CloudLinkerApiError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    cloudlinker_organization_id = fields.Char(
        string="Organization ID",
        config_parameter="cloudlinker_print.organization_id",
    )
    cloudlinker_api_key = fields.Char(
        string="API Key",
        config_parameter="cloudlinker_print.api_key",
    )
    cloudlinker_base_url = fields.Char(
        string="API Base URL",
        config_parameter="cloudlinker_print.base_url",
        default="https://cloudlinker.eu/api",
    )
    cloudlinker_auto_print = fields.Boolean(
        string="Auto-print on validation",
        config_parameter="cloudlinker_print.auto_print",
        help="Automatically send documents to CloudLinker when validated.",
    )

    cloudlinker_windows_version = fields.Char(
        string="Windows Version", readonly=True,
        config_parameter="cloudlinker_print.windows_version",
    )
    cloudlinker_windows_url = fields.Char(
        string="Windows Download URL", readonly=True,
        config_parameter="cloudlinker_print.windows_url",
    )
    cloudlinker_linux_version = fields.Char(
        string="Linux Version", readonly=True,
        config_parameter="cloudlinker_print.linux_version",
    )
    cloudlinker_linux_url = fields.Char(
        string="Linux Download URL", readonly=True,
        config_parameter="cloudlinker_print.linux_url",
    )

    def action_cloudlinker_fetch_downloads(self):
        """Fetch latest client download info from CloudLinker API (public endpoint)."""
        self.ensure_one()
        base_url = self.cloudlinker_base_url or "https://cloudlinker.eu/api"
        ICP = self.env["ir.config_parameter"].sudo()
        try:
            for platform in ("windows", "linux"):
                info = CloudLinkerService.get_client_version(base_url, platform)
                ICP.set_param(
                    f"cloudlinker_print.{platform}_version",
                    info.get("latest_version") or "",
                )
                ICP.set_param(
                    f"cloudlinker_print.{platform}_url",
                    info.get("installer_url") or info.get("download_url") or "",
                )
        except CloudLinkerApiError as exc:
            raise UserError(str(exc)) from exc
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    # ------------------------------------------------------------------

    def _cloudlinker_get_service(self):
        org_id = self.cloudlinker_organization_id
        api_key = self.cloudlinker_api_key
        base_url = self.cloudlinker_base_url or "https://cloudlinker.eu/api"
        try:
            return CloudLinkerService(org_id, api_key, base_url)
        except CloudLinkerApiError as exc:
            raise UserError(str(exc)) from exc

    def action_cloudlinker_login_wizard(self):
        """Open login wizard."""
        return {
            "type": "ir.actions.act_window",
            "name": _("Login with CloudLinker"),
            "res_model": "cloudlinker.login.wizard",
            "view_mode": "form",
            "target": "new",
        }

    def action_cloudlinker_register_wizard(self):
        """Open registration wizard."""
        return {
            "type": "ir.actions.act_window",
            "name": _("Create CloudLinker Account"),
            "res_model": "cloudlinker.register.wizard",
            "view_mode": "form",
            "target": "new",
        }

    def action_cloudlinker_clear_settings(self):
        """Clear organization ID and API key."""
        ICP = self.env["ir.config_parameter"].sudo()
        ICP.set_param("cloudlinker_print.organization_id", "")
        ICP.set_param("cloudlinker_print.api_key", "")
        return {
            "type": "ir.actions.client",
            "tag": "reload",
        }

    def action_cloudlinker_test_connection(self):
        self.ensure_one()
        svc = self._cloudlinker_get_service()
        try:
            result = svc.test_connection()
        except CloudLinkerApiError as exc:
            raise UserError(str(exc)) from exc

        org = result.get("organization_id", "")
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "CloudLinker",
                "message": f"Connected ✓  (organization: {org})",
                "type": "success",
                "sticky": False,
            },
        }

    def action_cloudlinker_sync_devices(self):
        """
        Pull all clients and their devices from CloudLinker and upsert
        them as cloudlinker.client / cloudlinker.device records.
        """
        self.ensure_one()
        svc = self._cloudlinker_get_service()

        try:
            clients = svc.get_clients()
        except CloudLinkerApiError as exc:
            raise UserError(str(exc)) from exc

        Client = self.env["cloudlinker.client"]
        Device = self.env["cloudlinker.device"]
        total_devices = 0

        for c in clients:
            cl_id = c["id"]
            existing_client = Client.search([("cloudlinker_id", "=", cl_id)], limit=1)
            client_vals = {
                "hostname": c.get("hostname", cl_id),
                "cloudlinker_id": cl_id,
                "ip_address": c.get("ip_address", ""),
            }
            if existing_client:
                existing_client.write(client_vals)
                client_rec = existing_client
            else:
                client_rec = Client.create(client_vals)

            # Fetch devices for this client
            try:
                devices = svc.get_devices(client_id=cl_id, device_type=1)
            except CloudLinkerApiError:
                devices = []

            for d in devices:
                dev_id = d["id"]
                existing_dev = Device.search([("cloudlinker_id", "=", dev_id)], limit=1)
                dev_vals = {
                    "name": d.get("name", dev_id),
                    "cloudlinker_id": dev_id,
                    "client_id": client_rec.id,
                }
                if existing_dev:
                    existing_dev.write(dev_vals)
                else:
                    Device.create(dev_vals)
                total_devices += 1

        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": "CloudLinker",
                "message": f"{len(clients)} client(s), {total_devices} printer(s) synchronised.",
                "type": "success",
                "sticky": False,
            },
        }
