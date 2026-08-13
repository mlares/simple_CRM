"""Identity endpoint routing."""

from django.urls import path

from . import views

app_name = "identity"

urlpatterns = [
    path("local/login/", views.local_login, name="local_login"),
    path("oidc/start/", views.oidc_start, name="oidc_start"),
    path("oidc/callback/", views.oidc_callback, name="oidc_callback"),
    path("logout/", views.logout_view, name="logout"),
    path("me/", views.me, name="me"),
]
