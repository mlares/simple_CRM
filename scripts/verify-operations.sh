#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

required_files=(
  Dockerfile
  .dockerignore
  docker/entrypoint.sh
  ops/observability.yaml
  ops/runbooks.md
  crm/docs/operations.md
  scripts/restore-drill.sh
  scripts/verify-production-image.sh
)
for file in "${required_files[@]}"; do
  test -s "$file" || { echo "missing operational artifact: $file" >&2; exit 1; }
done

bash -n docker/entrypoint.sh scripts/restore-drill.sh scripts/verify-production-image.sh
grep -q '^USER 10001:10001$' Dockerfile
grep -q 'uv.lock' Dockerfile
grep -q 'collectstatic --noinput --clear' Dockerfile
grep -q '/build/staticfiles' Dockerfile
grep -q 'DJANGO_STATIC_ROOT=/app/staticfiles' Dockerfile
grep -q 'XDG_RUNTIME_DIR=/tmp/simplecrm-runtime' Dockerfile
grep -q 'gunicorn simple_crm.config.wsgi:application' docker/entrypoint.sh
grep -q -- '--worker-tmp-dir' docker/entrypoint.sh
grep -q 'run_worker' docker/entrypoint.sh
if grep -Eq 'runserver|DJANGO_SECRET_KEY=|DATABASE_URL=postgres' Dockerfile docker/entrypoint.sh; then
  echo "development server or embedded secret detected in image artifacts" >&2
  exit 1
fi

for required in availability latency error_rate database_saturation job_backlog import_failures backup_freshness; do
  grep -q "^  $required:" ops/observability.yaml || {
    echo "missing SLI: $required" >&2
    exit 1
  }
done
for runbook in "Deploy and promote" "Rollback and migration" "Incident response"   "Restore drill and recovery" "Credential rotation" "Worker recovery"; do
  grep -q "## $runbook" ops/runbooks.md || {
    echo "missing runbook: $runbook" >&2
    exit 1
  }
done

echo "Operations artifact verification passed"
