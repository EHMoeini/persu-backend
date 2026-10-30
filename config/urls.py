from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.common.urls")),
]

handler404 = "apps.common.handlers.handler404"
handler500 = "apps.common.handlers.handler500"
