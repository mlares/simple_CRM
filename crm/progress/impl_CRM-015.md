# Implementation report — CRM-015

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the intentionally
  dirty completed-feature worktree recorded in `progress/current.md`.
- Requirement IDs: CRM-015-R01 through CRM-015-R05
- Acceptance-criterion IDs: CRM-015-AC01 through CRM-015-AC05
- Allowed scope: export request/artifact models, bounded CSV/XLSX services,
  audit/expiry behavior, migration, focused tests, docs, and this report.
- Dependencies and assumptions: CRM-005, CRM-013, and CRM-014 are done.
  `execute_definition` remains the scope-first query boundary.
- Persisted assignment: `crm015_exports_implementer_terra`, `gpt-5.6-terra`,
  high reasoning.
- Runtime note: this environment does not expose switchable model identities or
  a separate Terra process. The work followed the persisted assignment and the
  discrepancy is recorded rather than silently substituting an inherited
  assignment.

## Changed files and decisions

- `src/simple_crm/reporting/models.py` and
  `src/simple_crm/reporting/migrations/0003_exports.py`: added export request
  state, immutable structured/scope/field snapshots, idempotency, checksum,
  expiry, bounded attempts, payload state, and append-only audit events.
- `src/simple_crm/reporting/exports.py`: added separate `BULK_EXPORT` gating,
  denial auditing, snapshot/idempotency handling, current-scope materialization,
  safe explicit field layouts, CSV/XLSX serialization, formula neutralization,
  expiry, checksum, and download audit.
- `tests/reporting/test_exports.py`: added permission, snapshot, idempotency,
  CSV/XLSX, formula-control, redaction, expiry, and download tests.
- `crm/docs/exports.md` plus architecture/convention/verification docs:
  documented file, scope, audit, and expiry boundaries.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-015-AC01 | Separate `BULK_EXPORT` gate for requests, materialization, and downloads plus denial audit. | View-capable sales manager cannot request; denied audit is retained. | Pass |
| CRM-015-AC02 | Immutable definition/field snapshot and current-scope re-evaluation on materialization. | Repeated idempotency request returns one request and mutated caller definition does not alter snapshot. | Pass |
| CRM-015-AC03 | Explicit safe CSV/XLSX columns and `_safe_cell` formula-control neutralization. | CSV vector and XLSX fixture tests pass; sensitive party/contact fields are not in the layout. | Pass |
| CRM-015-AC04 | READY/EXPIRED state, expiry timestamp, bounded artifact, checksum, and retained audit rows. | Expired download is denied and request state changes to EXPIRED while metadata remains. | Pass |
| CRM-015-AC05 | Requested/denied/materialized/failed/downloaded append-only audit events with metadata only. | Audit assertions pass without storing file contents in event metadata. | Pass |

## Verification

Exact commands run:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format src/simple_crm/reporting/models.py src/simple_crm/reporting/exports.py src/simple_crm/reporting/migrations/0003_exports.py tests/reporting/test_exports.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check src/simple_crm/reporting src/simple_crm/platform tests/reporting/test_exports.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src/simple_crm/reporting src/simple_crm/platform
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py makemigrations --check --dry-run
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/reporting/test_exports.py
timeout 60s ./crm/init.sh
```

Relevant output:

```text
All checks passed!
Success: no issues found in 18 source files
No changes detected
3 passed in 1.60s
193 passed, 19 warnings in 5.14s
[harness] ready
```

The warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Risks and follow-up

- Large exports are bounded to 10,000 rows; a later worker feature owns durable
  polling/leases and deployment-scale processing.
- PostgreSQL-volume performance and storage-retention evidence remains a
  staging follow-up; generic verification uses SQLite.
- CRM-015 is implemented but not yet approved or marked done; independent
  validator review is required.
