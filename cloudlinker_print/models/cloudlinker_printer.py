from odoo import fields, models


class CloudLinkerClient(models.Model):
    """A client = a machine running the CloudLinker agent."""
    _name = "cloudlinker.client"
    _description = "CloudLinker Client"
    _order = "hostname"

    name = fields.Char(string="Hostname", related="hostname", store=True)
    hostname = fields.Char(string="Hostname", required=True)
    cloudlinker_id = fields.Char(string="CloudLinker ID", required=True, index=True, copy=False)
    ip_address = fields.Char(string="IP Address")
    description = fields.Char(string="Description")
    last_seen = fields.Datetime(string="Last Seen")
    active = fields.Boolean(default=True)

    device_ids = fields.One2many("cloudlinker.device", "client_id", string="Devices")
    device_count = fields.Integer(compute="_compute_device_count")

    def _compute_device_count(self):
        for rec in self:
            rec.device_count = len(rec.device_ids)

    _sql_constraints = [
        ("cl_id_uniq", "UNIQUE(cloudlinker_id)", "A client with this CloudLinker ID already exists."),
    ]


class CloudLinkerDevice(models.Model):
    """A device = a printer attached to a client."""
    _name = "cloudlinker.device"
    _description = "CloudLinker Device (Printer)"
    _order = "name"

    name = fields.Char(string="Printer Name", required=True)
    cloudlinker_id = fields.Char(string="CloudLinker Device ID", required=True, index=True, copy=False)
    client_id = fields.Many2one(
        comodel_name="cloudlinker.client",
        string="Client",
        required=True,
        ondelete="cascade",
    )
    active = fields.Boolean(default=True)

    document_rule_ids = fields.One2many(
        comodel_name="cloudlinker.document.rule",
        inverse_name="device_id",
        string="Document Rules",
    )

    _sql_constraints = [
        ("cl_device_id_uniq", "UNIQUE(cloudlinker_id)", "A device with this CloudLinker ID already exists."),
    ]

    def name_get(self):
        res = []
        for rec in self:
            label = f"{rec.name} [{rec.client_id.hostname}]" if rec.client_id else rec.name
            res.append((rec.id, label))
        return res
