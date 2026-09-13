# Implementation report — CRM-011

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the intentionally dirty completed-feature worktree recorded in `progress/current.md`.
- Requirement IDs: CRM-011-R01 through CRM-011-R06
- Acceptance-criterion IDs: CRM-011-AC01 through CRM-011-AC05
- Allowed scope: data-quality issue/candidate/merge models, services, admin, migration, documentation, focused tests, and this report.
- Out-of-scope files: feature/session/history state, validator report, identity/activity/platform/reporting apps, search, cutover, destructive source deletion, fully automatic fuzzy resolution, and clinical identities.
- Dependencies and assumptions: CRM-006, CRM-007, and CRM-010 are done. `simple_crm.data_quality` remains the owner of quality review and lineage; canonical merge is service-bounded.
- Persisted assignment: `crm011_quality_implementer_terra`, `gpt-5.6-terra`, high reasoning.
- Runtime note: this environment does not expose switchable model identities or a separate Terra process. The work followed the persisted Terra assignment and the discrepancy is recorded rather than silently substituting an inherited assignment.

## Changed files and decisions

- `src/simple_crm/data_quality/models.py`: added prioritized quality issues, exact/fuzzy candidate matches, review states, confidence/evidence, and immutable before/after/source audit events.
- `src/simple_crm/data_quality/services.py`: added queue/state services, deterministic exact contact matching, evidence-ranked fuzzy candidate creation, review decisions, merge preview, and atomic approved merge.
- `src/simple_crm/data_quality/admin.py`: added read-oriented issue/candidate/audit administration.
- `src/simple_crm/data_quality/migrations/0002_quality_merge.py`: added quality and governed-merge schema constraints.
- `tests/data_quality/test_quality_merge.py`: added three focused tests for queue/state/audit behavior, review-only matching, and related-record/suppression/source preservation through approved merge.
- `crm/docs/quality.md`, `crm/docs/architecture.md`, `crm/docs/conventions.md`, `crm/docs/verification.md`, `README.md`: documented evidence, approval, preview, merge, suppression, alias, and lineage boundaries.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-011-AC01 | `QualityIssue` severity/state/owner/reason fields, deterministic queue ordering, allowed transitions, and audit events. | Focused queue test resolves, accepts with reason, and reopens issues. | Pass |
| CRM-011-AC02 | Exact matching creates review candidates; fuzzy matching stores confidence/evidence and merge requires explicit approved state. | Focused fuzzy test proves no canonical lifecycle change before approval. | Pass |
| CRM-011-AC03 | `MergePreview` enumerates lead links, interaction participants, tasks, contact links, aliases, and source-canonical links. | Focused fixture-backed preview test inspects related records. | Pass |
| CRM-011-AC04 | Approved merge locks parties, redirects non-conflicting links, preserves contact suppression/source lineage, creates alias, and archives duplicate. | Focused merge invariant test passes. | Pass |
| CRM-011-AC05 | Immutable quality audit stores actor, reason, before state, after state, and source evidence for issue/candidate/merge decisions. | Focused audit assertions pass, including `party_merged`. | Pass |

## Verification

Exact commands run:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format src/simple_crm/data_quality tests/data_quality/test_quality_merge.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src/simple_crm/data_quality
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test .venv/bin/python manage.py check
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test .venv/bin/python manage.py makemigrations --check --dry-run
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/data_quality/test_quality_merge.py
timeout 60s ./crm/init.sh
git diff --check
```

Relevant output:

```text
Success: no issues found in 67 source files
176 passed, 13 warnings in 4.45s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
3 passed in 1.50s
```

The thirteen warnings are the existing non-fatal WhiteNoise warning for the
absent default `staticfiles/` directory during test-client setup.

## Risks and follow-up

- Merge conflicts are rejected for explicit steward resolution; no fuzzy or
  ambiguous relationship is silently discarded.
- PostgreSQL-specific runtime evidence for quality constraints remains a
  staging follow-up when Docker/PostgreSQL access is available.
- CRM-011 is implemented but is not approved or marked done by this report;
  independent validator review is required.
