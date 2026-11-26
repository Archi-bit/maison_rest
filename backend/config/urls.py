from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.views import api_health, health


urlpatterns = [
    path("health/", health, name="health"),
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="api-schema"),
    path(
        "api/swagger/",
        SpectacularSwaggerView.as_view(url_name="api-schema"),
        name="api-swagger",
    ),
    path("api/v1/health/", api_health, name="api-health"),
    path("api-auth/", include("rest_framework.urls")),
    path("api/v1/", include("apps.catalog.urls")),
    path("api/v1/", include("apps.cart.urls")),
    path("api/v1/", include("apps.staff.urls")),
]
