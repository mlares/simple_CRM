# Operations contract

CRM-020 uses one versioned, non-root image for the web and worker process
types. `Dockerfile` installs only the locked production dependency graph;
`docker/entrypoint.sh web` starts Gunicorn and `worker` starts the bounded
transactional outbox command. Staging and production receive configuration
from their deployment secret/configuration facilities, never from the image.

The application emits JSON operational events with an opaque `X-Request-ID`,
route names rather than raw URLs, status, duration, database query count, job
state, and bounded outcome fields. Each worker job has a deterministic opaque
correlation ID plus a short opaque job reference, so retries and failures can
be traced without logging primary keys, idempotency keys, or payload values. It
never records request bodies, query text, SQL parameters, notes, workbook rows,
credentials, or personal identifiers.
The optional `/health/metrics/` endpoint requires `OBSERVABILITY_METRICS_TOKEN`
and returns aggregate in-process counters only; a deployment should scrape or
forward them to its managed metrics system.

SLIs and alert thresholds are versioned in `ops/observability.yaml`. The
initial targets are 99.5% monthly availability, p95 500 ms for list/search,
p95 2 seconds for dashboards, error rate below 1%, database saturation below
80%, job backlog below 100, import failures below 5%, and backup freshness
within 15 minutes.

Backups remain a managed PostgreSQL responsibility: encrypted storage,
point-in-time recovery, 35-day retention, and quarterly isolated restore
drills are release requirements. `scripts/restore-drill.sh` is an explicit,
database-name-gated rehearsal adapter; it refuses shared names and does not
print credentials. Provider provisioning and signed drill records remain
deployment evidence rather than fabricated local state.

See [the operational runbooks](../../ops/runbooks.md) for deploy, rollback,
migration, incident, restore, credential rotation, and worker recovery steps.

## Current validation state — 2026-08-13

CRM-020 is `changes_requested`. CRM-001 through CRM-019 and CRM-023 are done;
CRM-021 and CRM-022 remain pending. The repository evidence includes 229
passing full-harness tests, 24 passing focused revision tests, and passing
`scripts/verify-operations.sh` and `scripts/verify-production-image.sh` runs.

The image runtime pins `DJANGO_STATIC_ROOT=/app/staticfiles`, the same location
that receives the collected WhiteNoise manifest. `XDG_RUNTIME_DIR` and the
Gunicorn worker temporary directory are owned by the non-root runtime user.
`scripts/verify-production-image.sh` builds a disposable image smoke, fetches
the rendered landing page, extracts a manifest-hashed asset, and verifies that
both return successfully. This resolves the previous effective static-root,
rendered/static HTTP, and non-root Gunicorn control-path warnings. The
failed-job correlation/redaction tests also pass. Local test settings still
emit non-fatal WhiteNoise warnings for the absent repository-level
`staticfiles/` directory; the production image instead uses its verified
collected manifest.

The remaining acceptance boundary is external to this repository. It requires
a same-digest staging/production promotion record; a controlled staging
deployment, migration, readiness, and rollback rehearsal; a deployed failed
request/job observability walkthrough; a signed isolated managed-backup/PITR
restore proving encrypted artifacts, backup freshness, login, row counts,
lineage, a representative report, and measured approved RPO/RTO; and alert
fire/recovery records for web failure, database unavailability, stale backup,
and excessive job backlog. Until all records exist and independent validation
approves them, CRM-020 remains `changes_requested` even though its repository
implementation checks are green. CRM-021 cannot start because it depends on
CRM-020 and no source workbook is present.
