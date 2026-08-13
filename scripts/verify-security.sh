#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"
VENV_BIN="${UV_PROJECT_ENVIRONMENT:-$PROJECT_ROOT/.venv}/bin"

"$VENV_BIN/ruff" check .
"$VENV_BIN/mypy" src
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.production \
DJANGO_SECRET_KEY='P9!simple-CRM-production-check-key_7xQ2vN8zL4mR6tY1wK3cB5' \
DJANGO_ALLOWED_HOSTS=crm.example.com \
DATABASE_URL=postgresql://crm:local-check@localhost:5432/crm \
DJANGO_DEBUG=false \
DJANGO_SESSION_COOKIE_SECURE=true \
DJANGO_CSRF_COOKIE_SECURE=true \
PYTHONDONTWRITEBYTECODE=1 "$VENV_BIN/python" manage.py check --deploy --fail-level WARNING

if command -v "$VENV_BIN/pip-audit" >/dev/null 2>&1; then
  AUDIT_CACHE_DIR="${TMPDIR:-/tmp}/simple-crm-pip-audit-cache"
  AUDIT_REQUIREMENTS="$(mktemp "${TMPDIR:-/tmp}/simple-crm-audit-requirements.XXXXXX")"
  trap 'rm -f "$AUDIT_REQUIREMENTS"' EXIT
  mkdir -p "$AUDIT_CACHE_DIR"
  "$VENV_BIN/pip" freeze --local --exclude-editable >"$AUDIT_REQUIREMENTS"
  "$VENV_BIN/pip-audit" --requirement "$AUDIT_REQUIREMENTS" --no-deps \
    --cache-dir "$AUDIT_CACHE_DIR" --strict --progress-spinner off
else
  echo "pip-audit is required for the dependency scan" >&2
  exit 1
fi
