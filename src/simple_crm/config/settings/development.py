"""Local PostgreSQL development settings; never use these for a deployment."""

from simple_crm.config.environment import postgres_database_config

from .base import *  # noqa: F403

SECRET_KEY = "development-only-not-a-secret-simple-crm-key"
DEBUG = True
ALLOWED_HOSTS = ["127.0.0.1", "localhost"]

DATABASES = {"default": postgres_database_config()}

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
