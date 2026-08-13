from pathlib import Path

import pytest
from django.test import Client

PLATFORM_TEMPLATES = Path("src/simple_crm/platform/templates/platform")
CRITICAL_TEMPLATES = (
    "home.html",
    "today.html",
    "lead_detail.html",
    "search.html",
    "segments.html",
    "reports.html",
    "notifications.html",
    "help.html",
)


def test_critical_templates_have_shared_keyboard_and_document_contract() -> None:
    for filename in CRITICAL_TEMPLATES:
        body = (PLATFORM_TEMPLATES / filename).read_text(encoding="utf-8")
        assert '<html lang="es-AR">' in body, filename
        assert 'name="viewport"' in body, filename
        assert 'name="description"' in body, filename
        assert "platform/accessibility.css" in body, filename
        assert 'class="skip-link"' in body, filename
        assert 'id="contenido"' in body, filename


def test_accessibility_styles_define_focus_visibility_and_touch_size() -> None:
    css = Path("src/simple_crm/platform/static/platform/accessibility.css").read_text(
        encoding="utf-8"
    )
    assert ":focus-visible" in css
    assert "min-height: 2.75rem" in css
    assert ".skip-link:focus" in css
    assert "@media" in css


def test_forms_keep_native_submission_and_visible_labels() -> None:
    for filename in (
        "search.html",
        "segments.html",
        "reports.html",
        "notifications.html",
    ):
        body = (PLATFORM_TEMPLATES / filename).read_text(encoding="utf-8")
        assert "<form" in body, filename
        assert "method=" in body, filename
        assert "hx-" not in body, filename
    assert '<label class="form-label" for="stage">Etapa</label>' in (
        PLATFORM_TEMPLATES / "segments.html"
    ).read_text(encoding="utf-8")
    assert '<label class="form-label" for="from">Desde</label>' in (
        PLATFORM_TEMPLATES / "reports.html"
    ).read_text(encoding="utf-8")


def test_local_login_has_error_region_and_accessible_label_path() -> None:
    body = Path(
        "src/simple_crm/identity/templates/identity/local_login.html"
    ).read_text(encoding="utf-8")
    assert 'id="contenido"' in body
    assert 'role="alert"' in body
    assert "field.label_tag" in body
    assert "Saltar al contenido principal" in body


@pytest.mark.django_db
def test_help_page_is_public_spanish_guide_with_contextual_links() -> None:
    response = Client().get("/ayuda/")

    assert response.status_code == 200
    body = response.content.decode()
    assert "Cómo trabajamos" in body
    assert "Registrar un contacto" in body
    assert "Buscar y guardar vistas" in body
    assert "Calidad de datos" in body
    assert "Glosario" in body
    assert "/buscar/" in body
    assert "/segmentos/" in body
    assert "cdn.jsdelivr.net" not in body


@pytest.mark.django_db
def test_home_exposes_help_without_javascript_dependency() -> None:
    response = Client().get("/")

    assert response.status_code == 200
    body = response.content.decode()
    assert 'href="/ayuda/"' in body
    assert 'href="/today/"' in body
    assert 'href="/ayuda/"' in body
