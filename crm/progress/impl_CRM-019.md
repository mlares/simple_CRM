# Implementation report — CRM-019

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the preserved
  completed-feature worktree.
- Requirement IDs: CRM-019-R01 through CRM-019-R06.
- Acceptance-criterion IDs: CRM-019-AC01 through CRM-019-AC05.
- Allowed scope: the CRM-019 task envelope, including deployment settings,
  security middleware, identity redirect handling, bounded import filename
  handling, security tests, documentation, `scripts/verify-security.sh`, and
  the opt-in PostgreSQL role/RLS acceptance procedure.
- Out-of-scope files: feature state, session state, task envelope, validator
  report, agent definitions, and the separate PostgreSQL deployment itself.
- Dependencies and assumptions: CRM-003, CRM-005, CRM-015, CRM-016, and
  CRM-017 are done. PostgreSQL role/RLS evidence requires a disposable
  PostgreSQL deployment with separately provisioned roles and is recorded as a
  release prerequisite rather than simulated in SQLite.

The persisted assignment names `crm019_security_implementer_terra` using
`gpt-5.6-terra` with high reasoning effort. This environment does not expose
separate Terra/Sol runtime processes, so the role was executed sequentially by
the available Codex runtime under the persisted assignment; the discrepancy
is recorded here as required by the agent contract.

## Changed files and decisions

- `src/simple_crm/config/security.py`: added response security headers and
  cache-backed, generic 429 request limits.
- `src/simple_crm/config/settings/base.py`: added restrictive self-hosted CSP,
  Permissions-Policy, 10 MiB request/upload bounds, and rate-limit rules. The
  existing WhiteNoise position was preserved to retain the static contract.
- `src/simple_crm/config/settings/_deployment.py`: added same-origin
  referrer, COOP, and CORP deployment defaults alongside HTTPS, cookie, HSTS,
  and framing controls.
- `src/simple_crm/identity/views.py`: validates local and OIDC continuation
  redirects against the current host.
- `src/simple_crm/data_quality/services.py`: normalizes and bounds uploaded
  workbook filenames before persistence or audit logging.
- `tests/config/test_security_headers.py`: covers headers, production
  settings, generic rate limiting, and malicious filename rejection.
- `tests/identity/test_authentication.py`: covers rejection of an external
  local-login continuation URL.
- `tests/data_quality/test_import_staging.py`: retains the existing bounded
  upload, malformed workbook, formula-error, and steward-gate regressions.
- `scripts/verify-security.sh`: runs Ruff, mypy, Django deployment checks, and
  a strict pip-audit over exact-version, non-editable installed dependencies.
  The generated temporary requirements file avoids falsely auditing the local
  editable `simple-crm` source distribution.
- `scripts/verify-postgres-security.sh`: opt-in PostgreSQL 18 acceptance
  procedure that provisions temporary non-superuser migrator, web, worker,
  and reporting roles; verifies grants, DDL/role denial, governed reporting,
  and campaign-scoped lead RLS; then removes temporary roles and security
  objects without bypassing immutable catalog guards.
- `tests/integration/test_verify_postgres_security_script.py`: verifies the
  PostgreSQL security procedure is explicitly gated and non-disclosing.
- `crm/docs/security.md`: documents the ASVS 5.0 Level 2 target, threat model,
  secrets boundary, database-role/RLS acceptance boundary, and release checks.
- `crm/docs/architecture.md`, `crm/docs/conventions.md`, and
  `crm/docs/verification.md`: cross-reference the security controls and
  release verification boundary.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-019-AC01 | Existing centralized authorization/CSRF/formula controls plus safe redirect, upload filename, and rate-limit regressions | Focused security suite: 14 passed; full suite: 216 passed | PASS |
| CRM-019-AC02 | Production security settings and response-header middleware | `manage.py check --deploy --fail-level WARNING`; header tests; full harness pass | PASS |
| CRM-019-AC03 | Least-privilege role/RLS procedure and PostgreSQL-only boundary documented in `crm/docs/security.md`; executable `scripts/verify-postgres-security.sh` | PostgreSQL 18 disposable acceptance passed: role grants, web DDL/role denial, governed reporting access, worker/migrator grants, and campaign-scoped lead RLS | PASS |
| CRM-019-AC04 | Strict static/dependency/security verification script | `bash scripts/verify-security.sh`; pip-audit: `No known vulnerabilities found` | PASS |
| CRM-019-AC05 | Generic authentication and rate-limit errors, safe redirect handling, and existing authorization/error contracts | Focused suite and full suite pass; no stack/secret details in tested generic responses | PASS |

## Verification

Exact verification performed on 2026-08-13:

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/config/test_security_headers.py tests/identity/test_authentication.py tests/data_quality/test_import_staging.py`
  — `14 passed, 7 warnings`.
- `timeout 120s ./crm/init.sh` — harness metadata valid; Ruff, formatting,
  mypy, `216 passed`, Django checks, migration drift, repository safety, and
  vendored assets passed.
- `bash scripts/verify-security.sh` with network access — Ruff, mypy, Django
  deployment checks, and pip-audit passed; `No known vulnerabilities found`.
- `DATABASE_URL='postgresql://…/simple_crm_crm019_security_test' SIMPLE_CRM_POSTGRES_SECURITY_ACCEPTANCE=1 CRM019_MIGRATOR_PASSWORD='(temporary)' CRM019_WEB_PASSWORD='(temporary)' CRM019_WORKER_PASSWORD='(temporary)' CRM019_REPORTING_PASSWORD='(temporary)' timeout 120s bash scripts/verify-postgres-security.sh` — `PostgreSQL security acceptance passed: role grants and lead RLS` against a disposable PostgreSQL 18 container. Temporary credentials were supplied in the process environment and are not persisted here.
- `git diff --check` — passed.

## Risks and follow-up

- Rate limits require a shared production cache for consistency across web
  processes.
- The full harness reports warnings for the absent local `staticfiles/`
  directory; this is an existing test-environment warning and not a failed
  check.
