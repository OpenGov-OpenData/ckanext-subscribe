import sys
import datetime
import time

from ckan import model
import ckan.plugins as p
from ckanext.subscribe.constants import IS_CKAN_29_OR_HIGHER


def initdb():
    from ckanext.subscribe.model import setup
    setup()


def send_any_notifications(repeatedly):
    log = __import__('logging').getLogger(__name__)

    while True:
        p.toolkit.get_action('subscribe_send_any_notifications')({
            'model': model,
            'ignore_auth': True},
            {}
        )
        if not repeatedly:
            break
        log.debug('Repeating in 10s')
        time.sleep(10)


def create_test_activity(object_id):
    if p.toolkit.check_ckan_version(max_version='2.8.99'):
        model.repo.new_revision()
    obj = model.Package.get(object_id) or model.Group.get(object_id)
    assert obj, 'Object could not be found'
    site_user = p.toolkit.get_action('get_site_user')({
        'model': model,
        'ignore_auth': True},
        {}
    )
    site_user_obj = model.User.get(site_user['name'])
    activity = model.Activity(
        user_id=site_user_obj.id,
        object_id=obj.id,
        activity_type='test activity',
        revision_id=None,
    )
    activity.timestamp = datetime.datetime.now()
    model.Session.add(activity)
    print(activity)
    model.Session.commit()


def delete_test_activity():
    test_activity = model.Session.query(model.Activity) \
        .filter_by(activity_type='test activity') \
        .all()
    for activity in test_activity:
        model.Session.delete(activity)


if not IS_CKAN_29_OR_HIGHER:
    from ckan.lib import cli

    class subscribeCommand(cli.CkanCommand):
        '''subscribe commands

        Usage:

            subscribe initdb
                Initialize the the ckanext-subscribe's database table

            subscribe send-any-notifications [-r]
                Check for activity and for any subscribers, send emails with the
                notifications.
                Option:
                  -r --repeatedly - does it repeatedly every 10s

            subscribe create-test-activity {package-name|group-name|org-name}
                Create some activity for testing purposes, for a given existing
                object.

            subscribe delete-test-activity
                Delete any test activity (i.e. clean up after doing
                'create-test-activity'). Works for test activity on all objects.

        '''

        summary = __doc__.split('\n')[0]
        usage = __doc__
        min_args = 1

        def __init__(self, name):
            self.parser.add_option('-r', '--repeatedly', dest='repeatedly',
                                   action='store_true', default=False,
                                   help='Repeat every 10s')
            super(subscribeCommand, self).__init__(name)

        def command(self):
            if not self.args:
                print(self.usage)
                sys.exit(1)
            if self.options.repeatedly:
                assert self.args[0] == 'send-any-notifications'
            if self.args[0] == 'initdb':
                self._load_config()
                initdb()
                print('DB tables created')
            elif self.args[0] == 'send-any-notifications':
                self._load_config()
                initdb()
                send_any_notifications(self.options.repeatedly)
            elif self.args[0] == 'create-test-activity':
                self._load_config()
                object_id = self.args[1]
                create_test_activity(object_id)
            elif self.args[0] == 'delete-test-activity':
                self._load_config()
                delete_test_activity()
            else:
                self.parser.error('Unrecognized command')


if IS_CKAN_29_OR_HIGHER:
    import click

    @click.group(name='subscribe')
    @click.help_option('-h', '--help')
    @click.pass_context
    def subscribe(ctx):
        pass

    @subscribe.command('initdb', short_help="Initialize the the ckanext-subscribe's database table")
    def initd_cmd():
        initdb()

    @subscribe.command('send-any-notifications',
                       short_help="Check for activity and for any subscribers, send emails with the notifications.")
    @click.option('-r', '--repeatedly',
                  help='Does it repeatedly every 10s',
                  is_flag=True)
    def send_any_notifications_cmd(repeatedly):
        send_any_notifications(repeatedly)

    @subscribe.command('create-test-activity',
                       short_help="Create some activity for testing purposes, for a given existing object.")
    @click.argument('object_id')
    def create_test_activity_cmd(object_id):
        create_test_activity(object_id)

    @subscribe.command('delete-test-activity',
                       short_help="Delete any test activity (i.e. clean up after doing 'create-test-activity'). "
                                  "Works for test activity on all objects.")
    def delete_test_activity_cmd():
        delete_test_activity()
