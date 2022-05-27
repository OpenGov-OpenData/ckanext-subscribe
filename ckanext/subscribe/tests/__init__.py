from ckanext.subscribe import model as subscribe_model
from ckan.tests.helpers import FunctionalTestBase
from ckanext.subscribe.constants import IS_CKAN_29_OR_HIGHER


class SubscribeBase(FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(SubscribeBase, cls).setup_class()
        subscribe_model.setup()
        del cls._test_app
        cls.app = cls._get_test_app()

    def setup(self):
        if IS_CKAN_29_OR_HIGHER:
            self.follow_kw = dict(follow_redirects=False)
        else:
            self.follow_kw = {}
