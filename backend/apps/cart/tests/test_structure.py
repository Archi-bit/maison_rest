from django.test import SimpleTestCase
from django.urls import reverse


class CartStructureTest(SimpleTestCase):
    def test_cart_route(self):
        self.assertEqual(reverse("guest-cart"), "/api/v1/cart/")
