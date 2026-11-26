from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.generics import RetrieveAPIView
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from apps.staff.permissions import IsEmployee
from apps.staff.serializers import (
    EmployeeProfileSerializer,
    StaffLoginSerializer,
    StaffTokenRefreshSerializer,
)


@extend_schema(
    tags=["Сотрудники"],
    summary="Вход сотрудника",
    request=TokenObtainPairSerializer,
    responses={
        200: TokenObtainPairSerializer,
        400: OpenApiResponse(description="Не передан логин или пароль."),
        401: OpenApiResponse(description="Вход отклонён."),
    },
)
@method_decorator(never_cache, name="dispatch")
class StaffLoginView(TokenObtainPairView):
    serializer_class = StaffLoginSerializer


@extend_schema(
    tags=["Сотрудники"],
    summary="Обновление access-токена",
    request=TokenRefreshSerializer,
    responses={
        200: TokenRefreshSerializer,
        400: OpenApiResponse(description="Не передан refresh-токен."),
        401: OpenApiResponse(description="Обновление токена отклонено."),
    },
)
@method_decorator(never_cache, name="dispatch")
class StaffTokenRefreshView(TokenRefreshView):
    serializer_class = StaffTokenRefreshSerializer


@extend_schema(
    tags=["Сотрудники"],
    summary="Профиль текущего сотрудника",
    responses={
        200: EmployeeProfileSerializer,
        401: OpenApiResponse(description="Требуется действующий JWT."),
        403: OpenApiResponse(description="Профиль сотрудника недоступен."),
    },
)
@method_decorator(never_cache, name="dispatch")
class StaffMeView(RetrieveAPIView):
    authentication_classes = (JWTAuthentication,)
    permission_classes = (IsEmployee,)
    serializer_class = EmployeeProfileSerializer

    def get_object(self):
        return self.request.user.employee_profile
