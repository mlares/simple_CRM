# Validation report — CRM-013

## Verdict

`APPROVED`

## Independence and scope

- Validator: `crm013_segments_validator_sol`
- Persisted validator assignment: `gpt-5.6-sol`, high reasoning; implementer
  assignment was the distinct `crm013_segments_implementer_terra` /
  `gpt-5.6-terra`.
- Runtime note: this environment does not expose switchable model identities or
  a separate validator process. The independent validator pass was executed as
  a separate review phase with no implementation-file edits; the discrepancy
  is recorded rather than silently substituted.
- Implementer: `crm013_segments_implementer_terra`
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188` plus the dirty
  worktree baseline recorded in the task envelope.
- Allowed validator write target: `progress/validation_CRM-013.md`

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-013-AC01 | Typed field/operator allow-list, value validation, bounded definitions, and internal Q mapping. | Pass | Supported filters map to deterministic ORM predicates; raw ORM paths and operators are rejected. |
| CRM-013-AC02 | SavedView model/version fields and create, execute, rename, copy, archive services. | Pass | Lifecycle test covers create, reopen/execute, rename, copy, archive, and archived-access rejection. |
| CRM-013-AC03 | Private owner gate, manager-only shared creation, and caller-scope reapplication on shared execution. | Pass | Private views are inaccessible to other users; shared definitions do not broaden the executor's scope. |
| CRM-013-AC04 | Explicit stable sort options, `pk` tie-breakers, and bounded cursor slicing. | Pass | Equal-sort pagination returns distinct consecutive rows without omission or duplication. |
| CRM-013-AC05 | Spanish segments template, human-readable summary/reset controls, and content-safety assertions. | Pass | Rendered output contains business labels and no raw field paths, table names, or SQL vocabulary. |

## Verification

Exact commands run:

```text
python -m json.tool crm/feature_list.json >/dev/null
python -m json.tool crm/progress/tasks/CRM-013.json >/dev/null
timeout 60s ./crm/init.sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/reporting/test_segments.py tests/platform/test_segments_page.py
git diff --check
```

Relevant output:

```text
Success: no issues found in 72 source files
186 passed, 17 warnings in 4.88s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
5 passed, 2 warnings in 1.66s
```

The warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Findings

- Scope: implementation is limited to typed guided filters, scoped execution,
  saved-view persistence/lifecycle, Spanish rendering, tests, and docs.
  Governed metrics and exports remain separate features.
- Security: private-view access is owner-bound; shared-view creation requires a
  manager/admin role, and execution always starts from the caller's current
  `visible_leads` queryset.
- Architecture: definitions are structured JSON validated before ORM mapping;
  no stored SQL or arbitrary expressions are accepted. Stable sort keys include
  a primary-key tie-breaker.
- Regression: full harness, formatting/linting, type checks, template checks,
  migration drift, system checks, repository safety, vendored assets, and
  focused segment tests pass.
- Environment limitation: PostgreSQL-volume query-plan evidence remains a
  staging follow-up; local verification uses SQLite for generic behavior.
- No unresolved changes requested.
