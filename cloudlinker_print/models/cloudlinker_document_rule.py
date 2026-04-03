from odoo import fields, models

DOCUMENT_TYPES = [
    ("invoice", "Invoice / Credit Note"),
    ("picking", "Picking / Warehouse Label"),
    ("shipping_label", "Shipping Label"),
    ("quotation", "Quotation / Sale Order"),
    ("qweb_report", "QWeb Report"),
    ("pos_receipt", "POS Receipt"),
]


class CloudLinkerDocumentRule(models.Model):
    _name = "cloudlinker.document.rule"
    _description = "CloudLinker Default Device per Document Type"
    _order = "document_type"

    document_type = fields.Selection(
        selection=DOCUMENT_TYPES,
        string="Document Type",
        required=True,
    )
    device_id = fields.Many2one(
        comodel_name="cloudlinker.device",
        string="Default Printer",
        ondelete="set null",
    )
    report_id = fields.Many2one(
        comodel_name="ir.actions.report",
        string="Specific Report",
        help="Leave empty to apply to ALL reports of this document type.",
    )
    copies = fields.Integer(string="Copies", default=1)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        (
            "doc_type_report_uniq",
            "UNIQUE(document_type, report_id)",
            "A rule for this document type / report already exists.",
        )
    ]
