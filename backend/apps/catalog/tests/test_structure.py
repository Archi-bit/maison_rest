from django.test import SimpleTestCase


class CatalogStructureTest(SimpleTestCase):
    def test_app_imports(self):
        from apps.catalog import urls
        self.assertEqual(urls.urlpatterns, [])
