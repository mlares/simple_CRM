import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from simple_crm.identity.models import IdentityProfile, Role, RoleAssignment


@pytest.mark.django_db
def test_notification_settings_page_preserves_spanish_labels_and_saves_digest() -> None:
    user = get_user_model().objects.create_user(
        username="notification-page", password="safe-pass"
    )
    profile = IdentityProfile.objects.get(user=user)
    RoleAssignment.objects.create(
        identity=profile, role=Role.objects.get(code="sales_representative")
    )
    client = Client()
    client.force_login(user)

    response = client.get(reverse("platform:notification_settings"))
    assert response.status_code == 200
    assert "Notificaciones" in response.content.decode()
    assert "Recibir resumen diario" in response.content.decode()

    saved = client.post(
        reverse("platform:notification_settings"),
        {"daily_digest_hour": "17"},
    )
    assert saved.status_code == 200
    profile.refresh_from_db()
    assert profile.notification_preferences.digest_enabled is False
    assert profile.notification_preferences.daily_digest_hour == 17
