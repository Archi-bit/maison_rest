from decimal import Decimal
from uuid import UUID, uuid4

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase

from apps.cart.models import Cart, CartItem
from apps.cart.services import (
    create_guest_cart,
    get_cart_by_token,
    get_cart_items,
    get_cart_total_price,
    get_cart_total_quantity,
    validate_cart_token,
)
from apps.catalog.models import Dish


class CartTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.cart = create_guest_cart()
        cls.dish = Dish.objects.create(name="Суп", price=Decimal("125.10"))

    def test_creates_unique_tokens_and_timestamps(self):
        another_cart = create_guest_cart()
        self.assertIsInstance(self.cart.token, UUID)
        self.assertEqual(self.cart.token.version, 4)
        self.assertNotEqual(self.cart.token, another_cart.token)
        self.assertIsNotNone(self.cart.created_at)
        self.assertIsNotNone(self.cart.updated_at)
        self.assertLessEqual(self.cart.created_at, self.cart.updated_at)

    def test_token_is_unique_in_database(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Cart.objects.create(token=self.cart.token)

    def test_gets_cart_by_token(self):
        self.assertEqual(get_cart_by_token(str(self.cart.token)), self.cart)
        self.assertEqual(get_cart_by_token(self.cart.token), self.cart)

    def test_rejects_invalid_tokens_without_creating_cart(self):
        for token in (None, "", "not-a-uuid", "123", 123):
            with self.subTest(token=token), self.assertRaises(ValidationError):
                validate_cart_token(token)
        self.assertEqual(Cart.objects.count(), 1)

    def test_unknown_token_does_not_create_cart(self):
        with self.assertRaises(Cart.DoesNotExist):
            get_cart_by_token(str(uuid4()))
        self.assertEqual(Cart.objects.count(), 1)

    def test_items_include_dishes_without_extra_queries(self):
        item = CartItem.objects.create(
            cart=self.cart, dish=self.dish, quantity=2
        )
        with self.assertNumQueries(1):
            items = list(get_cart_items(self.cart))
            self.assertEqual(items, [item])
            self.assertEqual(items[0].dish, self.dish)

    def test_dish_cannot_be_duplicated_in_cart(self):
        CartItem.objects.create(cart=self.cart, dish=self.dish)
        with self.assertRaises(IntegrityError), transaction.atomic():
            CartItem.objects.create(cart=self.cart, dish=self.dish)

    def test_dish_can_belong_to_different_carts(self):
        CartItem.objects.create(cart=self.cart, dish=self.dish)
        another_cart = create_guest_cart()
        CartItem.objects.create(cart=another_cart, dish=self.dish)
        self.assertEqual(CartItem.objects.count(), 2)

    def test_quantity_must_be_at_least_one(self):
        for quantity in (0, -1):
            with self.subTest(quantity=quantity):
                item = CartItem(
                    cart=self.cart, dish=self.dish, quantity=quantity
                )
                with self.assertRaises(ValidationError):
                    item.full_clean()
                with self.assertRaises(IntegrityError), transaction.atomic():
                    item.save()

    def test_deleting_cart_deletes_items_and_preserves_dish(self):
        CartItem.objects.create(cart=self.cart, dish=self.dish)
        self.cart.delete()
        self.assertFalse(CartItem.objects.exists())
        self.assertTrue(Dish.objects.filter(pk=self.dish.pk).exists())

    def test_empty_totals(self):
        self.assertEqual(get_cart_total_quantity(self.cart), 0)
        total_price = get_cart_total_price(self.cart)
        self.assertIsInstance(total_price, Decimal)
        self.assertEqual(total_price, Decimal("0.00"))

    def test_totals_use_current_dish_prices_and_only_this_cart(self):
        dessert = Dish.objects.create(name="Десерт", price=Decimal("90.25"))
        CartItem.objects.create(cart=self.cart, dish=self.dish, quantity=3)
        CartItem.objects.create(cart=self.cart, dish=dessert, quantity=2)
        CartItem.objects.create(
            cart=create_guest_cart(), dish=dessert, quantity=10
        )
        self.assertEqual(get_cart_total_quantity(self.cart), 5)
        self.assertEqual(get_cart_total_price(self.cart), Decimal("555.80"))
        self.dish.price = Decimal("130.15")
        self.dish.save(update_fields=["price"])
        self.assertEqual(get_cart_total_price(self.cart), Decimal("570.95"))
