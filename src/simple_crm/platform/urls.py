"""Public platform URLs."""

from django.urls import path

from . import views

app_name = "platform"

urlpatterns = [
    path("", views.home, name="home"),
    path("ayuda/", views.help_page, name="help"),
    path("today/", views.today, name="today"),
    path("buscar/", views.search_page, name="search"),
    path("segmentos/", views.segments_page, name="segments"),
    path("informes/", views.reports_page, name="reports"),
    path(
        "configuracion/notificaciones/",
        views.notification_settings_page,
        name="notification_settings",
    ),
    path("leads/<str:lead_number>/", views.lead_detail_page, name="lead_detail"),
    path("health/live/", views.liveness, name="liveness"),
    path("health/ready/", views.readiness, name="readiness"),
    path("health/metrics/", views.metrics, name="metrics"),
]
