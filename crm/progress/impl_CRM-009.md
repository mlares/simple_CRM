# Implementation report — CRM-009

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the intentionally dirty completed-feature worktree recorded in `progress/current.md`.
- Requirement IDs: CRM-009-R01 through CRM-009-R05
- Acceptance-criterion IDs: CRM-009-AC01 through CRM-009-AC04
- Allowed scope: platform workspace queries, views, URLs, templates, documentation, focused tests, and this report.
- Out-of-scope files: feature/session/history state, validator report, identity/activity/data-quality/reporting apps, imports, search, reports, notifications, programmable dashboards, gamification, and clinical identities.
- Dependencies and assumptions: CRM-007 and CRM-008 are done. Presentation reads use their existing scope-aware service/query boundaries; this feature does not write domain records.
- Persisted assignment: `crm009_workspace_implementer_terra`, `gpt-5.6-terra`, high reasoning.
- Runtime note: this environment does not expose switchable model identities or a separate Terra process. The work followed the persisted Terra assignment and the discrepancy is recorded rather than silently substituting an inherited assignment.

## Changed files and decisions

- `src/simple_crm/platform/workspace.py`: added scope-aware Today classification, fixed urgency ordering, manager-only unassigned visibility, and lead-detail composition.
- `src/simple_crm/platform/views.py`: added authenticated Today and lead-detail views while preserving dependency-safe health probes and the public landing page.
- `src/simple_crm/platform/urls.py`: added `/today/` and human-readable `/leads/<lead-number>/` routes.
- `src/simple_crm/platform/templates/platform/home.html`, `today.html`, `lead_detail.html`: added Spanish-first navigation, cards, empty state, lead detail, timeline, tasks, and no-database-vocabulary presentation.
- `tests/platform/test_workspace.py`: added four focused tests for urgency classification, scoped manager/seller visibility, rendered Spanish content, and anonymous redirect behavior.
- `crm/docs/workspace.md`, `crm/docs/architecture.md`, `crm/docs/conventions.md`, `crm/docs/verification.md`, `README.md`: documented presentation ownership, urgency rules, scope boundary, and manual UX follow-up.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-009-AC01 | Today and detail views require authentication; workspace queries start from `visible_leads()` and the detail route fails closed for inaccessible lead numbers. | Focused seller-scope and anonymous-redirect tests pass. | Pass |
| CRM-009-AC02 | `today_workspace()` classifies overdue, due-today, recent responses, stale in-progress leads, and manager-visible unassigned leads with fixed rank and local-date handling. | Focused fixed-fixture classification test passes. | Pass |
| CRM-009-AC03 | Each card links to human-readable lead detail; empty state and actionable labels are rendered in Spanish; detail includes timeline and tasks. | Focused rendered-page test and full template suite pass. | Pass |
| CRM-009-AC04 | Navigation and detail templates use Spanish labels, disabled future destinations, human-readable lead numbers, and no raw primary-key route or SQL vocabulary. | Focused rendered content test plus djLint/template checks pass. | Pass |

## Verification

Exact commands run:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format src/simple_crm/platform/views.py src/simple_crm/platform/workspace.py tests/platform/test_workspace.py
.venv/bin/djlint --reformat src/simple_crm/platform/templates/platform/today.html src/simple_crm/platform/templates/platform/lead_detail.html
timeout 60s ./crm/init.sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/platform/test_workspace.py
git diff --check
```

Relevant output:

```text
Success: no issues found in 61 source files
168 passed, 13 warnings in 4.41s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
4 passed, 3 warnings in 1.23s
```

The thirteen warnings are the existing non-fatal WhiteNoise warning for the
absent default `staticfiles/` directory during test-client setup, now including
the three workspace client tests.

## Risks and follow-up

- Manual moderated UX review remains appropriate once CRM-012 search and the
  rest of the navigation surface are available; the repository records the
  workflow and test boundary without claiming a human session occurred.
- The workspace uses a fixed fourteen-day stale threshold and seven-day
  response window as documented product defaults; later reporting may expose
  governed configuration if the feature list adds it.
- CRM-009 is implemented but is not approved or marked done by this report;
  independent validator review is required.
