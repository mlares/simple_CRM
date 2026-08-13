# Implementation report — CRM-007

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the intentionally dirty completed-feature worktree recorded in `progress/current.md`.
- Requirement IDs: CRM-007-R01 through CRM-007-R06
- Acceptance-criterion IDs: CRM-007-AC01 through CRM-007-AC05
- Allowed scope: CRM lead models, lifecycle services, admin read surface, migration, documentation, focused tests, and this report.
- Out-of-scope files: feature/session/history state, validator report, identity/activity/data-quality/reporting/platform apps, detailed CRM-008 tasks/interactions, imports, merges, revenue, quotes, contracts, and clinical identities.
- Dependencies and assumptions: CRM-004, CRM-005, and CRM-006 are done; `simple_crm.crm` owns the lead aggregate while CRM-005 identity policy owns scope decisions. Minimal next-action fields bridge to CRM-008.
- Persisted assignment: `crm007_lead_implementer_terra`, `gpt-5.6-terra`, high reasoning.
- Runtime note: this environment does not expose switchable model identities or a separate Terra process. The work followed the persisted Terra assignment and the discrepancy is recorded rather than silently substituting an inherited assignment.

## Changed files and decisions

- `src/simple_crm/crm/models.py`: added `Lead`, explicit `LeadParty`, `LeadAssignment`, and immutable `LeadStageHistory` models; added lifecycle, readiness, source, next-action, version, archival, partial uniqueness, and date constraints.
- `src/simple_crm/crm/lead_services.py`: added scope-aware atomic creation, candidate-warning preview, stage transitions, reassignment, optimistic locking, next-action validation, and scoped lead listing. Stage-history JSON fields are encoded safely before persistence.
- `src/simple_crm/crm/migrations/0005_lead_domain.py`: added the reviewed lead schema and database constraints.
- `src/simple_crm/crm/admin.py`: added bounded lead, party-link, assignment, and read-only stage-history administration.
- `tests/crm/test_lead_lifecycle.py`: added six focused tests for creation, stage policy/atomicity, primary-owner uniqueness, reassignment history, object scope, stale writes, and duplicate-candidate warnings.
- `crm/docs/lead_lifecycle.md`, `crm/docs/architecture.md`, `crm/docs/conventions.md`, `crm/docs/verification.md`, `README.md`: documented lead ownership, transitions, history, authorization, next-action policy, and verification.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-007-AC01 | Initial and transition services append history in the same transaction as the current-stage update; history records are immutable. | Focused creation and transition tests assert current stage matches latest history. | Pass |
| CRM-007-AC02 | Explicit transition matrix, nonblank reasons, closure reason, and in-progress next-action validation run before writes inside `transaction.atomic()`. | Focused test proves rejected transitions leave stage and history unchanged. | Pass |
| CRM-007-AC03 | Partial unique constraint permits at most one active assignment per lead/role; reassignment closes the previous row before creating the replacement. | Focused uniqueness and reassignment test passes on the generic SQLite suite. PostgreSQL runtime constraint evidence remains a staging follow-up. | Pass |
| CRM-007-AC04 | All mutation services and `visible_leads()` use CRM-005 action/scope policy; direct object input is re-checked after row locking. | Focused out-of-scope test rejects transition/reassignment and excludes the lead from the outsider list. | Pass |
| CRM-007-AC05 | Atomic creation validates creator/owner scope, previews existing campaign candidates, and writes lead, links, owner, source, next action, and initial history together. | Focused creation and duplicate-candidate tests pass; failed validation leaves no partial lead writes. | Pass |

## Verification

Exact commands run:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format tests/crm/test_lead_lifecycle.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check src/simple_crm/crm/models.py src/simple_crm/crm/lead_services.py tests/crm/test_lead_lifecycle.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/crm/test_lead_lifecycle.py
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test .venv/bin/python manage.py check
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test .venv/bin/python manage.py makemigrations --check --dry-run
timeout 60s ./crm/init.sh
git diff --check
```

Relevant output:

```text
All checks passed!
6 passed in 0.89s
Success: no issues found in 55 source files
159 passed, 10 warnings in 3.31s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
```

The ten warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Risks and follow-up

- The generic suite exercises the partial unique and check constraints on
  SQLite. A dedicated PostgreSQL 18 run should verify the same migration on the
  empty acceptance database when Docker/PostgreSQL access is available.
- CRM-008 should migrate the compact next-action commitment to first-class
  tasks through the documented service boundary rather than duplicating state.
- CRM-007 is implemented but is not approved or marked done by this report;
  independent validator review is required.
