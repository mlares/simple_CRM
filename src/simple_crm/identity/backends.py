"""Authentication backend that honors CRM offboarding state."""

from __future__ import annotations

from typing import Any

from django.contrib.auth.backends import ModelBackend

from .models import IdentityProfile


class IdentityAuthenticationBackend(ModelBackend):
    """Django password authentication with centralized identity disablement."""

    def user_can_authenticate(self, user: Any) -> bool:
        if not super().user_can_authenticate(user):
            return False
        try:
            profile = user.identity_profile
        except IdentityProfile.DoesNotExist:
            profile = IdentityProfile.objects.create(user=user)
        return profile.disabled_at is None
