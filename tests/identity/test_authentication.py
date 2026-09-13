from unittest.mock import patch

import pytest
from django.contrib.auth import authenticate, get_user_model
from django.test import Client, override_settings
from django.urls import reverse

from simple_crm.identity.models import IdentityProfile


@pytest.mark.django_db
def test_disabled_identity_cannot_authenticate_and_existing_session_is_flushed(
    client: Client,
) -> None:
    user = get_user_model().objects.create_user(
        username="offboarded", password="safe-password"
    )
    profile = IdentityProfile.objects.get(user=user)
    client.force_login(user)
    profile.disable("Baja solicitada por RR. HH.")

    assert authenticate(username="offboarded", password="safe-password") is None
    response = client.get(reverse("identity:me"))
    assert response.status_code == 302
    assert "local/login" in response["Location"]


@pytest.mark.django_db
def test_local_password_fallback_is_hidden_unless_explicitly_enabled(
    client: Client,
) -> None:
    response = client.get(reverse("identity:local_login"))
    assert response.status_code == 404

    with override_settings(LOCAL_AUTH_FALLBACK_ENABLED=True):
        response = client.get(reverse("identity:local_login"))
    assert response.status_code == 200
    assert "acceso local" in response.content.decode()


@pytest.mark.django_db
def test_local_login_rejects_external_next_redirect() -> None:
    user = get_user_model().objects.create_user(
        username="safe-next", password="safe-password"
    )
    with override_settings(LOCAL_AUTH_FALLBACK_ENABLED=True):
        response = Client().post(
            reverse("identity:local_login"),
            {
                "username": user.username,
                "password": "safe-password",
                "next": "https://evil.example/phishing",
            },
        )

    assert response.status_code == 302
    assert response["Location"] == "/"


@pytest.mark.django_db
def test_oidc_start_uses_state_nonce_and_pkce_without_provider_network(
    client: Client,
) -> None:
    with (
        override_settings(
            OIDC_ISSUER_URL="https://idp.example.test",
            OIDC_CLIENT_ID="crm-client",
            OIDC_CLIENT_SECRET="not-in-source",
            OIDC_REDIRECT_URI="https://crm.example.test/auth/oidc/callback/",
        ),
        patch(
            "simple_crm.identity.views.authorization_url",
            return_value="https://idp.example.test/authorize",
        ) as authorization,
    ):
        response = client.get(reverse("identity:oidc_start"))

    assert response.status_code == 302
    assert response["Location"] == "https://idp.example.test/authorize"
    session = client.session
    assert session["oidc_state"]
    assert session["oidc_nonce"]
    assert session["oidc_verifier"]
    authorization.assert_called_once()


def test_oidc_callback_rejects_state_replay(client: Client) -> None:
    response = client.get(
        reverse("identity:oidc_callback"), {"state": "wrong", "code": "code"}
    )
    assert response.status_code == 400
