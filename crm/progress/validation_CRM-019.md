# Validation report — CRM-019

## Verdict

`APPROVED`

## Independence and scope

- Validator: `crm019_security_validator_sol` (`gpt-5.6-sol`, high reasoning
  effort, persisted assignment).
- Implementer: `crm019_security_implementer_terra` (`gpt-5.6-terra`, high
  reasoning effort, persisted assignment).
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188` plus the
  preserved completed-feature worktree.
- Allowed validator write target: `progress/validation_CRM-019.md`.

The runtime does not expose separate Sol/Terra processes. The validator lane
was executed sequentially by the available Codex runtime; the role separation
and persisted assignment IDs remain independent, and no implementation files
were changed by this validation pass.

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-019-AC01 | Security middleware, redirect validation, safe filename handling, existing authorization/CSRF/formula tests, focused suite, and full suite | PASS | 14 focused tests and 216 full-suite tests passed. |
| CRM-019-AC02 | Deployment settings, header middleware, security tests, and production Django check | PASS | Expected HTTPS, cookie, HSTS, framing, referrer, COOP/CORP, CSP, and Permissions-Policy controls are present in code and checks. |
| CRM-019-AC03 | `crm/docs/security.md`, `scripts/verify-postgres-security.sh`, and its integration contract test | PASS | Disposable PostgreSQL 18 acceptance passed: temporary non-superuser role grants, web DDL/role denial, governed reporting access, worker/migrator boundaries, and campaign-scoped lead RLS. |
| CRM-019-AC04 | `scripts/verify-security.sh` and network-enabled execution | PASS | Static checks passed and pip-audit reported `No known vulnerabilities found`; the script correctly excludes only the editable local project via an exact-version temporary requirements input. |
| CRM-019-AC05 | Generic error tests, redirect/state checks, rate-limit response assertions, and full suite | PASS | Tested responses do not disclose stack/secret details; existing scope and authorization regression coverage remains green. |

## Verification

- `timeout 120s ./crm/init.sh` — passed: harness metadata, Ruff, formatting,
  mypy, 216 tests, Django checks, migration drift, repository safety, and
  vendored assets.
- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/config/test_security_headers.py tests/identity/test_authentication.py tests/data_quality/test_import_staging.py`
  — `14 passed, 7 warnings`.
- `bash scripts/verify-security.sh` — passed with network access; pip-audit
  reported `No known vulnerabilities found`.
- `DATABASE_URL='postgresql://…/simple_crm_crm019_security_test' SIMPLE_CRM_POSTGRES_SECURITY_ACCEPTANCE=1 CRM019_MIGRATOR_PASSWORD='(temporary)' CRM019_WEB_PASSWORD='(temporary)' CRM019_WORKER_PASSWORD='(temporary)' CRM019_REPORTING_PASSWORD='(temporary)' timeout 120s bash scripts/verify-postgres-security.sh` — passed against a disposable PostgreSQL 18 container with `PostgreSQL security acceptance passed: role grants and lead RLS`.
- `git diff --check` — passed.

## Findings

The implementation is within the delegated security scope and follows the
documented Django/ORM boundaries. The prior AC03 finding was resolved by the
opt-in PostgreSQL 18 acceptance procedure and successful disposable-database
run. The procedure retains immutable catalog/audit rows in the disposable
database rather than bypassing governance triggers; the database is discarded
after the run. No unresolved scope, security, architecture, or regression
finding remains. Production deployment still requires a shared cache for
consistent rate limits and secret-facility-managed credentials.
