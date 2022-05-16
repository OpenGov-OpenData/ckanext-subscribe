# encoding: utf-8

import re
import six

import ckan.lib.helpers as h
from ckan import model
from ckan.common import g, config
from ckan.lib.base import abort
from ckan.plugins.toolkit import (
    ValidationError,
    ObjectNotFound,
    get_action,
    request,
    render,
    redirect_to,
)
from ckan.lib.mailer import MailerException

from ckanext.subscribe import email_auth
from ckanext.subscribe import model as subscribe_model
from ckanext.subscribe.constants import IS_CKAN_29_OR_HIGHER

if six.PY2:
    from ckan.common import _ as ugettext
    from ckan.lib.base import BaseController
else:
    from ckan.common import ugettext


log = __import__('logging').getLogger(__name__)


class _SubscribeController:
    @classmethod
    def signup(cls):
        # validate inputs
        email = cls.get_value_from_request_data('email')
        dataset_title = cls.get_value_from_request_data('dataset-title')
        group_title = cls.get_value_from_request_data('group-title')
        if not email:
            abort(400, ugettext('No email address supplied'))
        email = email.strip()
        # pattern from https://html.spec.whatwg.org/#e-mail-state-(type=email)
        email_re = r'^[a-zA-Z0-9.!#$%&\'*+\/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?' \
                   r'(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
        if not re.match(email_re, email):
            abort(400, ugettext('Email supplied is invalid'))

        # create subscription
        data_dict = {
            'email': email,
            'dataset_id': cls.get_value_from_request_data('dataset'),
            'group_id': cls.get_value_from_request_data('group'),
            'organization_id': cls.get_value_from_request_data('organization'),
        }
        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'auth_user_obj': g.userobj
        }
        try:
            subscription = get_action('subscribe_signup')(context, data_dict)
        except ValidationError as err:
            error_messages = []
            for key_ignored in ('message', '__before', 'dataset_id',
                                'group_id'):
                if key_ignored in err.error_dict:
                    error_messages.extend(err.error_dict.pop(key_ignored))
            if err.error_dict:
                error_messages.append(repr(err.error_dict))
            h.flash_error(ugettext('Error subscribing: {}'
                                   .format('; '.join(error_messages))))
            return cls._redirect_back_to_subscribe_page_from_request(data_dict)
        except MailerException:
            h.flash_error(ugettext('Error sending email - please contact an '
                                   'administrator for help'))
            return cls._redirect_back_to_subscribe_page_from_request(data_dict)
        else:
            subscribe_title = dataset_title or group_title
            h.flash_success(
                ugettext('Subscription to {} was successful, please confirm '
                         'your subscription by checking your email inbox and '
                         'spam/trash folder'.format(subscribe_title))
            )

            return cls._redirect_back_to_subscribe_page(
                subscription['object_name'], subscription['object_type'])

    @classmethod
    def verify_subscription(cls):
        data_dict = {'code': request.params.get('code') or request.values.get('code')}
        context = {
            'model': model,
            'session': model.Session,
            'user': g.user,
            'auth_user_obj': g.userobj
        }

        try:
            subscription = get_action('subscribe_verify')(context, data_dict)
        except ValidationError as err:
            h.flash_error(ugettext('Error subscribing: {}'
                                   .format(err.error_dict['message'])))
            return cls.redirect('home.index', 'home.index', __no_cache__=True)

        h.flash_success(
            ugettext('Subscription confirmed'))
        code = email_auth.create_code(subscription['email'])

        return cls.redirect('subscribe.manage',
                            'ckanext.subscribe.controller:SubscribeController.manage',
                            code=code)

    @classmethod
    def manage(cls):
        code = request.params.get('code')
        if not code:
            h.flash_error('Code not supplied')
            log.debug('No code supplied')
            return cls._request_manage_code_form()
        try:
            email = email_auth.authenticate_with_code(code)
        except ValueError as exp:
            h.flash_error('Code is invalid: {}'.format(exp))
            log.debug('Code is invalid: {}'.format(exp))
            return cls._request_manage_code_form()

        # user has done auth, but it's an email rather than a ckan user, so
        # use site_user
        site_user = get_action('get_site_user')({
            'model': model,
            'ignore_auth': True},
            {}
        )
        context = {
            'model': model,
            'user': site_user['name'],
        }
        subscriptions = \
            get_action('subscribe_list_subscriptions')(
                context, {'email': email})
        frequency_options = [
            dict(text=f.name.lower().capitalize().replace(
                     'Immediate', 'Immediately'),
                 value=f.name)
            for f in sorted(subscribe_model.Frequency, key=lambda x: x.value)
        ]
        return render('subscribe/manage.html', extra_vars={
            'email': email,
            'code': code,
            'subscriptions': subscriptions,
            'frequency_options': frequency_options,
        })

    @classmethod
    def update(cls):
        code = cls.get_value_from_request_data('code')

        if not code:
            h.flash_error('Code not supplied')
            log.debug('No code supplied')
            return cls._request_manage_code_form()
        try:
            email = email_auth.authenticate_with_code(code)
        except ValueError as exp:
            h.flash_error('Code is invalid: {}'.format(exp))
            log.debug('Code is invalid: {}'.format(exp))
            return cls._request_manage_code_form()

        subscription_id = cls.get_value_from_request_data('id')
        if not subscription_id:
            abort(400, ugettext('No id supplied'))
        subscription = model.Session.query(subscribe_model.Subscription) \
            .get(subscription_id)
        if not subscription:
            abort(404, ugettext('That subscription ID does not exist.'))
        if subscription.email != email:
            h.flash_error('Code is invalid for that subscription')
            log.debug('Code is invalid for that subscription')
            return cls._request_manage_code_form()

        frequency = cls.get_value_from_request_data('frequency')
        if not frequency:
            abort(400, ugettext('No frequency supplied'))

        # user has done auth, but it's an email rather than a ckan user, so
        # use site_user
        site_user = get_action('get_site_user')({
            'model': model,
            'ignore_auth': True},
            {}
        )
        context = {
            'model': model,
            'session': model.Session,
            'user': site_user['name'],
        }
        data_dict = {
            'id': subscription_id,
            'frequency': frequency,
        }
        try:
            get_action('subscribe_update')(context, data_dict)
        except ValidationError as err:
            h.flash_error(ugettext('Error updating subscription: {}'
                                   .format(err.error_dict['message'])))
        else:
            h.flash_success(ugettext('Subscription updated'))

        return cls.redirect('subscribe.manage', 'ckanext.subscribe.controller:SubscribeController.manage', code=code)

    @classmethod
    def unsubscribe(cls):
        # allow a GET or POST to do this, so that we can trigger it from a link
        # in an email or a web form
        code = request.params.get('code') or cls.get_value_from_request_data('code')
        if not code:
            h.flash_error('Code not supplied')
            log.debug('No code supplied')
            return cls._request_manage_code_form()
        try:
            email = email_auth.authenticate_with_code(code)
        except ValueError as exp:
            h.flash_error('Code is invalid: {}'.format(exp))
            log.debug('Code is invalid: {}'.format(exp))
            return cls._request_manage_code_form()

        # user has done auth, but it's an email rather than a ckan user, so
        # use site_user
        site_user = get_action('get_site_user')({
            'model': model,
            'ignore_auth': True},
            {}
        )
        context = {
            'model': model,
            'user': site_user['name'],
        }
        data_dict = {
            'email': email,
            'dataset_id': request.params.get('dataset') or cls.get_value_from_request_data('dataset'),
            'group_id': request.params.get('group') or cls.get_value_from_request_data('group'),
            'organization_id': request.params.get('organization') or cls.get_value_from_request_data('organization'),
        }
        try:
            object_name, object_type = \
                get_action('subscribe_unsubscribe')(context, data_dict)
        except ValidationError as err:
            error_messages = []
            for key_ignored in ('message', '__before', 'dataset_id',
                                'group_id'):
                if key_ignored in err.error_dict:
                    error_messages.extend(err.error_dict.pop(key_ignored))
            if err.error_dict:
                error_messages.append(repr(err.error_dict))
            h.flash_error(ugettext('Error unsubscribing: {}'
                                   .format('; '.join(error_messages))))
        except ObjectNotFound as err:
            h.flash_error(ugettext('Error unsubscribing: {}'.format(err)))
        else:
            h.flash_success(
                ugettext('You are no longer subscribed to this {}'.format(object_type)))
            return cls._redirect_back_to_subscribe_page(object_name, object_type)
        return cls._redirect_back_to_subscribe_page_from_request(data_dict)

    @classmethod
    def unsubscribe_all(cls):
        # allow a GET or POST to do this, so that we can trigger it from a link
        # in an email or a web form
        code = cls.get_value_from_request_data('code')
        if not code:
            h.flash_error('Code not supplied')
            log.debug('No code supplied')
            return cls._request_manage_code_form()
        try:
            email = email_auth.authenticate_with_code(code)
        except ValueError as exp:
            h.flash_error('Code is invalid: {}'.format(exp))
            log.debug('Code is invalid: {}'.format(exp))
            return cls._request_manage_code_form()

        # user has done auth, but it's an email rather than a ckan user, so
        # use site_user
        site_user = get_action('get_site_user')({
            'model': model,
            'ignore_auth': True},
            {}
        )
        context = {
            'model': model,
            'user': site_user['name'],
        }
        data_dict = {
            'email': email,
        }
        try:
            get_action('subscribe_unsubscribe_all')(context, data_dict)
        except ValidationError as err:
            error_messages = []
            for key_ignored in ('message', '__before'):
                if key_ignored in err.error_dict:
                    error_messages.extend(err.error_dict.pop(key_ignored))
            if err.error_dict:
                error_messages.append(repr(err.error_dict))
            h.flash_error(ugettext('Error unsubscribing: {}'
                                   .format('; '.join(error_messages))))
        except ObjectNotFound as err:
            h.flash_error(ugettext('Error unsubscribing: {}'.format(err)))
        else:
            h.flash_success(
                ugettext('You are no longer subscribed to notifications from {}'
                         .format(config.get('ckan.site_title'))))
            return cls.redirect('home', 'home.index', __no_cache__=True)
        return cls.redirect(
            'subscribe.manage',
            'ckanext.subscribe.controller:SubscribeController.manage',
            code=code,
            __no_cache__=True
        )

    @staticmethod
    def _redirect_back_to_subscribe_page(object_name, object_type):
        if object_type in ('dataset', 'group', 'organization'):
            return SubscribeController.redirect(
                '{}.read'.format(object_type),
                '{}.read'.format(object_type),
                id=object_name,
                __no_cache__=True
            )
        return SubscribeController.redirect('home.index', 'home.index', __no_cache__=True)

    @staticmethod
    def _redirect_back_to_subscribe_page_from_request(data_dict):
        if data_dict.get('dataset_id'):
            dataset_obj = model.Package.get(data_dict['dataset_id'])
            return SubscribeController.redirect(
                'dataset.read',
                'package.read',
                id=dataset_obj.name if dataset_obj else data_dict['dataset_id'],
                __no_cache__=True
            )
        if data_dict.get('group_id'):
            group_obj = model.Group.get(data_dict['group_id'])
            controller = 'organization' \
                if group_obj and group_obj.is_organization else 'group'
            return SubscribeController.redirect(controller + '.read', controller + '.read',
                                                id=group_obj.name if group_obj else data_dict['group_id'])
        return SubscribeController.redirect('home.index', 'home.index', __no_cache__=True)

    @staticmethod
    def _request_manage_code_form():
        return SubscribeController.redirect('subscribe.request_manage_code',
                                            'ckanext.subscribe.controller:SubscribeController.request_manage_code',
                                            __no_cache__=True
                                            )

    @classmethod
    def request_manage_code(cls):
        email = cls.get_value_from_request_data('email')
        if not email:
            return render('subscribe/request_manage_code.html', extra_vars={})

        context = {
            'model': model,
        }
        try:
            get_action('subscribe_request_manage_code')(
                context, dict(email=email))
        except ValidationError as err:
            error_messages = []
            for key_ignored in ('message', '__before'):
                if key_ignored in err.error_dict:
                    error_messages.extend(err.error_dict.pop(key_ignored))
            if err.error_dict:
                error_messages.append(repr(err.error_dict))
            h.flash_error(ugettext('Error requesting code: {}'
                                   .format('; '.join(error_messages))))
        except ObjectNotFound as err:
            h.flash_error(ugettext('Error requesting code: {}'.format(err)))
        except MailerException:
            h.flash_error(ugettext('Error sending email - please contact an '
                                   'administrator for help'))
        else:
            h.flash_success(
                ugettext('An access link has been emailed to: {}'
                         .format(email)))
            return cls.redirect('home.index', 'home.index')
        return render('subscribe/request_manage_code.html',
                      extra_vars={'email': email})

    @staticmethod
    def get_value_from_request_data(name):
        try:
            # Ckan < 2.9
            if request.method == 'GET':
                return request.params.get(name)
            else:
                return request.POST.get(name)
        except AttributeError:
            # Ckan >= 2.9
            return request.values.get(name)

    @staticmethod
    def redirect(new_route, old_route, **kwargs):
        if IS_CKAN_29_OR_HIGHER:
            redirect_url = h.url_for(new_route, **kwargs)
            return redirect_to(redirect_url, **kwargs)
        else:
            parsed_route = old_route.split('.')
            action = parsed_route[-1]
            controller = old_route.replace('.' + action, '')
            if controller == 'dataset':
                controller = 'package'
            redirect_url = h.url_for(controller=controller, action=action, qualified=True, **kwargs)
            return redirect_to(redirect_url, **kwargs)


if six.PY2:
    class SubscribeController(BaseController, _SubscribeController):
        pass
else:
    class SubscribeController(_SubscribeController):
        pass
