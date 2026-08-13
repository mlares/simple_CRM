#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

export UV_CACHE_DIR="${UV_CACHE_DIR:-/tmp/uv-cache}"
export PYTHONDONTWRITEBYTECODE=1

uv sync --locked --offline

# `verify-clean.sh` supplies an isolated environment through UV_PROJECT_ENVIRONMENT.
# Direct invocations intentionally retain the project's conventional .venv.
VENV_BIN="${UV_PROJECT_ENVIRONMENT:-$PROJECT_ROOT/.venv}/bin"
"$VENV_BIN/ruff" check .
"$VENV_BIN/ruff" format --check .
"$VENV_BIN/djlint" src/simple_crm/platform/templates --check
"$VENV_BIN/mypy" src
"$VENV_BIN/pytest" -q
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test "$VENV_BIN/python" manage.py check
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test \
  "$VENV_BIN/python" manage.py makemigrations --check --dry-run
PYTHON_BIN="$VENV_BIN/python" bash scripts/verify-static.sh
bash scripts/verify-repository-safety.sh

if [ -f src/simple_crm/platform/static/vendor/bootstrap/5.3.8/bootstrap.min.css ] && \
  [ -f src/simple_crm/platform/static/vendor/htmx/2.0.10/htmx.min.js ]; then
  bash scripts/verify-vendored-assets.sh
else
  echo "[verify] vendored assets pending official download; tracked by manifest"
fi

DJANGO_SETTINGS_MODULE=simple_crm.config.settings.production \
DJANGO_SECRET_KEY='P9!simple-CRM-production-check-key_7xQ2vN8zL4mR6tY1wK3cB5' \
DJANGO_ALLOWED_HOSTS=crm.example.com \
DATABASE_URL=postgresql://crm:local-check@localhost:5432/crm \
DJANGO_DEBUG=false \
DJANGO_SESSION_COOKIE_SECURE=true \
DJANGO_CSRF_COOKIE_SECURE=true \
"$VENV_BIN/python" manage.py check --deploy --fail-level WARNING
