#!/usr/bin/env bash
# Prove CRM-004 database constraints only on its empty dedicated PostgreSQL 18 DB.
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

: "${DATABASE_URL:?DATABASE_URL must target the dedicated CRM-004 test database}"
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
from django.apps import apps
from django.core.management import call_command
from django.db import DatabaseError, IntegrityError, connection

django.setup()

if connection.vendor != "postgresql":
    raise SystemExit("Dedicated PostgreSQL 18 database is required")
if connection.settings_dict["NAME"] != "simple_crm_crm004_test":
    raise SystemExit("DATABASE_URL must target simple_crm_crm004_test")
with connection.cursor() as cursor:
    cursor.execute("SHOW server_version_num")
    if not 180000 <= int(cursor.fetchone()[0]) < 190000:
        raise SystemExit("PostgreSQL 18 is required")
    cursor.execute("SELECT count(*) FROM information_schema.tables WHERE table_schema = 'public'")
    if cursor.fetchone()[0] != 0:
        raise SystemExit("Dedicated database must be empty before acceptance")

call_command("migrate", interactive=False, verbosity=0, stdout=StringIO())
second_run = StringIO()
call_command("migrate", interactive=False, verbosity=1, stdout=second_run)
if "No migrations to apply." not in second_run.getvalue():
    raise SystemExit("Second migration run was not a no-op")

from simple_crm.crm.models import Campaign, CatalogAuditEntry, Country, Province

campaign = Campaign.objects.get(code="GENERAL")
campaign.label = "Etiqueta aprobada"
campaign.save()
from importlib import import_module
seed = import_module("simple_crm.crm.migrations.0002_seed_baseline_catalogs")
seed.seed_baseline_catalogs(apps, None)
if Campaign.objects.get(code="GENERAL").label != "Etiqueta aprobada":
    raise SystemExit("Seed overwrote an explicitly edited label")
if Campaign.objects.filter(code="GENERAL").count() != 1:
    raise SystemExit("Seed duplicated a stable code")

def must_fail(action, message):
    try:
        action()
    except (IntegrityError, DatabaseError):
        return
    raise SystemExit(message)

must_fail(lambda: Campaign.objects.create(code="GENERAL", label="Duplicada"), "Duplicate code was accepted")
must_fail(lambda: Province.objects.create(code="INVALID", label="Inválida", country_id=999999), "Unknown foreign key was accepted")
with connection.cursor() as cursor:
    must_fail(lambda: cursor.execute("UPDATE simple_crm_crm_campaign SET code = 'ALTERADO' WHERE id = %s", [campaign.pk]), "Database allowed a code change")
audit = CatalogAuditEntry.objects.filter(catalog_code="GENERAL").first()
if audit is None:
    raise SystemExit("Catalog change was not audited")
with connection.cursor() as cursor:
    must_fail(lambda: cursor.execute("UPDATE simple_crm_crm_catalogauditentry SET action = 'updated' WHERE id = %s", [audit.pk]), "Database allowed audit mutation")
    must_fail(lambda: cursor.execute("DELETE FROM simple_crm_crm_catalogauditentry WHERE id = %s", [audit.pk]), "Database allowed audit deletion")

print("PostgreSQL catalog acceptance passed: constraints, immutable audit, and idempotent seeds")
PY
