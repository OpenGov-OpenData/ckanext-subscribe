# encoding: utf-8
import pytest

from ckan import plugins as p
from ckan.tests import factories as ckan_factories
from ckan.tests import helpers

from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.email_verification import (
    get_verification_email_vars,
    get_verification_email_contents
)
from ckanext.subscribe.tests import factories


@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestEmailVerification(object):

    def setup(self):
        helpers.reset_db()
        subscribe_model.setup()

    def test_get_verification_email_vars(self):
        dataset = ckan_factories.Dataset()
        subscription = factories.Subscription(
            dataset_id=dataset['id'], return_object=True)
        subscription.verification_code = 'testcode'

        email_vars = get_verification_email_vars(subscription)

        assert email_vars['site_title'], p.toolkit.config['ckan.site_title']
        assert email_vars['site_url'], 'http://test.ckan.net'
        assert email_vars['object_title'], 'Test Dataset'
        assert email_vars['object_type'], 'dataset'
        assert email_vars['email'], 'bob@example.com'
        assert email_vars['verification_link'], 'http://test.ckan.net/subscribe/verify?code=testcode'
        assert email_vars['object_link'], 'http://test.ckan.net/dataset/{}'.format(dataset['id'])

    def test_get_verification_email_contents(self):
        dataset = ckan_factories.Dataset()
        subscription = factories.Subscription(
            dataset_id=dataset['id'], return_object=True)
        subscription.verification_code = 'testcode'

        subject, body_plain_text, body_html = \
            get_verification_email_contents(subscription)

        assert subject, 'Confirm your request for CKAN subscription'
        assert body_plain_text.strip().startswith(
            'CKAN subscription requested'), body_plain_text.strip()
        assert body_html.strip().startswith(
            '<p>CKAN subscription requested'), body_html.strip()
