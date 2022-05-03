# encoding: utf-8

import datetime
import mock
import pytest

from ckan.tests.factories import Dataset, Group, Organization

from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.tests.factories import (
    Subscription,
    SubscriptionLowLevel,
)
from ckanext.subscribe.tests import SubscribeBase
from ckanext.subscribe import email_auth


@pytest.mark.usefixtures('with_plugins')
class TestSignupSubmit(SubscribeBase):
    @pytest.mark.usefixtures('clean_db', 'clean_index')
    @mock.patch('ckanext.subscribe.mailer.mail_recipient')
    def test_signup_to_dataset_ok(self, mock_mailer):
        dataset = Dataset()
        response = self.app.post(
            '/subscribe/signup',
            params={'email': 'bob@example.com', 'dataset': dataset['id']},
            status=302,
            follow_redirects=False
        )
        assert mock_mailer.called
        assert response.location == 'http://test.ckan.net/dataset/{}?__no_cache__=True'.format(dataset['name'])

    @pytest.mark.usefixtures('clean_db', 'clean_index')
    @mock.patch('ckanext.subscribe.mailer.mail_recipient')
    def test_signup_to_group_ok(self, mock_mailer):
        group = Group()
        response = self.app.post(
            '/subscribe/signup',
            params={'email': 'bob@example.com', 'group': group['id']},
            status=302,
            follow_redirects=False
        )
        assert mock_mailer.called
        assert response.location == 'http://test.ckan.net/group/{}?__no_cache__=True'.format(group['name'])

    @pytest.mark.usefixtures('clean_db', 'clean_index')
    @mock.patch('ckanext.subscribe.mailer.mail_recipient')
    def test_signup_to_org_ok(self, mock_mailer):
        org = Organization()
        response = self.app.post(
            '/subscribe/signup',
            params={'email': 'bob@example.com', 'group': org['id']},
            status=302,
            follow_redirects=False
        )
        assert mock_mailer.called
        assert response.location == 'http://test.ckan.net/organization/{}?__no_cache__=True'.format(org['name'])

    @pytest.mark.usefixtures('clean_db', 'clean_index')
    def test_get_not_post(self):
        response = self.app.get('/subscribe/signup', status=400)
        assert 'No email address supplied' in response.body

    @pytest.mark.usefixtures('clean_db', 'clean_index')
    def test_object_not_specified(self):
        response = self.app.post(
            '/subscribe/signup',
            params={'email': 'bob@example.com'},  # no dataset or group
            status=200)
        assert 'Error subscribing: Must specify one of: &#34;dataset_id&#34;' in response.body

    @pytest.mark.usefixtures('clean_db', 'clean_index')
    def test_dataset_missing(self):
        response = self.app.post(
            '/subscribe/signup',
            params={'email': 'bob@example.com', 'dataset': 'unknown'},
            status=404
        )
        assert 'Dataset not found' in response.body

    @pytest.mark.usefixtures('clean_db', 'clean_index')
    def test_group_missing(self):
        response = self.app.post(
            '/subscribe/signup',
            params={'email': 'bob@example.com', 'group': 'unknown'},
            status=404
        )
        assert 'Group not found' in response.body

    @pytest.mark.usefixtures('clean_db', 'clean_index')
    def test_empty_email(self):
        dataset = Dataset()
        response = self.app.post(
            '/subscribe/signup',
            params={'email': '', 'dataset': dataset['id']},
            status=400)
        assert 'No email address supplied' in response.body

    @pytest.mark.usefixtures('clean_db', 'clean_index')
    def test_bad_email(self):
        dataset = Dataset()
        response = self.app.post(
            '/subscribe/signup',
            params={'email': 'invalid email', 'dataset': dataset['id']},
            status=400)
        assert 'Email supplied is invalid' in response.body


@pytest.mark.usefixtures('clean_db', 'clean_index', 'with_plugins')
class TestVerifySubscription(SubscribeBase):
    @mock.patch('ckanext.subscribe.mailer.mail_recipient')
    def test_verify_dataset_ok(self, mock_mailer):
        dataset = Dataset()
        SubscriptionLowLevel(
            object_id=dataset['id'],
            object_type='dataset',
            email='bob@example.com',
            frequency=subscribe_model.Frequency.IMMEDIATE.value,
            verification_code='verify_code',
            verification_code_expires=datetime.datetime.now() +
            datetime.timedelta(hours=1)
        )

        response = self.app.post(
            '/subscribe/verify',
            params={'code': 'verify_code'},
            status=302,
            follow_redirects=False
        )
        assert mock_mailer.called
        assert response.location.startswith(
            'http://test.ckan.net/subscribe/manage?code=')

    def test_wrong_code(self):
        response = self.app.post(
            '/subscribe/verify',
            params={'code': 'unknown_code'},
            status=302,
            follow_redirects=False
        )
        assert response.location == 'http://test.ckan.net/?__no_cache__=True'


@pytest.mark.usefixtures('clean_db', 'clean_index', 'with_plugins')
class TestManage(SubscribeBase):
    def test_basic(self):
        dataset = Dataset()
        Subscription(
            dataset_id=dataset['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        code = email_auth.create_code('bob@example.com')

        response = self.app.get(
            '/subscribe/manage',
            params={'code': code},
            status=200)

        assert dataset['title'] in response.body

    def test_no_code(self):
        response = self.app.get(
            '/subscribe/manage',
            params={'code': ''},
            status=302,
            follow_redirects=False
        )

        assert response.location.startswith(
           'http://test.ckan.net/subscribe/request_manage_code')

    def test_bad_code(self):
        response = self.app.get(
            '/subscribe/manage',
            params={'code': 'bad-code'},
            status=302,
            follow_redirects=False
        )

        assert response.location.startswith(
           'http://test.ckan.net/subscribe/request_manage_code')


@pytest.mark.ckan_config('ckan.plugins', 'subscribe')
@pytest.mark.usefixtures('with_plugins', 'with_request_context')
class TestUpdate(SubscribeBase):
    def test_submit(self):
        subscription = Subscription(
            email='bob@example.com',
            frequency='WEEKLY',
            skip_verification=True,
        )
        code = email_auth.create_code('bob@example.com')

        response = self.app.post(
            '/subscribe/update',
            params={'code': code, 'id': subscription['id'],
                    'frequency': 'daily'},
            status=200
        )

        # assert response.location.startswith(
        #     'http://test.ckan.net/subscribe/manage?code=')
        # response = response.follow()
        assert '<option value="DAILY" selected>' in response.body

    def test_form_submit(self):
        subscription = Subscription(
            email='bob@example.com',
            frequency='WEEKLY',
            skip_verification=True,
        )
        code = email_auth.create_code(subscription['email'])

        response = self.app.get(
            '/subscribe/manage',
            params={'code': code},
            status=200)
        assert subscription['email'] in response.body
        form = {
            'frequency': 'IMMEDIATE',
            'code': code,
            'id': subscription['id'],

        }
        post_response = self.app.post('/subscribe/update', data=form, status=200)

        assert '<option value="IMMEDIATE" selected>' in post_response.body

    def test_another_code(self):
        subscription = Subscription(
            email='bob@example.com',
            frequency='WEEKLY',
            skip_verification=True,
        )
        code = email_auth.create_code('someone_else@example.com')

        response = self.app.post(
            '/subscribe/update',
            params={'code': code, 'id': subscription['id'],
                    'frequency': 'daily'},
            status=302,
            follow_redirects=False
        )
        assert response.location.startswith('http://test.ckan.net/subscribe/request_manage_code')


@pytest.mark.usefixtures('with_plugins', 'with_request_context')
class TestUnsubscribe(SubscribeBase):
    def test_basic(self):
        dataset = Dataset()
        Subscription(
            dataset_id=dataset['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        code = email_auth.create_code('bob@example.com')

        response = self.app.get(
            '/subscribe/unsubscribe',
            params={'code': code, 'dataset': dataset['id']},
            status=302,
            follow_redirects=False
        )

        assert response.location == 'http://test.ckan.net/dataset/{}?__no_cache__=True'.format(dataset['name'])

    def test_group(self):
        group = Group()
        Subscription(
            group_id=group['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        code = email_auth.create_code('bob@example.com')

        response = self.app.get(
            '/subscribe/unsubscribe',
            params={'code': code, 'group': group['id']},
            status=302,
            follow_redirects=False
        )

        assert response.location == 'http://test.ckan.net/group/{}?__no_cache__=True'.format(group['name'])

    def test_org(self):
        org = Organization()
        Subscription(
            organization_id=org['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        code = email_auth.create_code('bob@example.com')

        response = self.app.get(
            '/subscribe/unsubscribe',
            params={'code': code, 'organization': org['id']},
            status=302,
            follow_redirects=False
        )

        assert response.location == 'http://test.ckan.net/organization/{}?__no_cache__=True'.format(org['name'])

    def test_no_code(self):
        dataset = Dataset()
        response = self.app.get(
            '/subscribe/unsubscribe',
            params={'code': '', 'dataset': dataset['id']},
            status=302,
            follow_redirects=False
        )

        assert response.location.startswith('http://test.ckan.net/subscribe/request_manage_code')

    def test_bad_code(self):
        dataset = Dataset()
        response = self.app.get(
            '/subscribe/unsubscribe',
            params={'code': 'bad-code', 'dataset': dataset['id']},
            status=302,
            follow_redirects=False
        )

        assert response.location.startswith('http://test.ckan.net/subscribe/request_manage_code')

    def test_no_subscription(self):
        dataset = Dataset()
        code = email_auth.create_code('bob@example.com')

        response = self.app.get(
            '/subscribe/unsubscribe',
            params={'code': code, 'dataset': dataset['id']},
            status=200)

        # assert response.location.startswith(
        #    'http://test.ckan.net/dataset/{}'.format(dataset['name']))
        # response = response.follow()
        assert 'Error unsubscribing: That user is not subscribed to that object' in response.body

    def test_no_object(self):
        code = email_auth.create_code('bob@example.com')
        response = self.app.get(
            '/subscribe/unsubscribe',
            params={'code': code, 'dataset': ''},
            status=302,
            follow_redirects=False
        )

        assert response.location == 'http://test.ckan.net/?__no_cache__=True'


@pytest.mark.usefixtures('with_plugins')
class TestUnsubscribeAll(SubscribeBase):
    def test_basic(self):
        dataset = Dataset()
        Subscription(
            dataset_id=dataset['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        code = email_auth.create_code('bob@example.com')

        response = self.app.get(
            '/subscribe/unsubscribe-all',
            params={'code': code},
            status=200,
        )

        # assert response.location, 'http://test.ckan.net/?__no_cache__=True'  # .format(dataset['name']))
        # response = response.follow()
        assert 'You are no longer subscribed to notifications from CKAN' in response.body

    def test_no_code(self):
        response = self.app.get(
            '/subscribe/unsubscribe-all',
            params={'code': ''},
            status=302,
            follow_redirects=False
        )

        assert response.location.startswith('http://test.ckan.net/subscribe/request_manage_code')

    def test_bad_code(self):
        response = self.app.get(
            '/subscribe/unsubscribe-all',
            params={'code': 'bad-code'},
            status=302,
            follow_redirects=False
        )

        assert response.location.startswith('http://test.ckan.net/subscribe/request_manage_code')

    def test_no_subscription(self):
        Dataset()
        code = email_auth.create_code('bob@example.com')

        response = self.app.get(
            '/subscribe/unsubscribe-all',
            params={'code': code},
            status=200
        )

        # assert response.location.startswith(
        #    'http://test.ckan.net/')
        # response = response.follow()
        assert 'Error unsubscribing: That user has no subscriptions' in response.body

    def test_no_object(self):
        code = email_auth.create_code('bob@example.com')
        response = self.app.get(
            '/subscribe/unsubscribe',
            params={'code': code, 'dataset': ''},
            status=302,
            follow_redirects=False
        )

        assert response.location == 'http://test.ckan.net/?__no_cache__=True'


@pytest.mark.usefixtures('with_plugins')
class TestRequestManageCode(SubscribeBase):
    @mock.patch('ckanext.subscribe.mailer.mail_recipient')
    def test_basic(self, mail_recipient):
        dataset = Dataset()
        Subscription(
            dataset_id=dataset['id'],
            email='bob@example.com',
            skip_verification=True,
        )

        form = {'email': 'bob@example.com'}
        self.app.post('/subscribe/request_manage_code', data=form, status=200)

        mail_recipient.assert_called_once()

    def test_no_email(self):
        self.app.post(
            '/subscribe/request_manage_code',
            params={'email': ''},
            status=200)
        # user is simply asked for the email

    def test_malformed_email(self):
        response = self.app.post(
            '/subscribe/request_manage_code',
            params={'email': 'malformed-email'},
            status=200)

        assert 'Email malformed-email is not a valid format' in response.body

    def test_unknown_email(self):
        response = self.app.post(
            '/subscribe/request_manage_code',
            params={'email': 'unknown@example.com'},
            status=200)

        assert 'That email address does not have any subscriptions' in response.body
