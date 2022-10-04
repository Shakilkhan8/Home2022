# -*- coding: utf-8 -*-

{
    'name': "Google Spreadsheet Synchronizer",

    'summary': """
        Synchronize any Odoo Object with Specified Spreadsheet""",

    'description': """
        Any Odoo Object with its fields are synchronized with Google Spreadsheet. You can also synchronize
        data from SQL query. Ideal for sharing information with partners
    """,

    'author': "Imanis",
    'maintainer': "Tharcisse M.",
    'website': "http://www.imanis.io",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Productivity',
    'version': '15.0.2.1.0',
    
    'depends': ['base','google_spreadsheet'],
    'support': 'mukundayi@gmail.com',
    'license':'OPL-1',
    'price': 125,
    'currency': 'USD',
    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/res_config_views.xml',
        'views/views.xml',
        'data/cron.xml',
        'views/templates.xml',
    ],
    'assets':{
        'web.assets_backend':[
            'im_od_spreadsheet_sync/static/src/pyeval.js'
            ]
    },

    'external_dependencies': {
        'python': ['google-api-python-client','google-auth-httplib2','google-auth-oauthlib'],
        },
    'images': ['static/description/banner.png'],
    'application':True
}
