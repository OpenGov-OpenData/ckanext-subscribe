# encoding: utf-8

import datetime

import mock
import pytest

from ckan.tests import helpers, factories
from ckan.plugins.toolkit import ValidationError
from ckan import model

from ckanext.subscribe.tests.factories import (
    Subscription,
    SubscriptionLowLevel,
    DatasetActivity,
    )
from ckanext.subscribe import model as subscribe_model


@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestSubscribeSignup(object):
    def setup(self):
        helpers.reset_db()

    @mock.patch('ckanext.subscribe.email_verification.send_request_email')
    def test_basic(self, send_request_email):
        dataset = factories.Dataset()

        subscription = helpers.call_action(
            'subscribe_signup',
            {},
            email='bob@example.com',
            dataset_id=dataset['id'],
        )

        send_request_email.assert_called_once()
        assert send_request_email.call_args[0][0].object_type, 'dataset'
        assert send_request_email.call_args[0][0].object_id, dataset['id']
        assert send_request_email.call_args[0][0].email, 'bob@example.com'
        assert subscription['object_type'], 'dataset'
        assert subscription['object_id'], dataset['id']
        assert subscription['email'], 'bob@example.com'
        assert not subscription['verified']
        assert 'verification_code' not in subscription
        subscription_obj = model.Session.query(subscribe_model.Subscription) \
            .get(subscription['id'])
        assert subscription_obj

    @mock.patch('ckanext.subscribe.email_verification.send_request_email')
    def test_dataset_name(self, send_request_email):
        dataset = factories.Dataset()

        helpers.call_action(
            'subscribe_signup',
            {},
            email='bob@example.com',
            dataset_id=dataset['name'],
        )

        send_request_email.assert_called_once()
        assert send_request_email.call_args[0][0].object_type, 'dataset'
        assert send_request_email.call_args[0][0].object_id, dataset['id']
        assert send_request_email.call_args[0][0].email, 'bob@example.com'

    @mock.patch('ckanext.subscribe.email_verification.send_request_email')
    def test_group_id(self, send_request_email):
        group = factories.Group()

        helpers.call_action(
            'subscribe_signup',
            {},
            email='bob@example.com',
            group_id=group['id'],
        )

        send_request_email.assert_called_once()
        assert send_request_email.call_args[0][0].object_type, 'group'
        assert send_request_email.call_args[0][0].object_id, group['id']
        assert send_request_email.call_args[0][0].email, 'bob@example.com'

    @mock.patch('ckanext.subscribe.email_verification.send_request_email')
    def test_group_name(self, send_request_email):
        group = factories.Group()

        helpers.call_action(
            'subscribe_signup',
            {},
            email='bob@example.com',
            group_id=group['name'],
        )

        send_request_email.assert_called_once()
        assert send_request_email.call_args[0][0].object_type, 'group'
        assert send_request_email.call_args[0][0].object_id, group['id']
        assert send_request_email.call_args[0][0].email, 'bob@example.com'

    @mock.patch('ckanext.subscribe.email_verification.send_request_email')
    def test_org_id(self, send_request_email):
        org = factories.Organization()

        helpers.call_action(
            'subscribe_signup',
            {},
            email='bob@example.com',
            organization_id=org['id'],
        )

        send_request_email.assert_called_once()
        assert send_request_email.call_args[0][0].object_type, 'organization'
        assert send_request_email.call_args[0][0].object_id, org['id']
        assert send_request_email.call_args[0][0].email, 'bob@example.com'

    @mock.patch('ckanext.subscribe.email_verification.send_request_email')
    def test_org_name(self, send_request_email):
        org = factories.Organization()

        helpers.call_action(
            'subscribe_signup',
            {},
            email='bob@example.com',
            organization_id=org['name'],
        )

        send_request_email.assert_called_once()
        assert send_request_email.call_args[0][0].object_type, 'organization'
        assert send_request_email.call_args[0][0].object_id, org['id']
        assert send_request_email.call_args[0][0].email, 'bob@example.com'

    @mock.patch('ckanext.subscribe.email_verification.send_request_email')
    def test_skip_verification(self, send_request_email):
        dataset = factories.Dataset()

        subscription = helpers.call_action(
            'subscribe_signup',
            {},
            email='bob@example.com',
            dataset_id=dataset['id'],
            skip_verification=True,
        )

        assert not send_request_email.called
        assert subscription['object_type'], 'dataset'
        assert subscription['object_id'], dataset['id']
        assert subscription['email'], 'bob@example.com'
        assert subscription['verified'], True

    @mock.patch('ckanext.subscribe.email_verification.send_request_email')
    def test_resend_verification(self, send_request_email):
        dataset = factories.Dataset()
        existing_subscription = Subscription(
            dataset_id=dataset['id'],
            email='bob@example.com',
            skip_verification=False,
            verification_code='original_code',
        )
        send_request_email.reset_mock()

        subscription = helpers.call_action(
            'subscribe_signup',
            {},
            email='bob@example.com',
            dataset_id=dataset['id'],
        )

        send_request_email.assert_called_once()
        assert send_request_email.call_args[0][0].id, existing_subscription['id']
        assert send_request_email.call_args[0][0].object_type, 'dataset'
        assert send_request_email.call_args[0][0].object_id, dataset['id']
        assert send_request_email.call_args[0][0].email, 'bob@example.com'
        assert send_request_email.call_args[0][0].verification_code != 'original_code'
        assert subscription['object_type'], 'dataset'
        assert subscription['object_id'], dataset['id']
        assert subscription['email'], 'bob@example.com'
        assert not subscription['verified']

    @mock.patch('ckanext.subscribe.email_verification.send_request_email')
    def test_dataset_doesnt_exist(self, send_request_email):
        with pytest.raises(ValidationError) as cm:
            helpers.call_action(
                'subscribe_signup',
                {},
                email='bob@example.com',
                dataset_id='doesnt-exist',
            )
            assert "dataset_id': [u'Not found" in str(cm.exception.error_dict)
        assert not send_request_email.called

    @mock.patch('ckanext.subscribe.email_verification.send_request_email')
    def test_group_doesnt_exist(self, send_request_email):
        with pytest.raises(ValidationError) as cm:
            helpers.call_action(
                'subscribe_signup',
                {},
                email='bob@example.com',
                group_id='doesnt-exist',
            )
            assert "group_id': [u'That group name or ID does not exist" in str(cm.exception.error_dict)
        assert not send_request_email.called

    @mock.patch('ckanext.subscribe.email_verification.send_request_email')
    def test_dataset_and_group_at_same_time(self, send_request_email):
        dataset = factories.Dataset()
        group = factories.Group()

        with pytest.raises(ValidationError) as cm:
            helpers.call_action(
                'subscribe_signup',
                {},
                email='bob@example.com',
                dataset_id=dataset['id'],
                group_id=group['id'],
            )
            assert 'Must not specify more than one of: "dataset_id", "group_id" or ' \
                   '"organization_id"' in str(cm.exception.error_dict)

        assert not send_request_email.called


class TestSubscribeVerify(object):
    def setup(self):
        helpers.reset_db()

    @mock.patch('ckanext.subscribe.email_auth.send_subscription_confirmation_email')
    def test_basic(self, send_confirmation_email):
        dataset = factories.Dataset()
        SubscriptionLowLevel(
            object_id=dataset['id'],
            object_type='dataset',
            email='bob@example.com',
            frequency=subscribe_model.Frequency.IMMEDIATE.value,
            verification_code='the_code',
            verification_code_expires=datetime.datetime.now() +
            datetime.timedelta(hours=1)
        )

        subscription = helpers.call_action(
            'subscribe_verify',
            {},
            code='the_code',
        )

        send_confirmation_email.assert_called_once()
        assert send_confirmation_email.call_args[1]['subscription'].email, 'bob@example.com'
        login_codes = model.Session.query(subscribe_model.LoginCode.code) \
            .filter_by(email='bob@example.com') \
            .all()
        assert send_confirmation_email.call_args[0] in login_codes
        subscribe_model.LoginCode.validate_code(
            send_confirmation_email.call_args[0])
        assert subscription['verified'], True
        assert subscription['object_type'], 'dataset'
        assert subscription['object_id'], dataset['id']
        assert subscription['email'], 'bob@example.com'
        assert 'verification_code' not in subscription

    def test_wrong_code(self):
        dataset = factories.Dataset()
        subscription = SubscriptionLowLevel(
            object_id=dataset['id'],
            object_type='dataset',
            email='bob@example.com',
            frequency=subscribe_model.Frequency.IMMEDIATE.value,
            verification_code='the_code',
            verification_code_expires=datetime.datetime.now() +
            datetime.timedelta(hours=1)
        )

        with pytest.raises(ValidationError) as cm:
            subscription = helpers.call_action(
                'subscribe_verify',
                {},
                code='wrong_code',
            )
            assert 'That validation code is not recognized' in str(cm.exception.error_dict)

        subscription = subscribe_model.Subscription.get(subscription['id'])
        assert not subscription.verified

    def test_code_expired(self):
        dataset = factories.Dataset()
        subscription = SubscriptionLowLevel(
            object_id=dataset['id'],
            object_type='dataset',
            email='bob@example.com',
            frequency=subscribe_model.Frequency.IMMEDIATE.value,
            verification_code='the_code',
            verification_code_expires=datetime.datetime.now() -
            datetime.timedelta(hours=1)  # in the past
        )

        with pytest.raises(ValidationError) as cm:
            subscription = helpers.call_action(
                'subscribe_verify',
                {},
                code='the_code',
            )
            assert 'That validation code has expired' in str(cm.exception.error_dict)

        subscription = subscribe_model.Subscription.get(subscription['id'])
        assert not subscription.verified


class TestSubscribeAndVerify(object):
    def setup(self):
        helpers.reset_db()

    @mock.patch('ckanext.subscribe.email_auth.send_subscription_confirmation_email')
    @mock.patch('ckanext.subscribe.email_verification.send_request_email')
    def test_basic(self, send_request_email, send_confirmation_email):
        dataset = factories.Dataset()

        # subscribe
        subscription = helpers.call_action(
            'subscribe_signup',
            {},
            email='bob@example.com',
            dataset_id=dataset['id'],
        )
        code = send_request_email.call_args[0][0].verification_code
        # verify
        subscription = helpers.call_action(
            'subscribe_verify',
            {},
            code=code,
        )

        send_request_email.assert_called_once()
        send_confirmation_email.assert_called_once()
        assert send_request_email.call_args[0][0].object_type, 'dataset'
        assert send_request_email.call_args[0][0].object_id, dataset['id']
        assert send_request_email.call_args[0][0].email, 'bob@example.com'
        assert subscription['object_type'], 'dataset'
        assert subscription['object_id'], dataset['id']
        assert subscription['email'], 'bob@example.com'
        assert subscription['verified'], True
        login_code = send_confirmation_email.call_args[0]
        subscribe_model.LoginCode.validate_code(login_code)


class TestSubscribeListSubscriptions(object):
    def setup(self):
        helpers.reset_db()

    def test_basic(self):
        dataset = factories.Dataset()
        Subscription(
            dataset_id=dataset['id'],
            email='bob@example.com',
            skip_verification=True,
        )

        sub_list = helpers.call_action(
            'subscribe_list_subscriptions', {},
            email='bob@example.com',
        )

        assert [sub['object_id'] for sub in sub_list], [dataset['id']]

    def test_dataset_details(self):
        dataset = factories.Dataset()
        group = factories.Group()
        org = factories.Organization()
        Subscription(
            dataset_id=dataset['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        Subscription(
            group_id=group['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        Subscription(
            group_id=org['id'],
            email='bob@example.com',
            skip_verification=True,
        )

        sub_list = helpers.call_action(
            'subscribe_list_subscriptions', {},
            email='bob@example.com',
        )

        assert set(sub['object_id'] for sub in sub_list), {[dataset['id'], group['id'], org['id']]}
        assert set(sub['object_link'] for sub in sub_list), {[
            '/dataset/{}'.format(dataset['name']),
            '/group/{}'.format(group['name']),
            '/organization/{}'.format(org['name']), ]}
        assert set(sub.get('object_name') for sub in sub_list), {[dataset['name'], group['name'], org['name']]}


class TestUnsubscribe(object):

    def setup(self):
        helpers.reset_db()

    def test_basic(self):
        dataset = factories.Dataset()
        dataset2 = factories.Dataset()
        Subscription(
            dataset_id=dataset['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        Subscription(
            dataset_id=dataset2['id'],
            email='bob@example.com',
            skip_verification=True,
        )

        sub_list = helpers.call_action(
            'subscribe_unsubscribe', {},
            email='bob@example.com',
            dataset_id=dataset['id'],
        )

        sub_list = helpers.call_action(
            'subscribe_list_subscriptions', {},
            email='bob@example.com',
        )
        assert [sub['object_id'] for sub in sub_list], [dataset2['id']]

    def test_group(self):
        group = factories.Group()
        group2 = factories.Group()
        Subscription(
            group_id=group['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        Subscription(
            group_id=group2['id'],
            email='bob@example.com',
            skip_verification=True,
        )

        sub_list = helpers.call_action(
            'subscribe_unsubscribe', {},
            email='bob@example.com',
            group_id=group['id'],
        )

        sub_list = helpers.call_action(
            'subscribe_list_subscriptions', {},
            email='bob@example.com',
        )
        assert [sub['object_id'] for sub in sub_list], [group2['id']]

    def test_org(self):
        org = factories.Organization()
        org2 = factories.Organization()
        Subscription(
            organization_id=org['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        Subscription(
            organization_id=org2['id'],
            email='bob@example.com',
            skip_verification=True,
        )

        sub_list = helpers.call_action(
            'subscribe_unsubscribe', {},
            email='bob@example.com',
            organization_id=org['id'],
        )

        sub_list = helpers.call_action(
            'subscribe_list_subscriptions', {},
            email='bob@example.com',
        )
        assert [sub['object_id'] for sub in sub_list], [org2['id']]


class TestUnsubscribeAll(object):

    def setup(self):
        helpers.reset_db()

    def test_basic(self):
        dataset = factories.Dataset()
        dataset2 = factories.Dataset()
        Subscription(
            dataset_id=dataset['id'],
            email='bob@example.com',
            skip_verification=True,
        )
        Subscription(
            dataset_id=dataset2['id'],
            email='bob@example.com',
            skip_verification=True,
        )

        sub_list = helpers.call_action(
            'subscribe_unsubscribe_all', {},
            email='bob@example.com',
        )

        sub_list = helpers.call_action(
            'subscribe_list_subscriptions', {},
            email='bob@example.com',
        )
        assert not [sub['object_id'] for sub in sub_list]


class TestSendAnyNotifications(object):

    def setup(self):
        helpers.reset_db()

    # Lots of overlap here with:
    # test_notification.py:TestSendAnyImmediateNotifications
    @mock.patch('ckanext.subscribe.notification_email.send_notification_email')
    def test_basic(self, send_notification_email):
        dataset = DatasetActivity(
            timestamp=datetime.datetime.now() - datetime.timedelta(minutes=10))
        subscription = Subscription(dataset_id=dataset['id'])

        helpers.call_action('subscribe_send_any_notifications', {})

        send_notification_email.assert_called_once()
        code, email, notifications = send_notification_email.call_args[0]
        assert type(code), type(u'')
        assert email, 'bob@example.com'
        assert len(notifications), 1
        assert [(a['activity_type'], a['data']['package']['id'])
                for a in notifications[0]['activities']], [('new package', dataset['id'])]
        assert notifications[0]['subscription']['id'], subscription['id']


class TestUpdate(object):
    def setup(self):
        helpers.reset_db()

    def test_basic(self):
        subscription = Subscription(
            email='bob@example.com',
            frequency='WEEKLY',
            skip_verification=True,
        )

        subscription = helpers.call_action(
            'subscribe_update',
            {},
            id=subscription['id'],
            frequency='DAILY',
        )

        assert subscription['frequency'], 'DAILY'

    def test_frequency_not_specified(self):
        subscription = Subscription(
            email='bob@example.com',
            frequency='WEEKLY',
            skip_verification=True,
        )

        subscription = helpers.call_action(
            'subscribe_update',
            {},
            id=subscription['id'],
        )

        assert subscription['frequency'], 'WEEKLY'  # unchanged
