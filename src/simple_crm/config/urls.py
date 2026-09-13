"""Root URL composition for Simple CRM."""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("auth/", include("simple_crm.identity.urls")),
    path("", include("simple_crm.platform.urls")),
]
