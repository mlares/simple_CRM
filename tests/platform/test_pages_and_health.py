from unittest.mock import patch

import pytest
from django.db import DatabaseError
from django.test import Client

from simple_crm.platform.views import home


def test_home_page_is_semantic_spanish_html(client: Client) -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith("text/html")
    body = response.content.decode()
    assert '<html lang="es-AR">' in body
    assert "CRM de Ventas" in body
    assert "equipo comercial" in body
    assert "<main" in body
    assert "https://" not in body
    assert "vendor/bootstrap/5.3.8/bootstrap.min.css" in body
    assert "vendor/htmx/2.0.10/htmx.min.js" in body
    assert "cdn.jsdelivr.net" not in body


def test_home_page_is_not_wrapped_in_a_database_transaction() -> None:
    assert getattr(home, "_non_atomic_requests") == {"default"}


def test_liveness_is_dependency_independent_and_not_cached(client: Client) -> None:
    with patch(
        "simple_crm.platform.views.connection.cursor",
        side_effect=DatabaseError("database must not be touched"),
    ) as cursor:
        response = client.get("/health/live/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "no-store" in response.headers["Cache-Control"]
    cursor.assert_not_called()


@pytest.mark.django_db
def test_liveness_remains_dependency_independent_with_atomic_requests(
    client: Client,
) -> None:
    with patch(
        "simple_crm.platform.views.connection.ensure_connection",
        side_effect=DatabaseError("liveness must not connect"),
    ):
        response = client.get("/health/live/")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.django_db
def test_readiness_succeeds_when_database_is_available(client: Client) -> None:
    response = client.get("/health/ready/")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    assert "no-store" in response.headers["Cache-Control"]


def test_readiness_is_generic_when_database_is_unavailable(client: Client) -> None:
    diagnostic = "postgresql://leaked-user:leaked-password@internal-db/crm"
    with patch(
        "simple_crm.platform.views.connection.cursor",
        side_effect=DatabaseError(diagnostic),
    ):
        readiness_response = client.get("/health/ready/")
        liveness_response = client.get("/health/live/")

    assert readiness_response.status_code == 503
    assert readiness_response.json() == {"status": "unavailable"}
    assert "no-store" in readiness_response.headers["Cache-Control"]
    assert diagnostic not in readiness_response.content.decode()
    assert "leaked-password" not in readiness_response.content.decode()
    assert liveness_response.status_code == 200
    assert liveness_response.json() == {"status": "ok"}
