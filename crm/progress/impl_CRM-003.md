# Implementation report — `CRM-003`

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` dirty completed-feature
  baseline, including the staged `__pycache__` deletion.
- Requirement IDs: CRM-003-R01, CRM-003-R02, CRM-003-R03, CRM-003-R04,
  CRM-003-R05.
- Acceptance-criterion IDs: CRM-003-AC01, CRM-003-AC02, CRM-003-AC03,
  CRM-003-AC04.
- Assignment: persisted implementer `crm003_postgres_implementer_terra`,
  `gpt-5.6-terra` / `high`; actual runtime matches the assignment.
- Dependencies and assumptions: CRM-002 is complete. Independent validation
  has executed the ephemeral PostgreSQL 18 acceptance gate successfully; only
  its sanitized pass output is recorded and no connection detail is persisted.

## Changed files and decisions

First durable slice:

- `src/simple_crm/config/environment.py`: safe PostgreSQL URL parsing and a
  `CONN_MAX_AGE=60`, health-checked, `ATOMIC_REQUESTS` configuration helper.
- `src/simple_crm/config/settings/{development,integration,_deployment}.py`:
  PostgreSQL-only development, integration, staging, and production settings.
- `src/simple_crm/platform/migrations/0001_enable_pg_trgm.py`: PostgreSQL
  `pg_trgm` extension migration.
- `scripts/verify-postgres.sh`: exact gated disposable PostgreSQL 18 evidence;
  it checks that the database is empty, migrates it, then proves the second run
  is a no-op without emitting `DATABASE_URL`.
- `tests/config/`, `tests/platform/`, and `tests/integration/`: generic
  parser/settings, migration-shape, and verifier-safety coverage.

Second durable slice:

- WhiteNoise compressed-manifest static storage, a guarded temporary
  `collectstatic` verifier, local template paths, and responsive Spanish layout.
- Provenance manifest and local official Bootstrap 5.3.8/HTMX 2.0.10 runtime
  bytes plus their official notices (Bootstrap MIT; HTMX Zero-Clause BSD/0BSD).
  It records published SRI, runtime SHA-256, license SHA-256, exact versions,
  source URLs, and `verified` status.
- Offline-safe vendor, static, and repository-safety verification scripts;
  the vendor verifier validates both runtime SHA-256/SHA-384 SRI, exact
  license identity/header and checksums, and guarded `collectstatic` proves
  both versioned files resolve into the manifest.
- README, environment example, and architecture/conventions/verification
  procedures for PostgreSQL 18, local assets, migration, fixture, and safe
  dedicated reset boundaries.

Validator follow-up correction: README and conventions/verification now state
that the foundation has no sales-domain fixtures because later owning features
own their models and fixtures. They document factories/in-memory generic data,
the future explicit `manage.py loaddata <versioned-owned-fixture>` boundary,
the current non-mutating `showmigrations` inspection, and the rule that the
PostgreSQL acceptance database starts empty with no fixtures.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-003-AC01 | Gated PostgreSQL 18 script and `pg_trgm` migration | Independent validator executed the pristine PostgreSQL 18 gate; sanitized output confirms empty apply and no-op rerun | PASS |
| CRM-003-AC02 | Safe URL parser and environment-specific PostgreSQL settings | 126 generic tests and config checks pass | PASS |
| CRM-003-AC03 | Local versioned assets, WhiteNoise configuration, static finders, and manifest collection | Asset/static/verifier tests and full generic matrix pass | PASS |
| CRM-003-AC04 | Repository safety scan and no-secret configuration examples | 126 generic tests and safety scan pass | PASS |

## Verification

Focused generic verification:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q \
  tests/config/test_postgres_configuration.py tests/config/test_settings.py \
  tests/platform/test_postgres_extension_migration.py \
  tests/integration/test_verify_postgres_script.py
26 passed in 0.90s
```

Second-slice focused checks:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q \
  tests/config/test_static_configuration.py \
  tests/integration/test_static_safety_scripts.py \
  tests/platform/test_pages_and_health.py
8 passed (the existing WhiteNoise test warning is non-fatal)

bash scripts/verify-static.sh
bash scripts/verify-repository-safety.sh
repository safety scan passed

bash scripts/verify-vendored-assets.sh
vendored assets verified
```

Historical pre-handoff evidence: the deliberately unconfigured gate was also exercised with
`UV_CACHE_DIR=/tmp/uv-cache timeout 120s bash scripts/verify-postgres.sh`.
It failed closed before database activity with:

```text
scripts/verify-postgres.sh: line 8: DATABASE_URL: DATABASE_URL must target
the dedicated CRM-003 test database
```

Independent validation subsequently executed the real dedicated PostgreSQL 18
gate and reported this sanitized successful output, with no URL retained:

```text
PostgreSQL migration acceptance passed: empty apply and no-op rerun
```

Official artifacts were copied mechanically from the approved local inputs and
independently verified before acceptance. No substitute library, hand-written
minimized asset, or CDN runtime reference has been used.

Full task matrix after the second slice:

```text
timeout 60s ./crm/init.sh
126 passed, 4 non-fatal WhiteNoise test warnings; harness ready

PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test ... manage.py check
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test ... makemigrations --check --dry-run
timeout 60s bash scripts/verify-static.sh
bash scripts/verify-repository-safety.sh
git diff --check
all passed; pytest: 126 passed, 4 warnings

UV_CACHE_DIR=/tmp/uv-cache timeout 120s bash scripts/verify-clean.sh
passed in an isolated temporary UV environment (126 passed)

Note: this earlier matrix predates official asset availability; the resumed
asset matrix below supersedes its vendor-pending result.

UV_CACHE_DIR=/tmp/uv-cache timeout 120s bash scripts/verify-postgres.sh
exit 1: DATABASE_URL must target the dedicated CRM-003 test database (earlier
external AC01 blocker)
```

Resumed asset verification:

```text
Bootstrap CSS SHA-256
d85327d99c7a3ee1f9b5d0500d1370acea3ad2db39c163c2f51f232baedbdede
Bootstrap CSS SHA-384 SRI
sha384-sRIl4kxILFvY47J16cr9ZwB07vP4J8+LH7qKQnuqkuIAvNWLzeN8tE5YBujZqJLB
HTMX JS SHA-256
71ea67185bfa8c98c39d31717c6fce5d852370fcdfd129db4543774d3145c0de
HTMX JS SHA-384 SRI
sha384-H5SrcfygHmAuTDZphMHqBJLc3FhssKjG7w/CeCpFReSfwBWDTKpkzPP8c+cLsK+V
Bootstrap MIT SHA-256
4620c84ad5ce8602ff65640ed6b7c8b78ebb9e036584f0ebc1ccc88206a4bb51
HTMX Zero-Clause BSD/0BSD SHA-256
d3d2456f76414f2456104660ebd65aff1c04cd7966b942bdabd63f3cdb316a38

timeout 60s ./crm/init.sh; Ruff; djLint; mypy; pytest; Django checks;
verify-static; verify-vendored-assets; verify-repository-safety;
verify-clean; git diff --check
all passed; 126 tests passed (4 existing non-fatal WhiteNoise warnings)
```

Fixture-documentation correction verification:

```text
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test \
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py showmigrations
completed without mutation; lists simple_crm_platform 0001_enable_pg_trgm

PYTHONDONTWRITEBYTECODE=1 .venv/bin/djlint src/simple_crm/platform/templates --check
0 files would be updated

PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q \
  tests/config/test_settings.py tests/config/test_postgres_configuration.py \
  tests/platform/test_postgres_extension_migration.py \
  tests/integration/test_verify_postgres_script.py
30 passed

git diff --check
passed
```

## Risks and follow-up

The verifier requires `SIMPLE_CRM_POSTGRES_ACCEPTANCE=1`, the exact dedicated
database name `simple_crm_crm003_test`, and PostgreSQL 18 before it can apply
migrations. It never prints `DATABASE_URL`.

All four official runtime/license files are now present at their manifest
paths. The previously pristine PostgreSQL 18 acceptance database was consumed
by independent validation, which recorded a sanitized PASS; this implementation
turn did not rerun or connect to it.

Provenance correction: HTMX's official license bytes and verified SHA-256 are
unchanged, but the path is now `htmx-2.0.10-0BSD.txt` and the manifest uses SPDX
`0BSD` with the exact `Zero-Clause BSD` header. Bootstrap remains MIT. The
vendor verifier and static tests now reject a mismatched name/version/license
tuple or a notice whose semantic header conflicts with manifest metadata.

Correction verification:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q \
  tests/config/test_static_configuration.py \
  tests/integration/test_static_safety_scripts.py \
  tests/platform/test_pages_and_health.py
8 passed, 4 existing non-fatal WhiteNoise warnings

bash scripts/verify-vendored-assets.sh
vendored assets verified

timeout 60s bash scripts/verify-static.sh
passed

timeout 60s ./crm/init.sh; mypy; full pytest; Django checks/migration check;
verify-static; verify-vendored-assets; verify-repository-safety; verify-clean;
git diff --check
all passed; 126 tests passed, 4 existing non-fatal WhiteNoise warnings
```

The PostgreSQL acceptance command was deliberately not rerun: independent
validation already consumed the pristine database and recorded the sanitized
successful empty-migration/no-op output above.
