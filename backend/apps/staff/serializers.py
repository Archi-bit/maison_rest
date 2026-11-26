from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import (
    TokenObtainPairSerializer,
    TokenRefreshSerializer,
)

from apps.staff.models import EmployeeProfile


class EmployeeProfileSerializer(serializers.ModelSerializer):
    first_name = serializers.CharField(
        source="user.first_name", read_only=True
    )
    last_name = serializers.CharField(source="user.last_name", read_only=True)
    username = serializers.CharField(source="user.username", read_only=True)

    class Meta:
        model = EmployeeProfile
        fields = ("id", "first_name", "last_name", "username", "role")
        read_only_fields = fields


class StaffLoginSerializer(TokenObtainPairSerializer):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password"].trim_whitespace = False


class StaffTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        try:
            return super().validate(attrs)
        except get_user_model().DoesNotExist as exc:
            # Simple JWT looks up the account even if it has been deleted.
            raise AuthenticationFailed(
                self.error_messages["no_active_account"], "no_active_account"
            ) from exc
