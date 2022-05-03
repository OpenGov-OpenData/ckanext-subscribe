from ckanext.subscribe import model as subscribe_model
from ckan.tests.helpers import FunctionalTestBase


class SubscribeBase(FunctionalTestBase):
    @classmethod
    def setup_class(cls):
        super(SubscribeBase, cls).setup_class()
        subscribe_model.setup()
        del cls._test_app
        cls.app = cls._get_test_app()

    def setup(self):
        pass
