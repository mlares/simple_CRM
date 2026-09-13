# Implementation report — `CRM-002`

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188`; resumed dirty worktree
  after CRM-001 and CRM-023. The pre-existing staged deletion of
  `src/simple_crm/__pycache__/__init__.cpython-312.pyc` was preserved.
- Requirement IDs: CRM-002-R01, CRM-002-R02, CRM-002-R03, CRM-002-R04,
  CRM-002-R05.
- Acceptance-criterion IDs: CRM-002-AC01, CRM-002-AC02, CRM-002-AC03,
  CRM-002-AC04.
- Assignment: `crm002_foundation_implementer_terra`, model
  `gpt-5.6-terra`, reasoning effort `high`, source `role_default`.
- Actual runtime: `gpt-5.6-terra`, reasoning effort `high`. No assignment
  discrepancy was observed.
- Allowed scope: the CRM-002 envelope paths only; this run changed
  `scripts/verify-fast.sh` and this report.
- Out of scope: feature/session state, task envelope, validator report,
  agent/harness infrastructure, `crm/tests`, bytecode cache, business models
  and migrations, and cloud deployment.
- Dependencies and assumptions: CRM-001 and CRM-023 were complete; the
  existing CRM-002 Django foundation was retained and audited rather than
  rewritten.

## Changed files and decisions

- `scripts/verify-fast.sh`: select its tool executables from
  `UV_PROJECT_ENVIRONMENT` when provided, falling back to the conventional
  project `.venv` for direct fast verification. This makes the temporary
  environment created by `verify-clean.sh` the environment that actually runs
  Ruff, djLint, mypy, pytest, and Django.
- `crm/progress/impl_CRM-002.md`: record scope, assignment, and verification
  evidence.

The already-present foundation was audited as follows: the `src/simple_crm`
layout has explicit config, CRM, activity, data-quality, reporting, identity,
and platform apps; settings use Spanish, time-zone-aware datetime support and
Córdoba time; staging/production parsing is fail-closed; and the landing page
and probes are server-rendered, Spanish, non-diagnostic, and require no build
tool or CDN.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-002-AC01 | `verify-clean.sh` creates `UV_PROJECT_ENVIRONMENT` under guarded `mktemp`; fast verification now consumes that variable. | Clean locked/offline run installed 74 packages into `/tmp/simple-crm-verify.hroZDSET/.venv` and completed the full suite. A traced clean run showed `UV_PROJECT_ENVIRONMENT=/tmp/simple-crm-verify.iYvTXMzM/.venv` and `VENV_BIN=/tmp/simple-crm-verify.iYvTXMzM/.venv/bin`. | PASS |
| CRM-002-AC02 | `platform/home.html` is semantic Spanish HTML with `lang="es-AR"`; it has no script/CDN dependency. Development settings are the `manage.py` default and are documented in README and verification docs. | `tests/platform/test_pages_and_health.py::test_home_page_is_semantic_spanish_html` passed as part of 108 tests. | PASS |
| CRM-002-AC03 | Liveness is dependency-free; readiness performs `SELECT 1`, returns only generic JSON, and is non-cached. | The platform test module passed available/unavailable database and liveness-independence coverage as part of 108 tests. | PASS |
| CRM-002-AC04 | Deployed settings require strong secret, exact hosts, and a PostgreSQL URL; reject debug and insecure cookie overrides; they enforce HTTPS/cookie/HSTS headers. | Isolated settings negative cases passed in pytest; the fast suite's fixture production `check --deploy --fail-level WARNING` passed. | PASS |

## Verification

All commands below ran from the repository root. `PYTHONDONTWRITEBYTECODE=1`
was retained where prescribed.

| Command | Relevant output | Result |
| --- | --- | --- |
| `timeout 60s ./crm/init.sh` | Harness metadata valid; complete fast suite passed; `108 passed`; Django checks clean. | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check .` | `All checks passed!` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check .` | `60 files already formatted` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src` | `Success: no issues found in 27 source files` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q` | `108 passed in 1.11s` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py check` | `System check identified no issues (0 silenced).` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py makemigrations --check --dry-run` | `No changes detected` | PASS |
| `UV_CACHE_DIR=/tmp/uv-cache timeout 120s bash scripts/verify-clean.sh` | Created isolated `/tmp/simple-crm-verify.hroZDSET/.venv`, installed 74 locked packages, then passed lint, template, types, `108` tests, checks, migration drift, and deployment check. | PASS |
| `git diff --check` | No output. | PASS |

Additional direct clean-environment proof (diagnostic only, not a source
change): `BASH_ENV=/tmp/simple-crm-bash-trace.sh UV_CACHE_DIR=/tmp/uv-cache
bash scripts/verify-clean.sh` was traced with a temporary `set -x` file that
was removed immediately afterward. Its relevant output was:

```text
+ export UV_PROJECT_ENVIRONMENT=/tmp/simple-crm-verify.iYvTXMzM/.venv
+ UV_PROJECT_ENVIRONMENT=/tmp/simple-crm-verify.iYvTXMzM/.venv
+ VENV_BIN=/tmp/simple-crm-verify.iYvTXMzM/.venv/bin
```

## Risks and follow-up

- The clean verifier deliberately requires the dependencies to be present in
  the local UV cache and runs offline; an unavailable cache is an external
  verification blocker, not a reason to use an unlocked or network-dependent
  command.
- PostgreSQL integration, migrations, locally vendored frontend assets, and
  cloud deployment remain explicitly owned by later features. No approval or
  feature-state transition is made by this implementer report.

## Correction cycle — malformed-port disclosure

- Persisted correction assignment: `crm002_orchestrator`, model
  `gpt-5.6-sol`, reasoning effort `high`, source `override`.
- Actual correction runtime: `gpt-5.6-sol`, reasoning effort `high`; no
  discrepancy was observed.
- Override reason: the runtime agent-thread limit prevented spawning or
  reactivating any Terra/high implementer. The task envelope therefore
  authorized the existing Sol/high orchestrator to switch sequentially to the
  implementer role for this bounded revision before returning to orchestration.
- Independent validator remains `crm002_foundation_validator`; this correction
  did not modify its report or perform revalidation.

### Changes and security evidence

- `src/simple_crm/config/environment.py`: suppress the chained `urllib`
  `ValueError` when a URL port cannot be parsed. The public startup failure
  remains `ImproperlyConfigured: DATABASE_URL is invalid`, while raw port text
  is no longer copied into stderr.
- `tests/config/test_settings.py`: add a production-import case whose malformed
  port contains `port-leak-marker`; the test requires rejection, the generic
  `DATABASE_URL` error, and absence of the marker.
- Direct reproduction exited 1 as required and emitted only the generic Django
  configuration exception; `port-leak-marker` was absent. The focused command
  `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q
  tests/config/test_settings.py` passed all 17 tests.

### Refreshed exact verification

| Command | Relevant output | Result |
| --- | --- | --- |
| `timeout 60s ./crm/init.sh` | Harness metadata valid; full suite passed with `109 passed`; Django checks clean. | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check .` | `All checks passed!` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check .` | `62 files already formatted` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src` | `Success: no issues found in 27 source files` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q` | `109 passed in 1.15s` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py check` | `System check identified no issues (0 silenced).` | PASS |
| `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py makemigrations --check --dry-run` | `No changes detected` | PASS |
| `UV_CACHE_DIR=/tmp/uv-cache timeout 120s bash scripts/verify-clean.sh` | Created `/tmp/simple-crm-verify.JIZotRnX/.venv`, installed 74 locked packages, and passed the full suite with `109 passed`. | PASS |
| `git diff --check` | No output. | PASS |

The correction resolves the sole blocking validation finding. It does not
approve the feature; independent revalidation is still required.
