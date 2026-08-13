from typing import Any

from django.apps import AppConfig
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save


def ensure_identity_profile(sender: type[Any], instance: Any, **kwargs: Any) -> None:
    from .models import IdentityProfile

    IdentityProfile.objects.get_or_create(user=instance)


class IdentityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "simple_crm.identity"
    label = "simple_crm_identity"
    verbose_name = "Identidad"

    def ready(self) -> None:
        post_save.connect(
            ensure_identity_profile,
            sender=get_user_model(),
            dispatch_uid="simple_crm.identity.ensure_identity_profile",
        )
