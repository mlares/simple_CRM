# Implementation report — CRM-017

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the intentionally
  dirty completed-feature worktree recorded in `progress/current.md`.
- Requirement IDs: CRM-017-R01 through CRM-017-R05
- Acceptance-criterion IDs: CRM-017-AC01 through CRM-017-AC05
- Persisted implementer assignment: `crm017_jobs_implementer_terra`,
  `gpt-5.6-terra`, high reasoning.
- Runtime note: this environment does not expose switchable model identities or
  a separate Terra process. The implementation followed the persisted role
  assignment and records that discrepancy rather than silently substituting an
  inherited assignment.

## Changed files and decisions

- `src/simple_crm/platform/models.py` and
  `src/simple_crm/platform/migrations/0002_outbox.py`: added durable outbox
  jobs, safe payload references, idempotency/provider keys, leases, bounded
  attempts, notification receipts, and per-identity preferences.
- `src/simple_crm/platform/jobs.py`: added task reminder replacement and
  cancellation, PostgreSQL skip-locked polling when supported, lease recovery,
  retry backoff, dead-letter states, idempotent delivery receipts, safe error
  summaries, preference authorization, and redacted operator projections.
- `src/simple_crm/activity/services.py`: reminder creation now shares the
  quick-contact transaction; completion, rescheduling, and the new governed
  cancellation service update reminders in the same transaction.
- `src/simple_crm/platform/views.py`, `urls.py`, and
  `templates/platform/notifications.html`: added Spanish notification
  settings and permission-gated operational review.
- `tests/platform/test_jobs.py` and `test_notifications_page.py`: added
  idempotency, lease/retry/dead-letter, sender failure, task lifecycle,
  preference, redaction, and rendered-page coverage.
- `crm/docs/jobs.md` plus architecture, convention, and verification updates:
  documented the outbox boundary and deployment contract.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-017-AC01 | Unique reminder idempotency keys and one-to-one delivery receipts make repeated scheduling/processing one-row operations. | `test_reminder_idempotency_and_worker_delivery_receipt` passes. | Pass |
| CRM-017-AC02 | Bounded claims carry leases and attempts; expired claims retry or dead-letter, while provider keys remain stable across retries. | `test_claim_lease_recovery_retry_and_dead_letter_are_bounded` and sender-failure test pass. | Pass |
| CRM-017-AC03 | Quick contact creates a reminder atomically; complete/cancel cancel obsolete jobs and reschedule replaces the old key. | `test_task_lifecycle_replaces_and_cancels_obsolete_reminders` passes. | Pass |
| CRM-017-AC04 | Digest defaults on, escalation requires administrative permission, and a labeled Spanish settings page persists allowed changes. | Preference assertions and `test_notification_settings_page_preserves_spanish_labels_and_saves_digest` pass. | Pass |
| CRM-017-AC05 | Operator projection exposes operational fields and reference field names only; payload values and provider keys are omitted. | `test_operator_projection_requires_scope_and_redacts_payload_values` passes. | Pass |

## Verification

Exact commands run:

```text
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
8 passed, 1 warning in 2.13s
Success: no issues found in 81 source files
204 passed, 20 warnings in 5.86s
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
```

The warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Risks and follow-up

- The worker adapter intentionally performs an internal receipt rather than
  contacting a real email/SMS provider. Production provider integration must
  pass and persist the same provider idempotency key before claiming delivery.
- SQLite verifies service behavior; PostgreSQL row-lock, skip-locked, and
  database-constraint evidence should be run on the dedicated acceptance
  database when Docker/PostgreSQL access is available.
- The scheduled worker loop is separately deployable through repeated
  `run_worker_once()` calls; process supervision and metrics belong to later
  operations work.
