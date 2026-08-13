# Implementation report — CRM-020

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the preserved
  completed-feature worktree and CRM-019 closure.
- Requirement IDs: CRM-020-R01 through CRM-020-R06.
- Acceptance-criterion IDs: CRM-020-AC01 through CRM-020-AC05.
- Allowed scope: the CRM-020 task envelope, including the locked container,
  deployment entrypoint, observability instrumentation, operations contracts,
  runbooks, restore-drill adapter, health endpoint behavior, worker command,
  and executable tests.
- Out-of-scope files: feature state, session state, task envelope, validator
  report, agent definitions, provider credentials, cloud provisioning, and
  customer data.
- Dependencies and assumptions: CRM-002, CRM-003, CRM-017, and CRM-019 are
  done. Managed PostgreSQL/PITR, encrypted object storage, alert routing, and
  signed restore records remain deployment-owned evidence; this repository
  provides provider-neutral contracts and exact-name-gated adapters.

The persisted assignment names `crm020_operations_implementer_terra` using
`gpt-5.6-terra` with high reasoning effort. Actual runtime for this revision:
`gpt-5.6-terra`, reasoning effort `high`; no assignment discrepancy.

## CHANGES_REQUESTED repository revision — 2026-08-13

This bounded revision addresses only the independent validator's
repository-fixable findings. It does not manufacture staging promotion,
observability walkthrough, managed-backup/PITR restore, RPO/RTO, or alert
fire/recovery evidence; those remain external acceptance gates.

- `Dockerfile`: sets `DJANGO_STATIC_ROOT=/app/staticfiles`, matching the
  copied collectstatic manifest, and creates a UID 10001-owned
  `XDG_RUNTIME_DIR`/home directory at `/tmp/simplecrm-runtime`.
- `docker/entrypoint.sh`: gives Gunicorn that runtime directory for worker
  heartbeat files. Gunicorn's control socket now resolves beneath the same
  writable directory rather than `/app/.gunicorn`.
- `src/simple_crm/platform/views.py`: keeps the read-only public landing page
  outside `ATOMIC_REQUESTS`, allowing a production image smoke to render it
  without pretending an unavailable smoke database is a deployment failure.
- `scripts/verify-production-image.sh` and its integration test: build a
  disposable image, start it with only bounded fake configuration, fetch the
  rendered landing page, extract a manifest-hashed Bootstrap URL, require both
  HTTP requests to succeed, and verify the manifest, writable runtime path,
  and live Gunicorn control socket. The script removes its uniquely named
  container on exit.
- `src/simple_crm/config/observability.py` and `platform/jobs.py`: establish a
  fixed-length opaque correlation context per job (stable across retries), add
  a separate short opaque job reference to allow-listed event fields, and
  snapshot correlation values on log records.
- `tests/config/test_observability.py` and `tests/platform/test_jobs.py`:
  prove bounded opaque job values, formatter snapshot behavior, failed-job
  traceability, and redaction of the job ID, idempotency key, and exception
  payload.

The initial validator's static-root and Gunicorn warnings are resolved by the
actual image smoke below. The new failure trace is an implementation control,
not a claim that an external observability walkthrough occurred.

## Changed files and decisions

- `Dockerfile`: added a multi-stage, lockfile-driven production image with a
  digest-pinned Python base, Gunicorn/runtime dependencies, non-root UID/GID
  `10001`, process healthcheck, and web/worker entrypoint.
- `.dockerignore`: excludes repository metadata, virtual environments, caches,
  local databases, environment files, and generated artifacts.
- `docker/entrypoint.sh`: starts Gunicorn web processes or the bounded Django
  outbox worker; secrets and database configuration are external.
- `src/simple_crm/config/observability.py`: added bounded correlation IDs,
  JSON operational events, aggregate counters, database query count/timing,
  and request middleware without SQL, bodies, credentials, or personal data.
- `src/simple_crm/config/settings/base.py`: configured JSON logging, aggregate
  metrics token, and observability middleware.
- `src/simple_crm/platform/views.py` and `platform/urls.py`: added protected
  aggregate metrics and exempted only liveness from `ATOMIC_REQUESTS` so the
  dependency-free process probe remains dependency-free in production.
- `src/simple_crm/platform/jobs.py`, `data_quality/services.py`,
  `reporting/exports.py`, `identity/views.py`, and `crm/lead_services.py`:
  added safe bounded events and counters for worker, import, export,
  authentication, and critical lead commands.
- `src/simple_crm/platform/management/commands/run_worker.py`: added the
  separate bounded worker process command with one-shot and polling modes.
- `ops/observability.yaml`: versioned SLIs and alerts for availability,
  latency, errors, database saturation, job backlog, import failures, and
  backup freshness.
- `ops/runbooks.md` and `crm/docs/operations.md`: documented deployment,
  promotion, rollback, migrations, incidents, restore drills, credential
  rotation, worker recovery, backup/PITR, and object-storage contracts.
- `scripts/verify-operations.sh`: verifies image, process, SLI, alert, and
  runbook artifacts.
- `scripts/restore-drill.sh`: gated `pg_dump`/`pg_restore` adapter for exact
  disposable source/restore database names with readiness, row-count,
  lineage, report-catalog, and RTO checks.
- `tests/config/test_observability.py`,
  `tests/platform/test_observability_requests.py`,
  `tests/platform/test_pages_and_health.py`, and the two integration contract
  tests: cover correlation/redaction, protected metrics, dependency-free
  liveness under atomic requests, operational artifacts, and restore gating.
- `README.md`, `crm/docs/architecture.md`, `crm/docs/conventions.md`, and
  `crm/docs/verification.md`: documented the operational boundary and
  provider-owned evidence requirements.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-020-AC01 | Digest-pinned multi-stage image, external settings, no embedded credentials, non-root runtime, separate web/worker entrypoint | Docker build succeeded; image metadata showed `user=10001:10001`; image `id` command confirmed UID/GID 10001; operations verifier passed | PASS |
| CRM-020-AC02 | Gunicorn web command, worker command, production runbook, migration/promotion/rollback procedure, process healthcheck | Full harness passed; image liveness smoke returned HTTP 200 with CSP, Permissions-Policy, and X-Request-ID; operations verifier passed | PASS |
| CRM-020-AC03 | Correlation context, JSON formatter, allow-listed event fields, query count/timing, protected aggregate metrics endpoint, domain/job/import/export/auth instrumentation | Observability tests passed; production image smoke returned a correlation response header; redaction tests passed | PASS |
| CRM-020-AC04 | Exact-name-gated isolated restore adapter, count/lineage/report checks, RPO/RTO inputs, managed backup/PITR and encrypted-storage runbook contract | Restore-drill contract test passed; unconfigured invocation fails closed with status 2. Actual provider restore remains deployment-owned evidence | FOLLOW-UP REQUIRED at staging release |
| CRM-020-AC05 | Versioned SLI/alert definitions and runbooks for web, database, jobs, imports, and backup freshness | Operations verifier and full harness passed. Alert fire/recovery requires deployment monitoring evidence | FOLLOW-UP REQUIRED at staging release |

## Verification

Exact verification performed on 2026-08-13:

- `timeout 120s ./crm/init.sh` — harness metadata valid; Ruff, formatting,
  mypy, `224 passed`, Django checks, migration drift, repository safety, and
  vendored assets passed.
- `bash scripts/verify-operations.sh` — `Operations artifact verification
  passed`.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/config/test_observability.py tests/platform/test_observability_requests.py tests/integration/test_verify_operations_script.py tests/integration/test_restore_drill_script.py`
  — `7 passed, 2 warnings`.
- `bash scripts/restore-drill.sh` without the explicit opt-in — failed closed
  with status 2 and `SIMPLE_CRM_RESTORE_DRILL must equal 1`.
- `docker build --tag simple-crm:crm020-local .` — succeeded using the
  digest-pinned Python 3.12 slim base; the final build collected 130 static
  files and post-processed 390 files into the image manifest.
- `docker run --rm --entrypoint id simple-crm:crm020-local` — `uid=10001(simplecrm)
  gid=10001(simplecrm)`.
- Production-style image smoke with external configuration and trusted-proxy
  header — `/health/live/` returned `200`, body `{"status": "ok"}`, and
  response contained CSP, Permissions-Policy, and `X-Request-ID`. The
  manifest maps the vendored static assets to hashed paths; probing the raw
  unhashed source path returns 404 as expected under manifest storage.
- `git diff --check` — passed.

Revision verification performed on 2026-08-13:

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/config/test_observability.py tests/platform/test_observability_requests.py tests/platform/test_pages_and_health.py tests/platform/test_jobs.py tests/integration/test_verify_operations_script.py tests/integration/test_verify_production_image_script.py tests/integration/test_restore_drill_script.py` — `24 passed, 7 warnings`. The warnings are existing local WhiteNoise missing-directory warnings outside the image.
- `bash scripts/verify-operations.sh` — `Operations artifact verification passed`.
- `bash scripts/verify-production-image.sh` — passed. The disposable image build collected `130` static files and post-processed `390`; its rendered `/` page emitted a manifest-hashed Bootstrap asset that returned successfully. The verifier also confirmed `/app/staticfiles/staticfiles.json`, the UID 10001-writable runtime directory, and `/tmp/simplecrm-runtime/gunicorn.ctl`.
- `timeout 120s ./crm/init.sh` — exit 0: harness metadata, Ruff, formatting, mypy, Django checks, migration drift, repository safety, and vendored assets passed; `229 passed, 28 warnings`.
- `git diff --check` and `git diff --no-index --check /dev/null scripts/verify-production-image.sh` — passed with no output.

## Risks and follow-up

- CRM-020 cannot claim full operational acceptance until staging proves the
  provider-owned backup/PITR restore drill, encrypted temporary artifact
  storage, and alert fire/recovery records. The repository deliberately does
  not invent those external facts.
- The full suite still reports existing warnings for the absent local
  `staticfiles/` directory. The verified production image instead uses its
  collected `/app/staticfiles` manifest and a writable Gunicorn control path;
  it does not emit the prior static-root/control-path failure.
- The observability counters are an aggregate local adapter; production must
  forward events and metrics to the managed monitoring system and define
  retention/access controls there.
