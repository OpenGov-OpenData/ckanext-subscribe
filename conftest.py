# -*- coding: utf-8 -*-
import six

if six.PY3:
    pytest_plugins = [
        u'ckan.tests.pytest_ckan.ckan_setup',
        u'ckan.tests.pytest_ckan.fixtures',
    ]
