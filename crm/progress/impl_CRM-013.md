# Implementation report — CRM-013

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the intentionally
  dirty completed-feature worktree recorded in `progress/current.md`.
- Requirement IDs: CRM-013-R01 through CRM-013-R05
- Acceptance-criterion IDs: CRM-013-AC01 through CRM-013-AC05
- Allowed scope: typed reporting filters, saved-view model/lifecycle,
  migration, Spanish segments page, focused tests, documentation, and this
  report.
- Dependencies and assumptions: CRM-009 and CRM-012 are done. `visible_leads`
  remains the authorization boundary for all counts and result querysets.
- Persisted assignment: `crm013_segments_implementer_terra`, `gpt-5.6-terra`,
  high reasoning.
- Runtime note: this environment does not expose switchable model identities or
  a separate Terra process. The work followed the persisted assignment and the
  discrepancy is recorded rather than silently substituting an inherited
  assignment.

## Changed files and decisions

- `src/simple_crm/reporting/services.py`: added allow-listed typed conditions
  for stage, owner, campaign, readiness, source, age, staleness, geography,
  specialty, contactability, activity, response, and task state; bounded
  AND/OR definitions; Spanish summaries; stable sorting/cursors; and scoped
  saved-view lifecycle operations.
- `src/simple_crm/reporting/models.py` and
  `src/simple_crm/reporting/migrations/0001_saved_views.py`: added versioned
  structured private/shared views with manager approval and archive state.
- `src/simple_crm/platform/views.py`, `src/simple_crm/platform/urls.py`, and
  `src/simple_crm/platform/templates/platform/segments.html`: added the
  Spanish guided segment page with filter/reset controls and saved-view links.
- `tests/reporting/test_segments.py`, `tests/platform/test_segments_page.py`:
  added filter, scope, lifecycle, pagination, endpoint, and content-safety
  coverage.
- `crm/docs/segments.md` plus architecture/convention/verification docs:
  documented the structured definition and authorization boundaries.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-013-AC01 | Field/operator allow-list, scalar/list type validation, bounded values, and internal ORM mapping. | Service tests validate supported stage execution and reject ORM paths/raw operators. | Pass |
| CRM-013-AC02 | SavedView version, rename, copy, archive, structured definition, and execution services. | Lifecycle test creates, reopens, renames, copies, archives, and rejects archived execution. | Pass |
| CRM-013-AC03 | Private owner checks and manager-only shared approval; shared execution re-applies the caller's scope. | Private-view permission test and shared-view execution test pass. | Pass |
| CRM-013-AC04 | Explicit sort allow-list with `pk` tie-breaker and bounded offset cursor. | Equal-sort pagination test returns distinct consecutive leads. | Pass |
| CRM-013-AC05 | Spanish labels, summaries, reset link, and no raw field paths in the template. | Rendered page test asserts business copy and rejects ORM vocabulary. | Pass |

## Verification

Exact commands run:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format src/simple_crm/reporting/models.py src/simple_crm/reporting/services.py src/simple_crm/platform/views.py tests/reporting/test_segments.py tests/platform/test_segments_page.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check src/simple_crm/reporting src/simple_crm/platform tests/reporting/test_segments.py tests/platform/test_segments_page.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src/simple_crm/reporting src/simple_crm/platform
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py makemigrations --check --dry-run
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/reporting/test_segments.py tests/platform/test_segments_page.py
timeout 60s ./crm/init.sh
```

Relevant output:

```text
All checks passed!
Success: no issues found in 14 source files
No changes detected
5 passed, 2 warnings in 1.58s
186 passed, 17 warnings in 4.89s
[harness] ready
```

The warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Risks and follow-up

- Shared views do not grant visibility; execution always rebuilds the query
  from the caller's current scope.
- PostgreSQL-volume query-plan evidence remains a staging follow-up; the local
  harness validates typed behavior and authorization on SQLite.
- CRM-013 is implemented but not yet approved or marked done; independent
  validator review is required.
