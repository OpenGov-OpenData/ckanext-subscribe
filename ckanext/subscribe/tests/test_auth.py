# encoding: utf-8

import pytest

from ckan.tests import helpers
from ckan.tests import factories
from ckan import logic, model


@pytest.mark.usefixtures('clean_db', 'with_plugins')
class TestSubscribeSignupToDataset(object):

    def setup(self):
        helpers.reset_db()

    def test_no_user_specified(self):
        dataset = factories.Dataset(state='deleted')
        context = {'model': model}
        context['user'] = ''

        with pytest.raises(logic.NotAuthorized) as cm:
            helpers.call_auth('subscribe_signup', context=context,
                              dataset_id=dataset['name'])
            assert 'not authorized to read package' in cm.exception.message

    def test_deleted_dataset_not_subscribable(self):
        factories.User(name='fred')
        dataset = factories.Dataset(state='deleted')
        context = {'model': model}
        context['user'] = 'fred'

        with pytest.raises(logic.NotAuthorized) as cm:
            helpers.call_auth('subscribe_signup', context=context,
                              dataset_id=dataset['name'])
            assert 'User fred not authorized to read package' in cm.exception.message

    def test_private_dataset_is_subscribable_to_editor(self):
        fred = factories.User(name='fred')
        fred['capacity'] = 'editor'
        org = factories.Organization(users=[fred])
        dataset = factories.Dataset(owner_org=org['id'], private=True)
        context = {'model': model}
        context['user'] = 'fred'

        ret = helpers.call_auth('subscribe_signup', context=context,
                                dataset_id=dataset['name'])
        assert ret

    def test_private_dataset_is_not_subscribable_to_public(self):
        factories.User(name='fred')
        org = factories.Organization()
        dataset = factories.Dataset(owner_org=org['id'], private=True)
        context = {'model': model}
        context['user'] = 'fred'

        with pytest.raises(logic.NotAuthorized) as cm:
            helpers.call_auth('subscribe_signup', context=context,
                              dataset_id=dataset['name'])
            assert 'User fred not authorized to read package' in cm.exception.message

    def test_admin_cant_skip_verification(self):
        # (only sysadmin can)
        fred = factories.User(name='fred')
        fred['capacity'] = 'editor'
        org = factories.Organization(users=[fred])
        dataset = factories.Dataset(owner_org=org['id'])
        context = {'model': model}
        context['user'] = 'fred'

        with pytest.raises(logic.NotAuthorized) as cm:
            helpers.call_auth('subscribe_signup', context=context,
                              dataset_id=dataset['name'],
                              skip_verification=True)
            assert 'Not authorized to skip verification' in cm.exception.message


class TestSubscribeListSubscriptions(object):

    def setup(self):
        helpers.reset_db()

    def test_admin_cant_use_it(self):
        # (only sysadmin can)
        fred = factories.User(name='fred')
        fred['capacity'] = 'editor'
        factories.Organization(users=[fred])
        context = {'model': model}
        context['user'] = 'fred'

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth('subscribe_list_subscriptions', context=context,
                              email=fred['email'])


class TestSubscribeUnsubscribe(object):

    def setup(self):
        helpers.reset_db()

    def test_admin_cant_use_it(self):
        # (only sysadmin can)
        fred = factories.User(name='fred')
        fred['capacity'] = 'editor'
        factories.Organization(users=[fred])
        context = {'model': model}
        context['user'] = 'fred'

        with pytest.raises(logic.NotAuthorized):
            helpers.call_auth('subscribe_unsubscribe', context=context,
                              email=fred['email'])
