# Implementation report — CRM-010

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the intentionally dirty completed-feature worktree recorded in `progress/current.md`.
- Requirement IDs: CRM-010-R01 through CRM-010-R06
- Acceptance-criterion IDs: CRM-010-AC01 through CRM-010-AC05
- Allowed scope: data-quality staging models/services/admin, migration, documentation, focused tests, and this report.
- Out-of-scope files: feature/session/history state, validator report, identity/activity/platform/reporting apps, CRM-011 matching/merge, CRM-021 cutover, direct migration database editing, automatic ambiguous correction, and production data loading.
- Dependencies and assumptions: CRM-006 and CRM-007 are done; `openpyxl` is already a locked project dependency. Canonical correction remains a later governed workflow.
- Persisted assignment: `crm010_import_implementer_terra`, `gpt-5.6-terra`, high reasoning.
- Runtime note: this environment does not expose switchable model identities or a separate Terra process. The work followed the persisted Terra assignment and the discrepancy is recorded rather than silently substituting an inherited assignment.

## Changed files and decisions

- `src/simple_crm/data_quality/models.py`: added source-document bytes/checksums, versioned import batches, row-level coordinates/raw payloads/classifications, source-canonical links, and immutable import audit events.
- `src/simple_crm/data_quality/services.py`: added bounded `.xlsx` parsing, Spanish validation failures, formula-error retention, duplicate-row classification, preview counters, checksum/version idempotency, steward authorization, approval, and atomic applied-state transitions.
- `src/simple_crm/data_quality/admin.py`: added a read-oriented data-steward administration surface.
- `src/simple_crm/data_quality/migrations/0001_import_staging.py`: added the source/import/lineage schema and uniqueness constraints.
- `tests/data_quality/test_import_staging.py`: added five focused tests for no-preapproval canonical mutation, idempotency, lineage/raw errors, malformed and oversized uploads, steward approval/application, and append-only audits.
- `crm/docs/imports.md`, `crm/docs/architecture.md`, `crm/docs/conventions.md`, `crm/docs/verification.md`, `README.md`: documented staging states, lossless evidence, idempotency, authorization, and the canonical-write boundary.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-010-AC01 | Preview creates only source document, batch, row, and audit records; canonical CRM services are not called before approval. | Focused preview test asserts zero parties and leads after staging. | Pass |
| CRM-010-AC02 | Unique checksum/parser/application-version constraint returns the existing batch on rerun without new rows or upload audit duplication. | Focused idempotency test passes. | Pass |
| CRM-010-AC03 | Source rows retain workbook sheet, row coordinate, raw JSON-safe payload, row checksum, classification, errors, warnings, links, and rejection reason. | Focused lineage test inspects exact sheet/coordinate/payload and formula-error evidence. | Pass |
| CRM-010-AC04 | Upload size/type/parser/header validation is bounded and Spanish; Excel error cells remain raw and classify as row errors. | Focused malformed, unexpected-header, formula-error, and oversized tests pass. | Pass |
| CRM-010-AC05 | Steward role plus global import scope is required; approval and application require separate reasons, states, and audit events. | Focused permission/state/audit test rejects manager actions and verifies uploaded/approved/applied sequence. | Pass |

## Verification

Exact commands run:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format src/simple_crm/data_quality tests/data_quality/test_import_staging.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src/simple_crm/data_quality
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test .venv/bin/python manage.py check
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test .venv/bin/python manage.py makemigrations --check --dry-run
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/data_quality/test_import_staging.py
timeout 60s ./crm/init.sh
git diff --check
```

Relevant output:

```text
Success: no issues found in 66 source files
173 passed, 13 warnings in 4.13s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
5 passed in 1.30s
```

The thirteen warnings are the existing non-fatal WhiteNoise warning for the
absent default `staticfiles/` directory during test-client setup.

## Risks and follow-up

- The current feature intentionally applies approved staging state and lineage
  without guessing canonical entities; CRM-011/CRM-021 own governed matching,
  correction, and cutover application.
- PostgreSQL-specific runtime evidence for the new uniqueness constraints
  remains a staging follow-up when Docker/PostgreSQL access is available.
- CRM-010 is implemented but is not approved or marked done by this report;
  independent validator review is required.
