from django.apps import AppConfig


class DataQualityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "simple_crm.data_quality"
    label = "simple_crm_data_quality"
    verbose_name = "Calidad de datos"
