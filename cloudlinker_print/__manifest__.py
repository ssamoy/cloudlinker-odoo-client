{
    'name': 'CloudLinker Print',
    'version': '1.0.0',
    'category': 'Technical',
    'summary': 'Print documents on local printers via CloudLinker cloud print service',
    'description': """
CloudLinker Print Integration
==============================
Connect your Odoo instance to CloudLinker to print documents directly
on local printers from the cloud — no drivers, no hassle.

Features
--------
* Configure your CloudLinker API key in Settings
* Fetch and manage available printers
* Assign default printers per document type
* Print invoices, picking slips, shipping labels, QWeb reports and POS receipts
* Manual printer override via wizard

Supported document types
-------------------------
- Invoices & credit notes (account.move)
- Picking / warehouse labels (stock.picking)
- Shipping labels (stock.picking)
- Custom QWeb reports (ir.actions.report)
- POS receipts (pos.order)

Compatibility: Odoo 16, 17, 18
    """,
    'author': 'CloudLinker',
    'website': 'https://www.cloudlinker.io',
    'license': 'LGPL-3',
    'depends': [
        'base',
        'account',
        'stock',
        'sale',
        'point_of_sale',
    ],
    'data': [
        'security/cloudlinker_security.xml',
        'security/ir.model.access.csv',
        'data/cloudlinker_document_rule_data.xml',
        'data/cloudlinker_quotation_rule_data.xml',
        'views/res_config_settings_views.xml',
        'views/cloudlinker_printer_views.xml',
        'views/cloudlinker_document_rule_views.xml',
        'views/cloudlinker_print_wizard_views.xml',
        'views/account_move_views.xml',
        'views/stock_picking_views.xml',
        'views/sale_order_views.xml',
        'views/pos_order_views.xml',
        'views/cloudlinker_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'cloudlinker_print/static/src/js/cloudlinker_action.js',
        ],
    },
    'images': ['static/description/banner.png'],
    'installable': True,
    'application': False,
    'auto_install': False,
}
