"""Settings shared by every Simple CRM environment."""

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
BASE_DIR = PROJECT_ROOT

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "simple_crm.crm.apps.CrmConfig",
    "simple_crm.activity.apps.ActivityConfig",
    "simple_crm.data_quality.apps.DataQualityConfig",
    "simple_crm.reporting.apps.ReportingConfig",
    "simple_crm.identity.apps.IdentityConfig",
    "simple_crm.platform.apps.PlatformConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "simple_crm.config.observability.ObservabilityMiddleware",
    "simple_crm.config.security.SecurityHeadersMiddleware",
    "simple_crm.config.security.RequestRateLimitMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "simple_crm.identity.middleware.IdentitySessionMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "simple_crm.config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "simple_crm.config.wsgi.application"
ASGI_APPLICATION = "simple_crm.config.asgi.application"

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
        )
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-ar"
TIME_ZONE = "America/Argentina/Cordoba"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = Path(os.environ.get("DJANGO_STATIC_ROOT", PROJECT_ROOT / "staticfiles"))
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; "
    "base-uri 'self'; "
    "connect-src 'self'; "
    "font-src 'self'; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
    "img-src 'self' data:; "
    "object-src 'none'; "
    "script-src 'self'; "
    "style-src 'self' 'unsafe-inline';"
)
PERMISSIONS_POLICY = "camera=(), geolocation=(), microphone=(), payment=()"
RATE_LIMIT_RULES = {
    "/auth/local/login/": (10, 60),
    "/buscar/": (60, 60),
    "/segmentos/": (60, 60),
    "/informes/": (60, 60),
}
OBSERVABILITY_METRICS_TOKEN = os.environ.get("OBSERVABILITY_METRICS_TOKEN", "").strip()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple_crm_json": {
            "()": "simple_crm.config.observability.JsonLogFormatter",
        }
    },
    "handlers": {
        "simple_crm_console": {
            "class": "logging.StreamHandler",
            "formatter": "simple_crm_json",
        }
    },
    "loggers": {
        "simple_crm.observability": {
            "handlers": ["simple_crm_console"],
            "level": "INFO",
            "propagate": False,
        }
    },
}
STORAGES = {
    "staticfiles": {
        "BACKEND": "simple_crm.config.static_storage.CrmStaticFilesStorage",
    },
}
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTHENTICATION_BACKENDS = [
    "simple_crm.identity.backends.IdentityAuthenticationBackend",
]
LOGIN_URL = "/auth/local/login/"
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

OIDC_ISSUER_URL = os.environ.get("OIDC_ISSUER_URL", "").strip()
OIDC_CLIENT_ID = os.environ.get("OIDC_CLIENT_ID", "").strip()
OIDC_CLIENT_SECRET = os.environ.get("OIDC_CLIENT_SECRET", "").strip()
OIDC_REDIRECT_URI = os.environ.get("OIDC_REDIRECT_URI", "").strip()
LOCAL_AUTH_FALLBACK_ENABLED = os.environ.get(
    "DJANGO_LOCAL_AUTH_FALLBACK_ENABLED", ""
).strip().lower() in {"1", "true", "yes", "on"}
