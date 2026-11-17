from decimal import Decimal
from uuid import UUID

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from apps.cart.models import Cart, CartItem

MAX_ITEM_QUANTITY = 2_147_483_647


def create_guest_cart():
    return Cart.objects.create()


def validate_cart_token(token):
    if token is None or token == "":
        raise ValidationError("Передайте заголовок X-Cart-Token.")
    if isinstance(token, UUID):
        return token
    try:
        return UUID(token)
    except (ValueError, TypeError, AttributeError):
        raise ValidationError(
            "Некорректный X-Cart-Token: ожидается UUID."
        ) from None


def get_cart_by_token(token):
    return Cart.objects.get(token=validate_cart_token(token))


def get_cart_items(cart):
    return cart.items.select_related("dish").order_by("pk")


def get_cart_total_quantity(cart):
    return cart.items.aggregate(total=Sum("quantity", default=0))["total"]


def get_cart_total_price(cart):
    return sum(
        (item.dish.price * item.quantity for item in get_cart_items(cart)),
        Decimal("0.00"),
    )


@transaction.atomic
def add_cart_item(cart, dish, quantity):
    cart = Cart.objects.select_for_update().get(pk=cart.pk)
    item, created = CartItem.objects.get_or_create(
        cart=cart, dish=dish, defaults={"quantity": quantity}
    )
    if not created:
        new_quantity = item.quantity + quantity
        if new_quantity > MAX_ITEM_QUANTITY:
            raise ValidationError(
                {"quantity": "Превышено максимальное количество товара."}
            )
        item.quantity = new_quantity
        item.save(update_fields=["quantity"])
    cart.save(update_fields=["updated_at"])
    return item, created


@transaction.atomic
def update_cart_item_quantity(cart, item_id, quantity):
    cart = Cart.objects.select_for_update().get(pk=cart.pk)
    item = CartItem.objects.get(cart=cart, pk=item_id)
    item.quantity = quantity
    item.save(update_fields=["quantity"])
    cart.save(update_fields=["updated_at"])
    return item


@transaction.atomic
def delete_cart_item(cart, item_id):
    cart = Cart.objects.select_for_update().get(pk=cart.pk)
    item = CartItem.objects.get(cart=cart, pk=item_id)
    item.delete()
    cart.save(update_fields=["updated_at"])
