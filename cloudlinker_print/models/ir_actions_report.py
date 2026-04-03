import logging
from odoo import models

_logger = logging.getLogger(__name__)


class IrActionsReport(models.Model):
    _inherit = "ir.actions.report"

    def _render_qweb_pdf(self, report_ref, res_ids=None, data=None):
        """
        After rendering the PDF, also send it to CloudLinker if auto-print
        is enabled and a matching document rule exists.
        """
        result = super()._render_qweb_pdf(report_ref, res_ids=res_ids, data=data)

        ICP = self.env["ir.config_parameter"].sudo()
        if not ICP.get_param("cloudlinker_print.auto_print"):
            return result

        if not res_ids:
            return result

        report = self._get_report(report_ref)
        if not report:
            return result

        doc_type = self._cloudlinker_map_report_to_doc_type(report)
        if not doc_type:
            return result

        try:
            records = self.env[report.model].browse(res_ids)
            for record in records:
                if hasattr(record, "cloudlinker_print"):
                    record.cloudlinker_print(doc_type)
                    _logger.info(
                        "CloudLinker auto-print: %s #%s → %s",
                        report.model, record.id, doc_type,
                    )
        except Exception as exc:
            _logger.warning("CloudLinker auto-print failed: %s", exc)

        return result

    def _cloudlinker_map_report_to_doc_type(self, report):
        """Map a report to its CloudLinker document type."""
        model = report.model
        mapping = {
            "account.move": "invoice",
            "stock.picking": "picking",
            "pos.order": "pos_receipt",
            "sale.order": "quotation",
        }
        return mapping.get(model)
