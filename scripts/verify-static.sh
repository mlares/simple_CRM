#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
VERIFY_PARENT="${TMPDIR:-/tmp}"
case "$VERIFY_PARENT" in /*) ;; *) echo "TMPDIR must be absolute" >&2; exit 2;; esac
VERIFY_TMP_DIR="$(mktemp -d "${VERIFY_PARENT%/}/simple-crm-static.XXXXXXXX")"
case "$VERIFY_TMP_DIR" in "${VERIFY_PARENT%/}"/simple-crm-static.*) ;; *) exit 2;; esac
trap 'rm -rf -- "$VERIFY_TMP_DIR"' EXIT HUP INT TERM

cd "$PROJECT_ROOT"
PYTHON_BIN="${PYTHON_BIN:-.venv/bin/python}"
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.production \
DJANGO_SECRET_KEY='P9!simple-CRM-production-check-key_7xQ2vN8zL4mR6tY1wK3cB5' \
DJANGO_ALLOWED_HOSTS=crm.example.com \
DATABASE_URL=postgresql://crm:local-check@localhost:5432/crm \
DJANGO_DEBUG=false \
DJANGO_SESSION_COOKIE_SECURE=true \
DJANGO_CSRF_COOKIE_SECURE=true \
DJANGO_STATIC_ROOT="$VERIFY_TMP_DIR/static" \
PYTHONDONTWRITEBYTECODE=1 "$PYTHON_BIN" manage.py collectstatic --noinput --clear >/dev/null
test -f "$VERIFY_TMP_DIR/static/staticfiles.json"
test -f "$VERIFY_TMP_DIR/static/vendor/bootstrap/5.3.8/bootstrap.min.css"
test -f "$VERIFY_TMP_DIR/static/vendor/htmx/2.0.10/htmx.min.js"
grep -q 'vendor/bootstrap/5.3.8/bootstrap.min.css' "$VERIFY_TMP_DIR/static/staticfiles.json"
grep -q 'vendor/htmx/2.0.10/htmx.min.js' "$VERIFY_TMP_DIR/static/staticfiles.json"
