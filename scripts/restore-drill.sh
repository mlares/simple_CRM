#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

if [ "${SIMPLE_CRM_RESTORE_DRILL:-}" != "1" ]; then
  echo "SIMPLE_CRM_RESTORE_DRILL must equal 1" >&2
  exit 2
fi
: "${SOURCE_DATABASE_URL:?SOURCE_DATABASE_URL is required}"
: "${RESTORE_DATABASE_URL:?RESTORE_DATABASE_URL is required}"

case "$SOURCE_DATABASE_URL" in
  */simple_crm_crm020_source) ;;
  *) echo "SOURCE_DATABASE_URL must target simple_crm_crm020_source" >&2; exit 2 ;;
esac
case "$RESTORE_DATABASE_URL" in
  */simple_crm_crm020_restore) ;;
  *) echo "RESTORE_DATABASE_URL must target simple_crm_crm020_restore" >&2; exit 2 ;;
esac

if ! command -v pg_dump >/dev/null 2>&1 || ! command -v pg_restore >/dev/null 2>&1; then
  echo "pg_dump and pg_restore are required for the isolated restore drill" >&2
  exit 2
fi

TEMP_ARTIFACT=0
if [ -z "${BACKUP_ARTIFACT:-}" ]; then
  BACKUP_ARTIFACT="${TMPDIR:-/tmp}/simple-crm-crm020-backup.dump"
  TEMP_ARTIFACT=1
fi
STARTED_AT="$(date +%s)"
cleanup() {
  if [ "$TEMP_ARTIFACT" = "1" ]; then
    rm -f -- "$BACKUP_ARTIFACT"
  fi
}
trap cleanup EXIT

pg_dump --format=custom --no-owner --file="$BACKUP_ARTIFACT" "$SOURCE_DATABASE_URL"
pg_restore --clean --if-exists --no-owner --dbname="$RESTORE_DATABASE_URL" "$BACKUP_ARTIFACT"

DATABASE_URL="$RESTORE_DATABASE_URL" \
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.integration \
PYTHONDONTWRITEBYTECODE=1 "${PYTHON_BIN:-.venv/bin/python}" - <<'PY'
import os

import django
from django.db import connection

django.setup()

if connection.vendor != "postgresql":
    raise SystemExit("Restore target must be PostgreSQL")
if connection.settings_dict["NAME"] != "simple_crm_crm020_restore":
    raise SystemExit("Restore target database name is not isolated")

with connection.cursor() as cursor:
    cursor.execute("SELECT 1")
    if cursor.fetchone() != (1,):
        raise SystemExit("Restored database readiness failed")

from simple_crm.crm.models import Lead  # noqa: E402
from simple_crm.data_quality.models import SourceCanonicalLink, SourceDocument  # noqa: E402
from simple_crm.reporting.models import MetricDefinition  # noqa: E402

counts = {
    "leads": Lead.objects.count(),
    "source_documents": SourceDocument.objects.count(),
    "lineage_links": SourceCanonicalLink.objects.count(),
    "active_metrics": MetricDefinition.objects.filter(is_active=True).count(),
}
expected = {
    "leads": int(os.environ.get("RESTORE_EXPECTED_LEADS", "0")),
    "source_documents": int(os.environ.get("RESTORE_EXPECTED_SOURCE_DOCUMENTS", "0")),
    "lineage_links": int(os.environ.get("RESTORE_EXPECTED_LINEAGE_LINKS", "0")),
}
for name, expected_value in expected.items():
    if counts[name] != expected_value:
        raise SystemExit(
            f"Restore count mismatch for {name}: {counts[name]} != {expected_value}"
        )
if counts["active_metrics"] <= 0:
    raise SystemExit("Restored governed report catalog is empty")
print("Restore verification passed: readiness, row counts, lineage, and report catalog")
PY

FINISHED_AT="$(date +%s)"
ELAPSED_SECONDS=$((FINISHED_AT - STARTED_AT))
MAX_SECONDS="${RESTORE_MAX_SECONDS:-3600}"
if [ "$ELAPSED_SECONDS" -gt "$MAX_SECONDS" ]; then
  echo "Restore drill exceeded the approved RTO budget" >&2
  exit 1
fi
echo "Restore drill completed in ${ELAPSED_SECONDS}s"
