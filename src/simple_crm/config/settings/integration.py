"""Dedicated PostgreSQL 18 settings for integration acceptance evidence."""

from simple_crm.config.environment import postgres_database_config

from .base import *  # noqa: F403

SECRET_KEY = "integration-only-secret-not-for-any-deployment"
DEBUG = False
ALLOWED_HOSTS = ["localhost", "testserver"]
DATABASES = {"default": postgres_database_config()}
ENVIRONMENT_NAME = "integration"
