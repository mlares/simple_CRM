# Validation report — `CRM-002`

## Verdict

`APPROVED`

The bounded correction suppresses the value-bearing `urllib` exception chain
for malformed PostgreSQL ports and adds regression coverage. Independent
reproduction now emits only the generic `DATABASE_URL is invalid` error; all
requirements, acceptance criteria, and assigned verification commands pass.

## Independence and scope

- Validator: `crm002_foundation_validator`; persisted assignment
  `gpt-5.6-sol`, reasoning effort `high`, source `role_default`.
- Actual runtime: `gpt-5.6-sol`, reasoning effort `high`. No assignment
  discrepancy was observed.
- Initial implementer: `crm002_foundation_implementer_terra`, persisted and
  reported runtime `gpt-5.6-terra`, reasoning effort `high`.
- Correction implementer: `crm002_orchestrator`, persisted and actual runtime
  `gpt-5.6-sol`, reasoning effort `high`, source `override`. The persisted
  reason states that the runtime thread limit prevented spawning or
  reactivating a Terra/high implementer, so the existing orchestrator executed
  the bounded revision sequentially before returning to orchestration. This
  validator remains a distinct agent and did not implement either revision.
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188`, the
  recorded resumed dirty-worktree baseline, current status/diffs, the staged
  bytecode deletion, the implementation report, source, scripts, and tests.
- Allowed validator write target: `crm/progress/validation_CRM-002.md` only.
  No application, configuration, script, test, feature-state, task-envelope,
  history/current, or staged file was edited by this validation.

## Requirement evidence

| Requirement ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-002-R01 | `src/simple_crm/config` plus explicit `crm`, `activity`, `data_quality`, `reporting`, `identity`, and `platform` app configs and stable app labels. | PASS | The modular `src` layout matches the architecture contract; no generic top-level `platform` package was introduced. |
| CRM-002-R02 | All four isolated settings variants, `_deployment.py`, environment parsers, 17 focused settings tests, the deployment check, direct malformed-port reproduction, and an independent 12-case production import matrix. | PASS | Missing secret, enabled debug, insecure cookies, empty/trailing-empty/wildcard/URL-shaped hosts, malformed/non-PostgreSQL DB URLs, and malformed ports fail closed. Every marker stayed out of stderr. The malformed-port case emitted the generic `ImproperlyConfigured: DATABASE_URL is invalid` with no chained `ValueError`. |
| CRM-002-R03 | `base.py` and focused settings tests. | PASS | `LANGUAGE_CODE="es-ar"`, `TIME_ZONE="America/Argentina/Cordoba"`, and `USE_TZ=True` are consistent across variants. |
| CRM-002-R04 | `format.sh`, `verify-fast.sh`, `verify-clean.sh`, harness integration, and all nine assigned commands. | PASS | Deterministic format, lint, template, types, tests, Django checks, migration drift, deployment checks, and locked/offline clean verification exist and terminate. |
| CRM-002-R05 | Probe views plus named endpoint tests for available/unavailable DB and liveness independence. | PASS | Liveness never opens a cursor; readiness executes `SELECT 1`; bodies are generic; both probes carry `no-store`; DB failure produces 503 while liveness remains 200. |

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-002-AC01 | Exact clean command created `/tmp/simple-crm-verify.WpDK30Ai/.venv`, installed 74 locked packages offline, and passed the complete 109-test suite. An independent xtrace run showed every Ruff/djLint/mypy/pytest/Python executable under `/tmp/simple-crm-verify.XPHpMMPH/.venv/bin`. | PASS | The clean verifier uses `UV_PROJECT_ENVIRONMENT`, not the repository `.venv`, and its guarded trap removes only its validated temporary path. |
| CRM-002-AC02 | Semantic template/source inspection, focused page test, README/development-settings inspection, dependency scan, and non-persistent Django client smoke. | PASS | The development settings rendered `/` as Spanish `text/html` with status 200 and `CRM de Ventas`; `lang="es-AR"`, semantic landmarks, and Spanish copy are present. No script, CDN, package manifest, or Node build dependency exists. The documented test-client equivalent is justified in place of a manual browser because it exercises the same server-rendered response without persistent state. |
| CRM-002-AC03 | Four focused endpoint tests and view inspection. | PASS | Available DB returns `200 {"status":"ready"}`; simulated `DatabaseError` returns generic `503 {"status":"unavailable"}` without the diagnostic marker; liveness stays `200 {"status":"ok"}` and its mocked cursor is not called. Both endpoints assert `Cache-Control: no-store`. |
| CRM-002-AC04 | Seventeen focused settings tests, independent negative matrix, secure settings inspection, and a valid production `check --deploy --fail-level WARNING`. | PASS | Missing secret, debug, insecure session/CSRF cookies, and invalid hosts all reject; a valid production fixture passes with no warnings. The corrected malformed-port path also rejects generically without disclosing its marker. |

## Verification

All assigned commands ran exactly from the repository root against the current
worktree:

| Exact command | Relevant output | Result |
| --- | --- | --- |
| `timeout 60s ./crm/init.sh` | `[OK] harness metadata is valid`; full fast suite; `109 passed in 1.15s`; Django and migration checks clean; `[harness] ready`. | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check .` | `All checks passed!` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check .` | `62 files already formatted` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src` | `Success: no issues found in 27 source files` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q` | `109 passed in 1.15s` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py check` | `System check identified no issues (0 silenced).` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py makemigrations --check --dry-run` | `No changes detected` | PASS |
| `UV_CACHE_DIR=/tmp/uv-cache timeout 120s bash scripts/verify-clean.sh` | Created `/tmp/simple-crm-verify.WpDK30Ai/.venv`; installed 74 locked packages; Ruff/djLint/mypy, `109` tests, Django, migration, and deploy checks passed. | PASS |
| `git diff --check` | No output; exit 0. | PASS |

Additional focused evidence:

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -vv
  tests/config/test_settings.py` collected and passed 17 tests, including all
  four settings imports and the malformed-port marker regression.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -vv
  tests/platform/test_pages_and_health.py` passed all four named page/probe
  tests.
- `DJANGO_SETTINGS_MODULE=simple_crm.config.settings.development
  PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -c '<Django test-client smoke>'`
  printed `200 True text/html; charset=utf-8`.
- The valid production `manage.py check --deploy --fail-level WARNING` fixture
  printed `System check identified no issues (0 silenced).`
- `env SHELLOPTS=xtrace UV_CACHE_DIR=/tmp/uv-cache bash
  scripts/verify-clean.sh 2>&1 | rg '<temporary executable paths>'` showed
  `VENV_BIN=/tmp/simple-crm-verify.XPHpMMPH/.venv/bin` followed by invocations
  of that directory's `ruff`, `djlint`, `mypy`, `pytest`, and `python`,
  including the deployment check.
- The independent 12-case production import matrix exited 0. Every case,
  including absent secret, enabled debug, insecure cookies, invalid hosts,
  malformed/non-PostgreSQL URLs, and malformed port, reported
  `rejected=True, leak_free=True, no_chained_value_error=True`.
- Direct malformed-port reproduction exited 1 as required and emitted only
  `django.core.exceptions.ImproperlyConfigured: DATABASE_URL is invalid`.
  Neither `port-leak-marker` nor a chained `ValueError` appeared.

## Findings

- Security: the prior malformed-port disclosure is resolved at
  `src/simple_crm/config/environment.py:81-84` by raising the generic
  configuration exception from `None`. The new marker-based regression at
  `tests/config/test_settings.py:153-162` exercises the exact parser failure.
  No unresolved secret, configuration-value, or health-diagnostic disclosure
  was found.
- Architecture: component ownership, deployed PostgreSQL boundary,
  server-rendered UI, environment split, and stable health interfaces match
  `crm/docs/architecture.md`.
- Scope: no business-domain model, application migration, cloud deployment
  configuration, package-manager frontend build, or external UI asset was
  found. Accumulated CRM-001/CRM-023 harness changes are distinguishable from
  the CRM-002 application scope and were not altered. The pre-existing staged
  deletion of `src/simple_crm/__pycache__/__init__.cpython-312.pyc` remains
  staged and preserved.
- Regression: all 109 tests and every assigned static/system/lockfile command
  pass. No unresolved scope, security, architecture, or regression finding
  remains.
