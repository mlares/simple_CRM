from django.apps import AppConfig


class PlatformConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "simple_crm.platform"
    label = "simple_crm_platform"
    verbose_name = "Plataforma"
