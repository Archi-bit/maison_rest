from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
)
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from apps.cart.models import Cart, CartItem
from apps.cart.serializers import (
    CartItemQuantitySerializer,
    CartItemSerializer,
)
from apps.cart.services import (
    add_cart_item,
    create_guest_cart,
    delete_cart_item,
    get_cart_by_token,
    get_cart_total_price,
    get_cart_total_quantity,
    update_cart_item_quantity,
)


def _get_request_cart(request):
    try:
        return get_cart_by_token(request.headers.get("X-Cart-Token"))
    except DjangoValidationError as exc:
        raise ValidationError({"detail": exc.messages[0]}) from None
    except Cart.DoesNotExist:
        raise NotFound("Корзина с таким токеном не найдена.") from None


def _cart_response(cart, payload=None, response_status=status.HTTP_200_OK):
    return Response(
        payload,
        status=response_status,
        headers={
            "X-Cart-Token": str(cart.token),
            "Cache-Control": "no-store",
        },
    )


@api_view(["GET", "POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def guest_cart(request):
    token = request.headers.get("X-Cart-Token")
    response_status = status.HTTP_200_OK
    if request.method == "POST" and token is None:
        cart = create_guest_cart()
        response_status = status.HTTP_201_CREATED
    else:
        cart = _get_request_cart(request)

    return _cart_response(
        cart,
        {
            "total_quantity": get_cart_total_quantity(cart),
            "total_price": str(get_cart_total_price(cart)),
        },
        response_status=response_status,
    )


@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def cart_items(request):
    cart = _get_request_cart(request)
    serializer = CartItemSerializer(data=request.data)
    serializer.is_valid(raise_exception=True)
    try:
        item, created = add_cart_item(cart, **serializer.validated_data)
    except DjangoValidationError as exc:
        raise ValidationError(exc.message_dict) from None
    response_status = (
        status.HTTP_201_CREATED if created else status.HTTP_200_OK
    )
    return _cart_response(
        cart, CartItemSerializer(item).data, response_status=response_status
    )


@api_view(["PATCH", "DELETE"])
@authentication_classes([])
@permission_classes([AllowAny])
def cart_item_detail(request, item_id):
    cart = _get_request_cart(request)
    try:
        if request.method == "DELETE":
            delete_cart_item(cart, item_id)
            return _cart_response(
                cart, response_status=status.HTTP_204_NO_CONTENT
            )
        serializer = CartItemQuantitySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        item = update_cart_item_quantity(
            cart, item_id, **serializer.validated_data
        )
    except CartItem.DoesNotExist:
        raise NotFound("Позиция корзины не найдена.") from None
    return _cart_response(cart, CartItemSerializer(item).data)
