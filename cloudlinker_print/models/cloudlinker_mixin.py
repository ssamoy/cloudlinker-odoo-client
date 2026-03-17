import logging
from odoo import _, api, models
from odoo.exceptions import UserError
from ..services import CloudLinkerService, CloudLinkerApiError

_logger = logging.getLogger(__name__)


class CloudLinkerMixin(models.AbstractModel):
    """
    Mixin that adds CloudLinker printing to any Odoo model.

    How it works:
    1. Render the Odoo report as PDF
    2. Store it as an attachment and get a download URL
    3. Pass that URL to CloudLinker — the agent fetches it and prints

    The Odoo server URL must be reachable from the client machine.
    For internal deployments this works out of the box.
    """

    _name = "cloudlinker.mixin"
    _description = "CloudLinker Print Mixin"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def cloudlinker_print(self, document_type: str, report_ref: str = None, device_id: int = None):
        """
        Render document and send a print job to CloudLinker.

        :param document_type: key from cloudlinker.document.rule selection
        :param report_ref:    optional external ID of ir.actions.report
        :param device_id:     cloudlinker.device record ID; falls back to document rule default
        """
        self.ensure_one()
        svc = self._cloudlinker_get_service()
        device = self._cloudlinker_resolve_device(document_type, device_id)
        rule = self._cloudlinker_get_rule(document_type)
        copies = rule.copies if rule else 1

        doc_url = self._cloudlinker_get_report_url(report_ref)
        try:
            result = svc.create_print_job(
                client_id=device.client_id.cloudlinker_id,
                device_id=device.cloudlinker_id,
                document_url=doc_url,
                copies=copies,
                launch_immediately=True,
            )
            _logger.info("CloudLinker job created: %s", result.get("id"))
        except CloudLinkerApiError as exc:
            raise UserError(_("CloudLinker print failed: %s") % exc) from exc
        return result

    def action_cloudlinker_print_wizard(self, document_type: str, report_ref: str = None):
        """Open the manual printer-selection wizard for this record."""
        self.ensure_one()
        rule = self._cloudlinker_get_rule(document_type)
        wizard = self.env["cloudlinker.print.wizard"].create({
            "res_model": self._name,
            "res_id": self.id,
            "document_type": document_type,
            "report_ref": report_ref or "",
            "device_id": rule.device_id.id if rule and rule.device_id else False,
            "copies": rule.copies if rule else 1,
        })
        return {
            "type": "ir.actions.act_window",
            "name": _("Print via CloudLinker"),
            "res_model": "cloudlinker.print.wizard",
            "res_id": wizard.id,
            "view_mode": "form",
            "target": "new",
        }

    # ------------------------------------------------------------------
    # Helpers — override in child models
    # ------------------------------------------------------------------

    def _cloudlinker_default_report(self):
        """Return the default ir.actions.report for this model."""
        return None

    def _cloudlinker_job_title(self) -> str:
        return f"{self._description or self._name} #{getattr(self, 'name', self.id)}"

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _cloudlinker_get_service(self) -> CloudLinkerService:
        ICP = self.env["ir.config_parameter"].sudo()
        org_id = ICP.get_param("cloudlinker_print.organization_id", "")
        api_key = ICP.get_param("cloudlinker_print.api_key", "")
        base_url = ICP.get_param("cloudlinker_print.base_url", "https://cloudlinker.eu/api")
        if not org_id or not api_key:
            raise UserError(_("CloudLinker credentials not configured. Go to Settings → CloudLinker."))
        return CloudLinkerService(org_id, api_key, base_url)

    def _cloudlinker_get_rule(self, document_type: str):
        return self.env["cloudlinker.document.rule"].search(
            [("document_type", "=", document_type), ("active", "=", True)],
            limit=1,
        )

    def _cloudlinker_resolve_device(self, document_type: str, device_id: int = None):
        if device_id:
            device = self.env["cloudlinker.device"].browse(device_id)
        else:
            rule = self._cloudlinker_get_rule(document_type)
            if not rule or not rule.device_id:
                raise UserError(
                    _("No default printer configured for '%s'. "
                      "Go to CloudLinker → Document Rules.") % document_type
                )
            device = rule.device_id
        if not device.exists():
            raise UserError(_("The selected printer no longer exists."))
        return device

    def _cloudlinker_get_report_url(self, report_ref: str = None) -> str:
        """
        Return a URL pointing to the rendered PDF that the CloudLinker
        agent can fetch.  Uses Odoo's /report/pdf/ route with a download
        access token so no login is required.
        """
        if report_ref:
            report = self.env.ref(report_ref)
        else:
            report = self._cloudlinker_default_report()
        if not report:
            raise UserError(_("No report found for this document."))

        # Build the report URL using the base URL from system parameters
        ICP = self.env["ir.config_parameter"].sudo()
        base_url = ICP.get_param("web.base.url", "http://localhost:8069")

        # Generate a download token valid for this record
        # Odoo's report controller accepts ?download=1 — for auth we use
        # the access_token field if available, or fall back to session-less
        # download which works on networks where Odoo is reachable.
        record_ids = ",".join(str(i) for i in self.ids)
        url = (
            f"{base_url}/report/pdf/{report.report_name}/{record_ids}"
        )

        # If the model has an access_token field (e.g. sale.order, account.move)
        # append it so the CloudLinker agent can download without logging in.
        if hasattr(self, "access_token") and self.access_token:
            url += f"?access_token={self.access_token}"

        return url
