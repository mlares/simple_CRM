"""Strict environment parsing shared by deployed settings."""

import os
import re
from collections.abc import Mapping
from typing import Any
from urllib.parse import urlsplit

import dj_database_url
from django.core.exceptions import ImproperlyConfigured

_TRUE_VALUES = frozenset({"1", "true", "yes", "on"})
_FALSE_VALUES = frozenset({"0", "false", "no", "off"})
_HOST_PATTERN = re.compile(
    r"^(?:localhost|(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)(?:\.(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?))*)$",
    re.IGNORECASE,
)


def required_value(name: str, environment: Mapping[str, str] | None = None) -> str:
    """Return a non-empty environment value without exposing it in errors."""
    source = os.environ if environment is None else environment
    value = source.get(name, "").strip()
    if not value:
        raise ImproperlyConfigured(f"{name} is required")
    return value


def optional_bool(
    name: str, environment: Mapping[str, str] | None = None
) -> bool | None:
    """Parse an optional boolean, rejecting ambiguous values."""
    source = os.environ if environment is None else environment
    raw_value = source.get(name)
    if raw_value is None:
        return None
    value = raw_value.strip().lower()
    if value in _TRUE_VALUES:
        return True
    if value in _FALSE_VALUES:
        return False
    raise ImproperlyConfigured(f"{name} must be a boolean")


def strong_secret(environment: Mapping[str, str] | None = None) -> str:
    """Require a production-grade Django secret key."""
    secret = required_value("DJANGO_SECRET_KEY", environment)
    lowered = secret.lower()
    if (
        len(secret) < 50
        or len(set(secret)) < 5
        or lowered.startswith("django-insecure-")
        or "replace" in lowered
        or "placeholder" in lowered
    ):
        raise ImproperlyConfigured("DJANGO_SECRET_KEY is not strong enough")
    return secret


def allowed_hosts(environment: Mapping[str, str] | None = None) -> list[str]:
    """Parse exact deployed hosts; wildcard and URL-shaped entries are unsafe."""
    raw_hosts = required_value("DJANGO_ALLOWED_HOSTS", environment)
    hosts = [host.strip() for host in raw_hosts.split(",")]
    if any(
        not host
        or "*" in host
        or host.startswith(".")
        or "://" in host
        or "/" in host
        or not _HOST_PATTERN.fullmatch(host)
        for host in hosts
    ):
        raise ImproperlyConfigured("DJANGO_ALLOWED_HOSTS contains an invalid host")
    return hosts


def postgres_database_url(environment: Mapping[str, str] | None = None) -> str:
    """Require a PostgreSQL URL while keeping credentials out of exceptions."""
    database_url = required_value("DATABASE_URL", environment)
    try:
        parsed = urlsplit(database_url)
        parsed.port
    except ValueError:
        # urllib's parsing error may include the raw port text, so suppress the
        # exception chain before this reaches startup stderr.
        raise ImproperlyConfigured("DATABASE_URL is invalid") from None
    if (
        parsed.scheme.lower() not in {"postgres", "postgresql"}
        or not parsed.hostname
        or not parsed.path.lstrip("/")
    ):
        raise ImproperlyConfigured("DATABASE_URL must be a PostgreSQL URL")
    return database_url


def postgres_database_config(
    environment: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Build the only supported deployed database configuration.

    The connection lifetime is intentionally finite and Django validates a
    reused connection before serving a request.  Atomic requests ensure that
    later web writes share a well-defined transaction boundary.
    """
    database_url = postgres_database_url(environment)
    try:
        configuration = dj_database_url.parse(
            database_url,
            conn_max_age=60,
            conn_health_checks=True,
        )
    except (KeyError, TypeError, ValueError):
        raise ImproperlyConfigured("DATABASE_URL is invalid") from None

    if configuration.get("ENGINE") != "django.db.backends.postgresql":
        raise ImproperlyConfigured("DATABASE_URL must be a PostgreSQL URL")

    configuration["ATOMIC_REQUESTS"] = True
    configuration["CONN_MAX_AGE"] = 60
    configuration["CONN_HEALTH_CHECKS"] = True
    return dict(configuration)
