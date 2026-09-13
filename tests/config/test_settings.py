import os
import subprocess
import sys
from pathlib import Path

import pytest
from django.conf import settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PRODUCTION_ENVIRONMENT = {
    "DJANGO_SECRET_KEY": "P9!simple-CRM-production-check-key_7xQ2vN8zL4mR6tY1wK3cB5",
    "DJANGO_ALLOWED_HOSTS": "crm.example.com",
    "DATABASE_URL": "postgresql://crm:local-check@localhost:5432/crm",
    "DJANGO_DEBUG": "false",
    "DJANGO_SESSION_COOKIE_SECURE": "true",
    "DJANGO_CSRF_COOKIE_SECURE": "true",
}


def _isolated_settings_import(
    module: str,
    overrides: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    environment = os.environ.copy()
    for name in tuple(environment):
        if name.startswith("DJANGO_") or name == "DATABASE_URL":
            environment.pop(name)
    environment.update(overrides or {})
    source_path = str(PROJECT_ROOT / "src")
    inherited_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        source_path
        if not inherited_pythonpath
        else f"{source_path}{os.pathsep}{inherited_pythonpath}"
    )
    code = (
        "import importlib; "
        f"settings = importlib.import_module({module!r}); "
        "print(settings.DEBUG, settings.LANGUAGE_CODE, settings.TIME_ZONE)"
    )
    return subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def test_shared_locale_and_timezone_contract() -> None:
    assert settings.LANGUAGE_CODE == "es-ar"
    assert settings.TIME_ZONE == "America/Argentina/Cordoba"
    assert settings.USE_TZ is True


@pytest.mark.parametrize(
    "module",
    [
        "simple_crm.config.settings.development",
        "simple_crm.config.settings.integration",
        "simple_crm.config.settings.staging",
        "simple_crm.config.settings.production",
    ],
)
def test_postgres_settings_fail_closed_without_database_url(module: str) -> None:
    environment = (
        {
            name: value
            for name, value in PRODUCTION_ENVIRONMENT.items()
            if name != "DATABASE_URL"
        }
        if module.endswith(("staging", "production"))
        else {}
    )
    result = _isolated_settings_import(module, environment)

    assert result.returncode != 0
    assert "DATABASE_URL is required" in result.stderr


@pytest.mark.parametrize(
    ("module", "environment", "expected_prefix"),
    [
        (
            "simple_crm.config.settings.development",
            PRODUCTION_ENVIRONMENT,
            "True es-ar",
        ),
        ("simple_crm.config.settings.test", {}, "False es-ar"),
        (
            "simple_crm.config.settings.integration",
            PRODUCTION_ENVIRONMENT,
            "False es-ar",
        ),
        (
            "simple_crm.config.settings.staging",
            PRODUCTION_ENVIRONMENT,
            "False es-ar",
        ),
        (
            "simple_crm.config.settings.production",
            PRODUCTION_ENVIRONMENT,
            "False es-ar",
        ),
    ],
)
def test_each_settings_variant_imports_in_isolation(
    module: str,
    environment: dict[str, str],
    expected_prefix: str,
) -> None:
    result = _isolated_settings_import(module, environment)

    assert result.returncode == 0, result.stderr
    assert result.stdout.startswith(expected_prefix)


@pytest.mark.parametrize(
    ("overrides", "expected_variable", "sensitive_marker"),
    [
        ({}, "DJANGO_SECRET_KEY", ""),
        (
            {
                name: value
                for name, value in PRODUCTION_ENVIRONMENT.items()
                if name != "DJANGO_ALLOWED_HOSTS"
            },
            "DJANGO_ALLOWED_HOSTS",
            "",
        ),
        (
            {
                name: value
                for name, value in PRODUCTION_ENVIRONMENT.items()
                if name != "DATABASE_URL"
            },
            "DATABASE_URL",
            "",
        ),
        (
            {**PRODUCTION_ENVIRONMENT, "DJANGO_SECRET_KEY": "short-leaky-secret"},
            "DJANGO_SECRET_KEY",
            "short-leaky-secret",
        ),
        (
            {**PRODUCTION_ENVIRONMENT, "DJANGO_DEBUG": "YES"},
            "DJANGO_DEBUG",
            "YES",
        ),
        (
            {**PRODUCTION_ENVIRONMENT, "DJANGO_SESSION_COOKIE_SECURE": "false"},
            "DJANGO_SESSION_COOKIE_SECURE",
            "",
        ),
        (
            {**PRODUCTION_ENVIRONMENT, "DJANGO_CSRF_COOKIE_SECURE": "0"},
            "DJANGO_CSRF_COOKIE_SECURE",
            "",
        ),
        (
            {**PRODUCTION_ENVIRONMENT, "DJANGO_ALLOWED_HOSTS": "*"},
            "DJANGO_ALLOWED_HOSTS",
            "",
        ),
        (
            {
                **PRODUCTION_ENVIRONMENT,
                "DJANGO_ALLOWED_HOSTS": "https://leaky-host.example/private",
            },
            "DJANGO_ALLOWED_HOSTS",
            "leaky-host.example",
        ),
        (
            {
                **PRODUCTION_ENVIRONMENT,
                "DATABASE_URL": "sqlite:///leaky-database-marker.sqlite3",
            },
            "DATABASE_URL",
            "leaky-database-marker",
        ),
        (
            {**PRODUCTION_ENVIRONMENT, "DATABASE_URL": "not-a-database-url"},
            "DATABASE_URL",
            "not-a-database-url",
        ),
        (
            {
                **PRODUCTION_ENVIRONMENT,
                "DATABASE_URL": (
                    "postgresql://crm:password@localhost:port-leak-marker/crm"
                ),
            },
            "DATABASE_URL",
            "port-leak-marker",
        ),
    ],
)
def test_production_rejects_unsafe_configuration_without_leaking_values(
    overrides: dict[str, str],
    expected_variable: str,
    sensitive_marker: str,
) -> None:
    result = _isolated_settings_import(
        "simple_crm.config.settings.production", overrides
    )

    assert result.returncode != 0
    assert expected_variable in result.stderr
    if sensitive_marker:
        assert sensitive_marker not in result.stderr
