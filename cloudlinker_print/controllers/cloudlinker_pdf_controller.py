import logging
from odoo import http
from odoo.http import request, Response

_logger = logging.getLogger(__name__)


class CloudLinkerPdfController(http.Controller):
    """
    Serves temporary PDF files to the CloudLinker client agent.

    Flow:
      1. Odoo renders a report PDF and stores it in ir.attachment
         with description="cloudlinker_token:<token>"
      2. The CloudLinker job payload contains:
         document_url = <web.base.url>/cloudlinker/pdf/<token>
      3. The CloudLinker client fetches this URL to download the PDF.

    Security:
      - Tokens are SHA-256 hashes, effectively random and single-use.
      - No Odoo session is required (the CloudLinker agent has none).
      - Attachment is deleted after serving (one-time download).
    """

    @http.route(
        "/cloudlinker/pdf/<string:token>",
        type="http",
        auth="public",
        methods=["GET"],
        csrf=False,
    )
    def serve_pdf(self, token, **kwargs):
        if not token or len(token) < 32:
            return Response("Invalid token", status=400)

        # Find attachment by token stored in description field
        attachment = (
            request.env["ir.attachment"]
            .sudo()
            .search(
                [("description", "=", f"cloudlinker_token:{token}")],
                limit=1,
            )
        )

        if not attachment:
            _logger.warning("CloudLinker: no attachment found for token %s", token)
            return Response("Not found", status=404)

        pdf_data = attachment.raw or b""
        filename = attachment.name or "document.pdf"

        # Delete attachment immediately after serving (one-time use)
        try:
            attachment.sudo().unlink()
            _logger.debug("CloudLinker: served and deleted attachment for token %s", token)
        except Exception:
            _logger.exception("CloudLinker: could not delete attachment for token %s", token)

        return Response(
            pdf_data,
            status=200,
            headers={
                "Content-Type": "application/pdf",
                "Content-Disposition": f'attachment; filename="{filename}"',
                "Content-Length": str(len(pdf_data)),
                "Cache-Control": "no-store",
            },
        )
