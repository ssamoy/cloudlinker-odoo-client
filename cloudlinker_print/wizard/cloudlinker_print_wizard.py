from odoo import _, api, fields, models
from odoo.exceptions import UserError
from ..services import CloudLinkerApiError


class CloudLinkerPrintWizard(models.TransientModel):
    _name = "cloudlinker.print.wizard"
    _description = "CloudLinker – Select Printer"

    res_model    = fields.Char(string="Model", required=True)
    res_id       = fields.Integer(string="Record ID", required=True)
    document_type = fields.Char(string="Document Type", required=True)
    report_ref   = fields.Char(string="Report Reference")

    device_id = fields.Many2one(
        comodel_name="cloudlinker.device",
        string="Printer",
        required=True,
        default=lambda self: self._default_device(),
    )

    @api.model
    def _default_device(self):
        devices = self.env["cloudlinker.device"].search([], limit=2)
        if len(devices) == 1:
            return devices.id
        return False
    copies = fields.Integer(string="Copies", default=1)

    def action_print(self):
        self.ensure_one()
        record = self.env[self.res_model].browse(self.res_id)
        if not record.exists():
            raise UserError(_("The document no longer exists."))

        record.cloudlinker_print(
            document_type=self.document_type,
            report_ref=self.report_ref or None,
            device_id=self.device_id.id,
        )
        return {
            "type": "ir.actions.client",
            "tag": "display_notification",
            "params": {
                "title": _("CloudLinker"),
                "message": _("Print job sent to '%s' (%s copies).") % (
                    self.device_id.name, self.copies
                ),
                "type": "success",
                "sticky": False,
            },
        }
