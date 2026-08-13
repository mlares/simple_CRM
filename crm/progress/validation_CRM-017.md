# Validation report — CRM-017

## Verdict

`APPROVED`

## Independence and scope

- Validator: `crm017_jobs_validator_sol`
- Persisted validator assignment: `gpt-5.6-sol`, high reasoning; the
  implementer assignment was the distinct
  `crm017_jobs_implementer_terra` / `gpt-5.6-terra`.
- Runtime note: this environment does not expose switchable model identities
  or a separate validator process. The validator pass was executed after the
  implementation phase against the actual files and test results, with no
  implementation-file edits; the discrepancy is recorded rather than silently
  substituted.
- Implementer: `crm017_jobs_implementer_terra`
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188` plus the dirty
  worktree baseline recorded in the task envelope.
- Validator write target: `progress/validation_CRM-017.md`

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-017-AC01 | Unique outbox idempotency key, replacement logic, one-to-one delivery receipt, and stable provider key. | Pass | Repeated scheduling and processing leave one reminder and one receipt. |
| CRM-017-AC02 | Bounded claim transaction, PostgreSQL skip-locked branch, leases, exponential bounded backoff, safe errors, and dead-letter transition. | Pass | Lease-expiry and max-attempt tests pass; crash-after-receipt retry reuses the same provider key and receipt. PostgreSQL runtime locking remains an acceptance-database follow-up. |
| CRM-017-AC03 | Quick-contact, completion, reschedule, and governed cancellation transaction seams. | Pass | Obsolete reminders are cancelled and rescheduling creates a replacement; rollback behavior is protected by the existing atomic service boundary. |
| CRM-017-AC04 | Default preference model, restricted escalation service, and Spanish settings route/template. | Pass | Sellers can change digest/hour for themselves; escalation and cross-user changes require administrative elevation. |
| CRM-017-AC05 | Global audit-scoped operator projection and settings rendering. | Pass | Only job metadata and reference field names are exposed; payload values, message bodies, and provider keys are absent. |

## Verification

Exact commands run independently:

```text
python3 crm/scripts/harness_check.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/djlint src/simple_crm/platform/templates --check
PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/platform/test_jobs.py tests/platform/test_notifications_page.py
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py check
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py makemigrations --check --dry-run
timeout 60s ./crm/init.sh
git diff --check
```

Relevant output:

```text
[OK] harness metadata is valid
All checks passed!
164 files already formatted
Success: no issues found in 81 source files
8 passed, 1 warning in 2.13s
204 passed, 20 warnings in 5.86s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
```

The warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Findings

- Scope: implementation is limited to platform outbox and preference models,
  worker services, activity lifecycle hooks, Spanish settings, tests, and
  documented deployment boundaries. No broker, marketing campaign, or
  external-provider dependency was added.
- Security: reminder payloads contain only stable IDs; operator output uses a
  redacted projection; safe error summaries omit exception arguments and
  credentials; authorization uses the centralized identity policy.
- Data integrity: the migration is drift-free, idempotency and receipt keys
  are unique, attempts are database-bounded, and task/job changes share the
  caller's transaction.
- Review correction: final validation includes the state-shape correction that
  permits a cancelled job to retain its provider idempotency key, which is
  required for an immutable cancellation trail.
- Environment limitation: SQLite validates service behavior; PostgreSQL
  skip-locked concurrency and database-level constraint evidence remain a
  staging acceptance follow-up because no PostgreSQL runtime is available in
  this environment.
- No unresolved changes requested.
