from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "",
        RedirectView.as_view(pattern_name="swagger-ui", permanent=False),
        name="home",
    ),
    path(
        "docs/",
        RedirectView.as_view(pattern_name="swagger-ui", permanent=False),
    ),
    path(
        "swagger/",
        RedirectView.as_view(pattern_name="swagger-ui", permanent=False),
    ),
    path(
        "redoc/",
        RedirectView.as_view(pattern_name="redoc", permanent=False),
    ),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
    path("auth/", include("apps.accounts.auth_urls")),
    path("api/", include("apps.resources.urls")),
    path("", include("apps.common.urls")),
]

handler404 = "apps.common.handlers.handler404"
handler500 = "apps.common.handlers.handler500"
