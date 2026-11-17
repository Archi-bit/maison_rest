from django.contrib import admin
from django.urls import include, path

from config.views import api_health, health


urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("api/v1/health/", api_health, name="api-health"),
    path("api-auth/", include("rest_framework.urls")),
    path("api/v1/", include("apps.catalog.urls")),
    path("api/v1/", include("apps.cart.urls")),
]
