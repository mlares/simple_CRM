"""Fail-closed settings shared only by staging and production."""

import os

from django.core.exceptions import ImproperlyConfigured

from simple_crm.config.environment import (
    allowed_hosts,
    optional_bool,
    postgres_database_config,
    strong_secret,
)

SECRET_KEY = strong_secret()
ALLOWED_HOSTS = allowed_hosts()

if optional_bool("DJANGO_DEBUG") is True:
    raise ImproperlyConfigured("DJANGO_DEBUG must be false")
if optional_bool("DJANGO_SESSION_COOKIE_SECURE") is False:
    raise ImproperlyConfigured("DJANGO_SESSION_COOKIE_SECURE must be true")
if optional_bool("DJANGO_CSRF_COOKIE_SECURE") is False:
    raise ImproperlyConfigured("DJANGO_CSRF_COOKIE_SECURE must be true")

DEBUG = False
DATABASES = {"default": postgres_database_config()}

SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31_536_000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
SECURE_CROSS_ORIGIN_RESOURCE_POLICY = "same-origin"

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
X_FRAME_OPTIONS = "DENY"

# Trusting a forwarding header changes the security boundary, so it is opt-in.
if os.environ.get("DJANGO_TRUST_X_FORWARDED_PROTO", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
