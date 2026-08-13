import pytest
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import Client, override_settings

from simple_crm.data_quality.services import safe_upload_filename


def test_security_headers_are_present_and_csp_is_self_hosted() -> None:
    response = Client().get("/")

    assert response.status_code == 200
    assert "default-src 'self'" in response["Content-Security-Policy"]
    assert "script-src 'self'" in response["Content-Security-Policy"]
    assert "frame-ancestors 'none'" in response["Content-Security-Policy"]
    assert response["Permissions-Policy"] == (
        "camera=(), geolocation=(), microphone=(), payment=()"
    )


def test_production_settings_require_transport_and_privacy_headers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv(
        "DJANGO_SECRET_KEY",
        "P9!simple-CRM-production-check-key_7xQ2vN8zL4mR6tY1wK3cB5",
    )
    monkeypatch.setenv("DJANGO_ALLOWED_HOSTS", "crm.example.com")
    monkeypatch.setenv(
        "DATABASE_URL", "postgresql://crm:local-check@localhost:5432/crm"
    )
    monkeypatch.setenv("DJANGO_DEBUG", "false")
    monkeypatch.setenv("DJANGO_SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("DJANGO_CSRF_COOKIE_SECURE", "true")
    from simple_crm.config.settings import _deployment

    assert _deployment.SECURE_SSL_REDIRECT is True
    assert _deployment.SECURE_HSTS_SECONDS >= 31_536_000
    assert _deployment.SESSION_COOKIE_SECURE is True
    assert _deployment.SESSION_COOKIE_HTTPONLY is True
    assert _deployment.CSRF_COOKIE_SECURE is True
    assert _deployment.X_FRAME_OPTIONS == "DENY"
    assert _deployment.SECURE_REFERRER_POLICY == "same-origin"
    assert _deployment.SECURE_CROSS_ORIGIN_OPENER_POLICY == "same-origin"


@pytest.mark.django_db
def test_rate_limit_returns_generic_429_without_sensitive_details() -> None:
    cache.clear()
    with override_settings(RATE_LIMIT_RULES={"/": (1, 60)}):
        client = Client()
        assert client.get("/").status_code == 200
        response = client.get("/")

    assert response.status_code == 429
    assert response["Retry-After"] == "60"
    assert "secret" not in response.content.decode().lower()
    assert "stack" not in response.content.decode().lower()
    cache.clear()


def test_upload_filename_is_bounded_and_path_safe() -> None:
    safe = safe_upload_filename("../../Ventas Clínicas 2026.xlsx")

    assert safe == "Ventas_Clinicas_2026.xlsx"
    assert "/" not in safe
    assert "\\" not in safe
    assert len(safe) <= 120
    with pytest.raises(ValidationError, match="nombre"):
        safe_upload_filename("../../secreto.csv")
