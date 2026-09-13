#!/usr/bin/env bash
# Prove PostgreSQL 18 migration idempotency only on the dedicated disposable DB.
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

: "${DATABASE_URL:?DATABASE_URL must target the dedicated CRM-003 test database}"
: "${SIMPLE_CRM_POSTGRES_ACCEPTANCE:?Set SIMPLE_CRM_POSTGRES_ACCEPTANCE=1 to opt in}"
if [ "$SIMPLE_CRM_POSTGRES_ACCEPTANCE" != "1" ]; then
  echo "SIMPLE_CRM_POSTGRES_ACCEPTANCE must equal 1" >&2
  exit 2
fi

export DJANGO_SETTINGS_MODULE=simple_crm.config.settings.integration
export PYTHONDONTWRITEBYTECODE=1

python_bin="${PYTHON_BIN:-.venv/bin/python}"
if [ ! -x "$python_bin" ]; then
  echo "Python environment is unavailable; run uv sync --locked first" >&2
  exit 2
fi

"$python_bin" - <<'PY'
from io import StringIO

import django
from django.core.management import call_command
from django.db import connection

django.setup()

if connection.vendor != "postgresql":
    raise SystemExit("Dedicated PostgreSQL 18 database is required")
if connection.settings_dict["NAME"] != "simple_crm_crm003_test":
    raise SystemExit("DATABASE_URL must target simple_crm_crm003_test")

with connection.cursor() as cursor:
    cursor.execute("SHOW server_version_num")
    version_number = int(cursor.fetchone()[0])
    if not 180000 <= version_number < 190000:
        raise SystemExit("PostgreSQL 18 is required")
    cursor.execute(
        "SELECT count(*) FROM information_schema.tables "
        "WHERE table_schema = 'public'"
    )
    if cursor.fetchone()[0] != 0:
        raise SystemExit("Dedicated database must be empty before acceptance")

first_run = StringIO()
call_command("migrate", interactive=False, verbosity=1, stdout=first_run)
second_run = StringIO()
call_command("migrate", interactive=False, verbosity=1, stdout=second_run)
if "No migrations to apply." not in second_run.getvalue():
    raise SystemExit("Second migration run was not a no-op")

with connection.cursor() as cursor:
    cursor.execute("SELECT extname FROM pg_extension WHERE extname = 'pg_trgm'")
    if cursor.fetchone() != ("pg_trgm",):
        raise SystemExit("pg_trgm extension was not installed")

print("PostgreSQL migration acceptance passed: empty apply and no-op rerun")
PY
