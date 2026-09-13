# Explorer report — CRM-002 Django foundation

## Question

What bounded Django 5.2 architecture should implement `CRM-002-R01` through
`CRM-002-R05` and `CRM-002-AC01` through `CRM-002-AC04` without pulling
business models or the PostgreSQL-specific work of CRM-003 into this feature?

## Baseline and gaps

- CRM-001 is recorded `done`, so CRM-002's only dependency is satisfied in
  metadata. CRM-002 is still `pending` and no CRM-002 task envelope exists.
- The baseline revision is `fcbe3b4` on
  `feature/first_version_with_agents`, with the completed CRM-001 work still
  present as an uncommitted worktree. The implementer must preserve it and the
  pre-existing staged bytecode deletion.
- Application code is only `src/simple_crm/__init__.py`, which prints the
  scaffold greeting. There is no Django project, settings module, URL map,
  template, app package, health endpoint, application test, or verification
  script.
- `docs/architecture.md`, `docs/conventions.md`, and `docs/verification.md`
  are still placeholders. CRM-002 is the first appropriate feature to replace
  them with enforceable project-specific contracts.
- `pyproject.toml` requires Python 3.12 and `.python-version` selects 3.12.
  The lock resolves Python 3.12.13, Django 5.2.17,
  `dj-database-url` 3.1.2, psycopg 3.3.4, pytest 9.1.1,
  pytest-django 4.13.0, Ruff 0.16.2, mypy 2.3.0,
  django-stubs 6.0.9, and djLint 1.44.1. No dependency addition is needed for
  this feature.

## Recommended package boundary (R01)

Keep every project module inside the existing distributable namespace. This
avoids generic top-level imports such as `platform` shadowing the Python
standard library and makes the src layout work consistently when installed by
UV.

```text
manage.py
src/simple_crm/
  config/
    environment.py
    urls.py
    asgi.py
    wsgi.py
    settings/
      base.py
      development.py
      test.py
      _deployment.py
      staging.py
      production.py
  crm/
  activity/
  data_quality/
  reporting/
  identity/
  platform/
    apps.py
    urls.py
    views.py
    templates/platform/home.html
tests/
  config/
  platform/
scripts/
  format.sh
  verify-fast.sh
  verify-clean.sh
```

Each domain directory should be an explicit Django app with an `AppConfig`
and stable label, but contain no business models yet. `config` owns only
composition and deployment entry points. `platform` may own the landing page
and health probes because those are platform concerns. Later features should
place business services inside their owning app and communicate through
documented service interfaces; views and templates must not become the
business-rule layer.

Replace the placeholder package greeting and remove the unused console-script
entry point unless the orchestrator explicitly wants a management wrapper.
`manage.py` plus WSGI/ASGI are the conventional entry points.

## Settings and environment contract (R02-R03, AC04)

- `base.py`: shared installed apps, middleware, templates, URL/WSGI/ASGI
  wiring, `LANGUAGE_CODE = "es-ar"`, `USE_I18N = True`,
  `USE_TZ = True`, and `TIME_ZONE = "America/Argentina/Cordoba"`.
  PostgreSQL will then store aware timestamps in UTC while Django presents
  local business time in Cordoba. Render the base document with
  `lang="es-AR"` and keep all visible CRM-002 copy in Spanish.
- `development.py`: explicit development-only secret, `DEBUG=True`, local
  hosts only, console email, and a local SQLite database by default. Permit a
  `DATABASE_URL` override. SQLite is acceptable for this foundation's generic
  tests, but must never be presented as evidence for PostgreSQL-specific
  behavior.
- `test.py`: deterministic test secret, `DEBUG=False`, `testserver` host,
  in-memory SQLite, and fast password hashing. This is the default
  pytest-django/mypy settings module.
- `_deployment.py`: shared fail-closed staging/production parsing. Require
  `DJANGO_SECRET_KEY`, a non-empty comma-separated `DJANGO_ALLOWED_HOSTS`, and
  `DATABASE_URL`; accept only a PostgreSQL URL for deployed settings. Reject a
  short/placeholder secret, wildcard/scheme/path host entries, a truthy
  `DJANGO_DEBUG`, and any explicit attempt to disable secure session or CSRF
  cookies. Hard-code `DEBUG=False`, HTTPS redirect, secure/HTTP-only/SameSite
  cookies, clickjacking protection, and conservative HSTS defaults. Do not
  infer a proxy header unless the deployment contract explicitly enables it.
- `staging.py` and `production.py`: explicit entry modules importing the
  deployment contract; neither should silently fall back to development
  values. Environment parsing should raise `ImproperlyConfigured` with the
  missing/invalid variable name, never its value.

CRM-003 should retain ownership of PostgreSQL 18 integration, connection
lifetime/tuning, extensions, migrations-from-empty, and locally vendored
Bootstrap/HTMX. CRM-002 should only enforce that deployed database URLs are
PostgreSQL-shaped and use generic database readiness semantics.

Production tests should isolate settings imports in subprocesses or test pure
environment-parsing functions; mutating `os.environ` after Django settings are
cached creates order-dependent false positives. A valid production fixture
should run `check --deploy --fail-level WARNING`; negative fixtures should
prove missing secret, debug enabled, insecure cookie flags, and empty,
wildcard, or URL-shaped hosts are rejected.

## HTTP surface (R05, AC02-AC03)

- `/` renders a small semantic Spanish landing page from a Django template.
  It should use no CDN and require no Node/JavaScript build. Bootstrap and HTMX
  references wait for CRM-003.
- `/health/live/` performs no dependency access and returns only
  `{"status":"ok"}` with HTTP 200. This answers whether the Django process can
  serve requests.
- `/health/ready/` executes a minimal `SELECT 1` through Django's default
  connection. It returns only `{"status":"ready"}`/200 or
  `{"status":"unavailable"}`/503 after catching `DatabaseError`. Never return
  exception text, backend/version, host, database name, credentials, or a
  traceback. Mark both responses `Cache-Control: no-store`.

Endpoint tests should prove Spanish page content and HTML language, the live
probe's independence from database failure, readiness 200 with the test
database, readiness 503 with the cursor/connection made unavailable, the
generic response body, and absence of exception/connection details.

## Deterministic developer commands (R04, AC01)

Put configuration in `pyproject.toml` (Ruff target `py312`, pytest-django test
settings/test paths, mypy's django-stubs plugin and test settings) and expose
small root-relative scripts:

- Format: `UV_CACHE_DIR=/tmp/uv-cache uv run --locked ruff format .` followed
  by Ruff safe fixes and djLint reformatting for HTML templates.
- Lint: `ruff check .`, `ruff format --check .`, and djLint `--check` against
  HTML templates.
- Types: `mypy src` with `simple_crm.config.settings.test`.
- Tests: `pytest -q` covering both `crm/tests` and application tests.
- Django: `manage.py check`, `makemigrations --check --dry-run`, and a
  production `check --deploy --fail-level WARNING` using a valid, non-secret
  test fixture environment.

`scripts/verify-fast.sh` should run all non-mutating checks above under
`uv run --locked`, resolve the repository root from the script location, and
fail on the first error. Change `crm/harness.json:test_command` to invoke that
script from the `crm/` working directory (for example,
`UV_CACHE_DIR=/tmp/uv-cache ../scripts/verify-fast.sh`). Leaving it as bare
`pytest -q` would start discovery in `crm/` and can omit top-level application
tests.

`scripts/verify-clean.sh` should create an explicit temporary UV project
environment, run `uv sync --locked --all-groups`, then run the same fast
script. This is the AC01 clean-lockfile evidence. A mutating formatter must not
be part of verification.

## Python bootstrap pitfall

The host's `/usr/bin/python3` is Python 3.8.10, while UV has Python 3.12.13 and
the project requires 3.12+. `crm/init.sh` intentionally uses system Python
only for the dependency-free harness checker, then invokes the configured UV
command. Do not call Django, pytest, TOML parsing, or project imports directly
with `python3` from that bootstrap script: Django 5.2/project dependencies are
not available there, and newer language/library APIs can break harness startup
before UV is reached. Keep `harness_check.py` Python-3.8-compatible and run all
application tooling as `uv run --locked ...` with the writable cache override.

## Acceptance evidence map

- AC01: clean temporary `uv sync --locked --all-groups`, Django system check,
  and complete `verify-fast.sh` output.
- AC02: Django client integration test for `/`, plus a documented manual
  `runserver` check using development settings; no external/static build
  dependency in the rendered response.
- AC03: endpoint tests for available/unavailable database plus proof that the
  same failure leaves liveness at 200.
- AC04: isolated environment/settings rejection tests and a passing production
  deployment check at warning fail level.

The implementer should update the three project docs and README alongside the
code so the commands, supported runtimes, settings variables, health semantics,
and module dependency rules are durable rather than report-only.
