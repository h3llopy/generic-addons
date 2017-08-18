# -*- coding: utf-8 -*-
{
    "name": "Generic Tag - Test",
    "version": "9.0.0.0.1",
    "author": "Management and Accounting Online",
    "website": "https://maao.com.ua",
    "license": "Other proprietary",
    "summary": "Generic Tag - Tests (do not install manualy)",
    'category': 'Technical Settings',
    'depends': [
        'generic_tag',
    ],
    'data': [
        'security/ir.model.access.csv',
    ],
    'demo': [
        'demo/res_groups.xml',
        'demo/demo.xml',
    ],
    'installable': True,
    'auto_install': False,
    'application': False,
}