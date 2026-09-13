# Implementation report — CRM-014

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` plus the intentionally
  dirty completed-feature worktree recorded in `progress/current.md`.
- Requirement IDs: CRM-014-R01 through CRM-014-R06
- Acceptance-criterion IDs: CRM-014-AC01 through CRM-014-AC05
- Allowed scope: governed metric catalog, read-only dashboard services and
  page, migration, focused tests, documentation, and this report.
- Dependencies and assumptions: CRM-007, CRM-008, and CRM-013 are done.
  `visible_leads` is the authorization boundary for every report queryset.
- Persisted assignment: `crm014_metrics_implementer_terra`, `gpt-5.6-terra`,
  high reasoning.
- Runtime note: this environment does not expose switchable model identities or
  a separate Terra process. The work followed the persisted assignment and the
  discrepancy is recorded rather than silently substituting an inherited
  assignment.

## Changed files and decisions

- `src/simple_crm/reporting/models.py` and
  `src/simple_crm/reporting/migrations/0002_metric_catalog.py`: added seeded,
  versioned metric definitions with owner, semantics, inclusion rules, and
  effective date.
- `src/simple_crm/reporting/metrics.py`: added read-only scope-first KPI and
  dimension projections for contactability, contacted leads, response rate,
  stale leads, stage age, overdue tasks, cohort conversion, attention,
  pipeline, activity, source, and follow-up gaps.
- `src/simple_crm/platform/views.py`, `src/simple_crm/platform/urls.py`, and
  `src/simple_crm/platform/templates/platform/reports.html`: added the Spanish
  report page with date range, metadata, KPI definitions/versions, and
  dashboard sections.
- `tests/reporting/test_metrics.py`, `tests/platform/test_reports_page.py`:
  added fixture-backed metric, occurrence-date, attempted-contact, scope, and
  rendered metadata tests.
- `crm/docs/reports.md` plus architecture/convention/verification docs:
  documented ownership and timeframe semantics.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| CRM-014-AC01 | Metric catalog and dashboard projections for all governed KPI and report dimensions. | Fixture-backed metrics test verifies contactability, contacted leads, response, and section set. | Pass |
| CRM-014-AC02 | Eligible interaction query excludes placeholder notes and attempted outbound rows from response denominator. | Metric regression test proves completed/response behavior and attempted exclusion. | Pass |
| CRM-014-AC03 | Dashboard starts from `visible_leads(actor)` and derives all related rows from authorized lead IDs. | Cross-campaign metric test confirms hidden rows do not affect result count or stale KPI. | Pass |
| CRM-014-AC04 | `MetricDefinition` metadata is returned with every `MetricResult`; dashboard carries period, scope, freshness, result count, and as-of time. | Rendered page test asserts business metadata and versioned KPI definition. | Pass |
| CRM-014-AC05 | Read-only service uses bounded date range and simple ORM aggregations. | Full harness and focused report test pass; PostgreSQL-volume timing remains staged follow-up. | Pass |

## Verification

Exact commands run:

```text
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format src/simple_crm/reporting/models.py src/simple_crm/reporting/metrics.py src/simple_crm/reporting/migrations/0002_metric_catalog.py src/simple_crm/platform/views.py src/simple_crm/platform/urls.py tests/reporting/test_metrics.py tests/platform/test_reports_page.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check src/simple_crm/reporting src/simple_crm/platform tests/reporting/test_metrics.py tests/platform/test_reports_page.py
PYTHONDONTWRITEBYTECODE=1 .venv/bin/mypy src/simple_crm/reporting src/simple_crm/platform
DJANGO_SETTINGS_MODULE=simple_crm.config.settings.test PYTHONDONTWRITEBYTECODE=1 .venv/bin/python manage.py makemigrations --check --dry-run
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/reporting/test_metrics.py tests/platform/test_reports_page.py
timeout 60s ./crm/init.sh
```

Relevant output:

```text
All checks passed!
Success: no issues found in 16 source files
No changes detected
4 passed, 2 warnings in 1.67s
190 passed, 19 warnings in 4.95s
[harness] ready
```

The warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Risks and follow-up

- PostgreSQL-volume query plans and the agreed two-second p95 target remain a
  staging performance follow-up; local verification uses SQLite.
- The dashboard is read-only and intentionally does not include exports,
  warehouse synchronization, or user-authored SQL metrics.
- CRM-014 is implemented but not yet approved or marked done; independent
  validator review is required.
