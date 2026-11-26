from django.urls import path

from apps.staff.views import StaffLoginView, StaffMeView, StaffTokenRefreshView


app_name = "staff"

urlpatterns = [
    path("staff/login/", StaffLoginView.as_view(), name="login"),
    path(
        "staff/token/refresh/",
        StaffTokenRefreshView.as_view(),
        name="token-refresh",
    ),
    path("staff/me/", StaffMeView.as_view(), name="me"),
]
