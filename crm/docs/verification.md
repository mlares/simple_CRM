# Verification contract

`crm/init.sh` validates agent metadata and invokes the root
`scripts/verify-fast.sh`. The script is deterministic and non-mutating; it
runs, in order:

1. Ruff lint and format checks;
2. djLint template checks;
3. mypy with django-stubs;
4. all pytest application and harness tests;
5. Django system and migration-drift checks;
6. a fail-closed production `check --deploy --fail-level WARNING` with safe,
   disposable fixture configuration.

Use `UV_CACHE_DIR=/tmp/uv-cache bash scripts/verify-clean.sh` for lockfile
evidence. It creates a validated `mktemp` directory, points
`UV_PROJECT_ENVIRONMENT` at that directory, runs
`uv sync --locked --all-groups --offline`, invokes the same fast suite, and
removes only that temporary directory through a guarded trap. It fails when a
locked dependency is absent from the local cache; that is an external cache
blocker, not permission to use an unlocked or network-dependent verification.

`scripts/verify-static.sh` runs `collectstatic` only into a guarded temporary
directory. `scripts/verify-repository-safety.sh` rejects credential-like
material and accidental local environment files. `scripts/verify-vendored-assets.sh`
verifies the committed local Bootstrap and HTMX bytes against the provenance
manifest; it intentionally fails until the official artifact and license files
are present. The fast suite reports that external pending state without claiming
asset verification passed.

PostgreSQL acceptance is intentionally separate from the generic suite:

```bash
DATABASE_URL='postgresql://…/simple_crm_crm003_test' \
SIMPLE_CRM_POSTGRES_ACCEPTANCE=1 \
UV_CACHE_DIR=/tmp/uv-cache timeout 120s bash scripts/verify-postgres.sh
```

It requires PostgreSQL 18 and an empty named disposable database, applies
migrations, verifies `pg_trgm`, and proves a no-op rerun. It must not be run
against any shared database.

No sales-domain fixtures exist in this foundation. Generic tests use factories
or in-memory data; future owning features may load only their explicitly
versioned fixture via `manage.py loaddata <versioned-owned-fixture>`. Until
then, this non-mutating inspection is the supported fixture procedure:

```bash
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test \
  UV_CACHE_DIR=/tmp/uv-cache uv run --locked python manage.py showmigrations
```

The PostgreSQL acceptance database must remain empty before migrations and
never receives fixtures.

Identity acceptance uses the generic suite. It verifies disabled-session
offboarding, the six-role/action matrix, exact object and team/campaign scope,
negative view-only permissions, temporary elevation expiry/audit, OIDC state and
PKCE handling, and the explicitly gated Argon2 local fallback. No provider
network is contacted by tests.

Party acceptance uses the generic suite for database-enforced subtype XOR,
effective relationship validation, raw-preserving email/phone normalization,
durable contact suppression, archive/concurrency behavior, shared institutional
contacts, geography-parent validation, and non-merging duplicate warnings. A
PostgreSQL 18 migration run remains the production constraint boundary; no
workbook rows are loaded by CRM-006.

Lead acceptance uses the generic suite for separate party links, atomic lead
creation, stage-transition rules, immutable stage history, next-action
requirements, owner reassignment history, partial uniqueness of active primary
assignments, optimistic concurrency, duplicate-candidate warnings, and
campaign-scope rejection. The compact next-action fields are intentionally
bridged to CRM-008's future task model. PostgreSQL-specific partial-index and
check-constraint evidence should be run on the dedicated empty acceptance
database when Docker/PostgreSQL access is available; no production or workbook
data is used.

Workspace acceptance uses rendered-page and domain tests for authentication,
scope filtering, manager-only unassigned cards, fixed urgency ordering,
timezone-aware fixtures, empty states, direct lead navigation, Spanish labels,
and absence of raw database vocabulary or identifiers. UI usability review
remains a manual follow-up when the full navigation surface is available.

Import acceptance uses the generic suite for lossless workbook staging,
checksum/version idempotency, row coordinates and raw payloads, formula-error
retention, malformed/header/size rejection, steward-only approval/application,
separate audit events, and no pre-approval canonical writes. PostgreSQL runtime
checks for the import constraints should be run on the dedicated acceptance
database when available; no production workbook is loaded by tests.

Quality acceptance uses the generic suite for severity/age queue ordering,
issue state transitions, exact normalized candidate generation, fuzzy review-
only behavior, merge preview coverage, approved atomic redirection, alias and
source-lineage preservation, suppressed contact retention, archived duplicate
parties, and immutable before/after/source audit evidence. PostgreSQL runtime
constraint evidence remains a separate acceptance step when available.

Activity acceptance uses the generic suite for quick-contact atomicity,
governed outcome semantics, placeholder rejection, task completion and
rescheduling constraints, timezone-aware overdue calculation, date-only
precision, permission-scoped timelines, and inclusion of stage/assignment
history. PostgreSQL-specific check-constraint evidence should be run on the
dedicated empty acceptance database when available; no production or workbook
data is used.

## Controlled catalog evidence

The generic SQLite suite exercises baseline idempotency, active-selection
behavior, audit records and the built-in admin permission boundary. PostgreSQL
enforcement is separate because it uses trigger protections SQLite cannot
prove. Run it only on a fresh PostgreSQL 18 database named exactly
`simple_crm_crm004_test`:

```bash
DATABASE_URL='postgresql://…/simple_crm_crm004_test' \
SIMPLE_CRM_POSTGRES_ACCEPTANCE=1 \
UV_CACHE_DIR=/tmp/uv-cache timeout 120s bash scripts/verify-postgres-catalogs.sh
```

It refuses a non-empty/wrong-name database, applies migrations and verifies a
no-op rerun. It then proves duplicate code, unknown geography parent, direct
code change and audit update/delete fail at the database boundary without
printing the URL. Never point it at an application database.

Global search checks include exact normalized identifiers, accent-insensitive
names, alias similarity, authorized notes, cross-scope non-disclosure, bounded
input, stable pagination, and the rendered Spanish endpoint.

Segment checks include allow-listed typed filters, bounded AND/OR definitions,
scope-first counts, private/shared saved-view authorization, lifecycle actions,
stable tie-break sorting, Spanish summaries, and reset controls.

Report checks include seeded metric-definition metadata, occurrence-date
activity semantics, attempted/placeholder exclusion, cross-scope KPI isolation,
date-window validation, and rendered definition/timeframe/freshness metadata.

Export checks include separate permission/denial audit, definition snapshot and
idempotency, current-scope materialization, CSV/XLSX formula neutralization,
expiry/download denial, checksum, and redacted audit metadata.

Privacy checks include audit-scope authorization, related-record bundles with
note redaction, immutable governance events, durable contact suppression,
retention preview/approval, legal-hold exclusion, non-destructive execution,
and commercial-only clinical-data guidance.

Transactional-job checks include one-row reminder idempotency, bounded claims,
lease recovery, safe retry/dead-letter behavior, task completion/cancellation/
reschedule replacement, digest-default preferences, administrative escalation,
and redacted operator projections. PostgreSQL `select_for_update(skip_locked)`
and constraint enforcement should be exercised on the dedicated acceptance
database when available; SQLite tests cover service behavior only.

Accessibility checks include Spanish document metadata, skip navigation, focus
visibility, 44-pixel-class controls, semantic labels, native form methods,
absence of required `hx-*` behavior, public help/glossary content, and
responsive table/card contracts. Run a manual keyboard, 200% zoom, phone
viewport, and screen-reader pass for the critical workflows before release;
the automated contract suite is a guardrail, not a substitute for that pass.

Security checks include generic production deployment checks, CSP/permissions
headers, secure cookie and HSTS settings, CSRF and safe-redirect regressions,
cache-backed route limits, safe upload filename normalization, formula
neutralization, repository credential scans, Ruff/mypy, and `pip-audit`.
PostgreSQL role privilege and RLS checks use a second dedicated disposable
database because SQLite cannot demonstrate them:

```bash
DATABASE_URL='postgresql://…/simple_crm_crm019_security_test' \\
SIMPLE_CRM_POSTGRES_SECURITY_ACCEPTANCE=1 \\
CRM019_MIGRATOR_PASSWORD='provided-by-the-disposable-db-secret-facility' \\
CRM019_WEB_PASSWORD='provided-by-the-disposable-db-secret-facility' \\
CRM019_WORKER_PASSWORD='provided-by-the-disposable-db-secret-facility' \\
CRM019_REPORTING_PASSWORD='provided-by-the-disposable-db-secret-facility' \\
UV_CACHE_DIR=/tmp/uv-cache timeout 120s bash scripts/verify-postgres-security.sh
```

The procedure is opt-in, requires PostgreSQL 18, refuses a wrong database
name, creates temporary non-superuser roles, proves web DDL/role denial,
governed reporting access, worker grants, and campaign-scoped lead RLS, then
removes its temporary roles and security objects. Catalog rows and their audit
history remain immutable; discard the dedicated database after acceptance
instead of deleting them. Never run it against shared or production data;
passwords must come from the disposable database secret facility and are never
committed or printed.

Operations acceptance is split between repository checks and deployment
evidence:

```bash
bash scripts/verify-operations.sh
```

This checks the non-root locked image, separate web/worker entrypoints, SLI and
alert definitions, and required runbooks. The provider-neutral restore adapter
is deliberately opt-in and destructive only to exact disposable database
names:

```bash
SIMPLE_CRM_RESTORE_DRILL=1 \\
SOURCE_DATABASE_URL='postgresql://…/simple_crm_crm020_source' \\
RESTORE_DATABASE_URL='postgresql://…/simple_crm_crm020_restore' \\
RESTORE_EXPECTED_LEADS=0 RESTORE_EXPECTED_SOURCE_DOCUMENTS=0 \\
RESTORE_EXPECTED_LINEAGE_LINKS=0 \\
bash scripts/restore-drill.sh
```

The deployment record must additionally prove image-digest promotion, managed
backup/PITR freshness, encrypted artifact storage, alert fire/recovery, and a
quarterly signed isolated restore drill. Local tests cannot manufacture those
provider facts.

### Current CRM-020 validation result

On 2026-08-13, independent validation recorded 229 passing full-harness tests,
24 passing focused revision tests, and passing operations-artifact and
production-image verifiers. The image smoke rendered `/`, fetched the
manifest-hashed Bootstrap asset, confirmed the collected
`/app/staticfiles/staticfiles.json`, and proved that UID/GID 10001 can use the
live `/tmp/simplecrm-runtime/gunicorn.ctl` socket. The previous effective
static-root, rendered/static HTTP, and non-root Gunicorn control-path warnings
are resolved. Correlation and redaction tests also prove the bounded failed-job
trace control. Non-fatal local-test WhiteNoise warnings for an absent
repository-level `staticfiles/` directory remain distinct from the verified
production image behavior.

The validator returned `CHANGES_REQUESTED`, so CRM-020 is not approved. Closure
requires all of the following external evidence:

- promotion of one image digest through staging and production;
- a controlled staging deployment, migration, readiness, and rollback
  rehearsal;
- a deployed observability walkthrough for a failed request or job using its
  correlation ID without personal-data payloads;
- a signed isolated restore from a managed backup/PITR input, with encrypted
  recovery artifacts, backup freshness, login, row-count, lineage, and
  representative-report checks plus measured approved RPO/RTO; and
- fire-and-recovery records for web failure, database unavailability, stale
  backup, and excessive job backlog alerts.

Repository tests and runbooks cannot substitute for those deployment-owned
records.

## HTTP evidence

Automated integration tests verify the Spanish landing page, dependency-free
liveness, successful database readiness, generic failure readiness, cache
headers, and absence of diagnostics. To manually smoke development without a
browser build step:

```bash
UV_CACHE_DIR=/tmp/uv-cache uv run --locked python manage.py runserver
```

Visit `/`, `/health/live/`, and `/health/ready/`, then stop the development
server. A non-persistent equivalent uses Django's test client:

```bash
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.development \
  UV_CACHE_DIR=/tmp/uv-cache uv run --locked python -c \
  'import django; django.setup(); from django.test import Client; response = Client(HTTP_HOST="localhost").get("/"); print(response.status_code, "CRM de Ventas" in response.content.decode())'
```

Feature reports must record exact commands, material output, environment
limitations, and an evidence row for each delegated acceptance criterion.
