from django.apps import AppConfig
from django.db.models.signals import post_migrate


def ensure_data_stewards_group(**kwargs: object) -> None:
    """Grant the temporary, catalog-only maintenance boundary idempotently."""
    from django.contrib.auth.models import Group, Permission

    catalog_models = {
        "campaign",
        "leadstatus",
        "interactionchannel",
        "interactionoutcome",
        "specialty",
        "country",
        "province",
        "locality",
    }
    permissions = Permission.objects.filter(
        content_type__app_label="simple_crm_crm",
        content_type__model__in=catalog_models,
        codename__regex=r"^(add|change|view)_",
    )
    group, created = Group.objects.get_or_create(name="Data Stewards")
    group.permissions.set(permissions)


class CrmConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "simple_crm.crm"
    label = "simple_crm_crm"
    verbose_name = "CRM"

    def ready(self) -> None:
        post_migrate.connect(
            ensure_data_stewards_group,
            sender=self,
            dispatch_uid="simple_crm.crm.ensure_data_stewards_group",
        )
