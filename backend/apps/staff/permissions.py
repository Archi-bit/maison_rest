from rest_framework.permissions import BasePermission


def is_active_employee(user):
    return (
        user is not None
        and user.is_active
        and hasattr(user, "employee_profile")
    )


class IsEmployee(BasePermission):
    def has_permission(self, request, view):
        return is_active_employee(request.user)
