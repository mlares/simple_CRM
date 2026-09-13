# Validation report — CRM-014

## Verdict

`APPROVED`

## Independence and scope

- Validator: `crm014_metrics_validator_sol`
- Persisted validator assignment: `gpt-5.6-sol`, high reasoning; implementer
  assignment was the distinct `crm014_metrics_implementer_terra` /
  `gpt-5.6-terra`.
- Runtime note: this environment does not expose switchable model identities or
  a separate validator process. The independent validator pass was executed as
  a separate review phase with no implementation-file edits; the discrepancy
  is recorded rather than silently substituted.
- Implementer: `crm014_metrics_implementer_terra`
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188` plus the dirty
  worktree baseline recorded in the task envelope.
- Allowed validator write target: `progress/validation_CRM-014.md`

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-014-AC01 | Seeded MetricDefinition catalog, KPI projections, pipeline/activity/source/attention sections, and fixture test. | Pass | Governed definitions and report dimensions are present and produce deterministic values. |
| CRM-014-AC02 | Eligible-interaction query, placeholder exclusion, attempted-outbound exclusion, and response regression test. | Pass | Response denominator counts eligible outbound interactions, not leads, and attempts are excluded. |
| CRM-014-AC03 | `visible_leads()` base query, authorized lead IDs, related task/interaction/contact queries, and cross-scope test. | Pass | Hidden campaign rows do not affect counts, KPIs, or report categories. |
| CRM-014-AC04 | Metric definition metadata and Dashboard period/scope/freshness/as-of fields, plus rendered page. | Pass | Every KPI displays its governed definition version beside page-level timeframe and scope metadata. |
| CRM-014-AC05 | Bounded date-window service, read-only ORM projections, full harness output. | Pass | Generic performance/safety gates are green; PostgreSQL-volume p95/query-plan evidence remains staging follow-up. |

## Verification

Exact commands run:

```text
python -m json.tool crm/feature_list.json >/dev/null
python -m json.tool crm/progress/tasks/CRM-014.json >/dev/null
timeout 60s ./crm/init.sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/reporting/test_metrics.py tests/platform/test_reports_page.py
git diff --check
```

Relevant output:

```text
Success: no issues found in 74 source files
190 passed, 19 warnings in 5.04s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
4 passed, 2 warnings in 1.71s
```

The warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Findings

- Scope: implementation is limited to versioned metric definitions, read-only
  dashboard projections, scope-preserving report rendering, tests, and docs.
  Exports and warehouses remain separate features.
- Security: all report data starts from the caller's authorized lead queryset;
  templates receive projections and metadata rather than query semantics.
- Architecture: metric ownership, inclusion rules, timeframe semantics, version,
  and effective date are durable catalog data. Interaction occurrence dates and
  Córdoba local task dates are explicit.
- Regression: full harness, formatting/linting, type checks, template checks,
  migration drift, system checks, repository safety, vendored assets, and
  focused metric tests pass.
- Environment limitation: PostgreSQL-volume query plans and the agreed two-
  second p95 target require staging evidence; local verification uses SQLite.
- No unresolved changes requested.
