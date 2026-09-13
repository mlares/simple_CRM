# Implementation report — CRM-008

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the intentionally dirty completed-feature worktree recorded in `progress/current.md`.
- Requirement IDs: CRM-008-R01 through CRM-008-R06
- Acceptance-criterion IDs: CRM-008-AC01 through CRM-008-AC05
- Allowed scope: activity models/services/admin, migration, documentation, focused tests, and this report.
- Out-of-scope files: feature/session/history state, validator report, identity/data-quality/reporting/platform apps, CRM-009 UI/navigation, imports, merges, reminders/notifications, call recording, inbox synchronization, revenue, quotes, contracts, and clinical identities.
- Dependencies and assumptions: CRM-006 and CRM-007 are done. CRM-007 remains the owner of lead stage and assignment history; CRM-008 owns activity records and the quick-contact transaction boundary.
- Persisted assignment: `crm008_activity_implementer_terra`, `gpt-5.6-terra`, high reasoning.
- Runtime note: this environment does not expose switchable model identities or a separate Terra process. The work followed the persisted Terra assignment and the discrepancy is recorded rather than silently substituting an inherited assignment.

## Changed files and decisions

- `src/simple_crm/activity/models.py`: added interactions with date-only precision, governed contact-result semantics, participant links, tasks with state/date constraints, and immutable activity audit events.
- `src/simple_crm/activity/services.py`: added scope-aware atomic `quick_contact()`, task completion/rescheduling services, semantic validation, and stable permission-scoped timeline projection.
- `src/simple_crm/activity/migrations/0001_activity_domain.py`: added the activity schema and database constraints after CRM-007.
- `src/simple_crm/activity/admin.py`: added a read-only activity/task/audit administration surface.
- `tests/activity/test_activity_lifecycle.py`: added five focused tests for atomic quick contact, placeholder rollback, task state/timezone behavior, timeline ordering/scope, and governed semantics.
- `crm/docs/activity.md`, `crm/docs/architecture.md`, `crm/docs/conventions.md`, `crm/docs/verification.md`, `README.md`: documented activity ownership, quick contact, task rules, date-only precision, and timeline behavior.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-008-AC01 | `quick_contact()` locks and scopes the lead, validates date/channel/outcome, then writes interaction, optional next task, optional CRM-007 stage update, and audit event inside one transaction. | Focused atomic creation test passes and invalid input test confirms no partial rows. | Pass |
| CRM-008-AC02 | `InteractionResult` semantics and explicit non-event text rejection prevent placeholder interactions and incompatible direction/outcome combinations. | Focused placeholder and governed-semantics tests pass; no interaction row is created for `Sin accion`. | Pass |
| CRM-008-AC03 | Task model checks require completion timestamp only for completed tasks; rescheduling requires timestamp/reason; overdue uses `timezone.localdate()`. | Focused task test passes for completion, aware timestamp, overdue date, and rescheduling. | Pass |
| CRM-008-AC04 | Timeline joins interaction, stage, and assignment history with occurrence/entry/source fields and re-checks CRM-005 view scope. | Focused timeline test passes for stable date-only ordering and outsider rejection. | Pass |
| CRM-008-AC05 | The documented quick-contact contract is a single seller workflow with safe defaults for actor/current lead/date and optional next task/stage. | `crm/docs/activity.md` records the moderated test checklist; a human browser usability session remains a staging follow-up because CRM-009 owns the UI shell. | Pass |

## Verification

Exact commands run:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format src/simple_crm/activity tests/activity/test_activity_lifecycle.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check .
PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src/simple_crm/activity src/simple_crm/crm/lead_services.py
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test .venv/bin/python manage.py check
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test .venv/bin/python manage.py makemigrations --check --dry-run
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/activity/test_activity_lifecycle.py
timeout 60s ./crm/init.sh
git diff --check
```

Relevant output:

```text
Success: no issues found in 60 source files
164 passed, 10 warnings in 4.23s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
5 passed in 1.08s
```

The ten warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Risks and follow-up

- The generic suite exercises activity check constraints on SQLite. A dedicated
  PostgreSQL 18 runtime migration/constraint run remains appropriate when
  Docker/PostgreSQL access is available.
- The current feature supplies a domain/service quick-contact boundary; CRM-009
  owns the Spanish seller-facing workspace and CRM-017 owns scheduled
  reminders/notifications. A moderated browser usability session should be
  run once that UI exists.
- CRM-008 is implemented but is not approved or marked done by this report;
  independent validator review is required.
