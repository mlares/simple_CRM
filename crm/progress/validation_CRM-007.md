# Validation report — CRM-007

## Verdict

`APPROVED`

## Independence and scope

- Validator: `crm007_lead_validator_sol`
- Persisted validator assignment: `gpt-5.6-sol`, high reasoning; implementer assignment was the distinct `crm007_lead_implementer_terra` / `gpt-5.6-terra`.
- Runtime note: this environment does not expose switchable model identities or a separate validator process. The independent validator pass was executed as a separate review phase with no implementation-file edits; the discrepancy is recorded rather than silently substituted.
- Implementer: `crm007_lead_implementer_terra`
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188` plus the dirty worktree baseline recorded in the task envelope.
- Allowed validator write target: `progress/validation_CRM-007.md`

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-007-AC01 | Lead current-stage field, initial/transition service transactions, immutable history save guard, and focused stage/history assertions. | Pass | Current stage and latest accepted history agree for creation and transitions. |
| CRM-007-AC02 | Transition matrix, reason/closure/next-action validation, transaction decorators, and rollback assertions. | Pass | Invalid or incomplete transitions leave both lead state and history unchanged. |
| CRM-007-AC03 | `LeadAssignment` partial unique constraint, assignment date constraint, reassignment service, and uniqueness/history test. | Pass | Generic SQLite evidence passes. A dedicated PostgreSQL 18 runtime constraint run remains appropriate when Docker/PostgreSQL access is available. |
| CRM-007-AC04 | CRM-005 policy calls in mutation/list services and out-of-scope identity test. | Pass | An outsider cannot transition, reassign, or discover the lead through the scoped list. |
| CRM-007-AC05 | Atomic creation service, candidate warning preview, source/next-action/party/owner/history writes, and creation tests. | Pass | Existing candidates warn without merge; the new lead is created atomically. |

## Verification

Exact commands run:

```text
python -m json.tool crm/feature_list.json >/dev/null
python -m json.tool crm/progress/tasks/CRM-007.json >/dev/null
timeout 60s ./crm/init.sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/crm/test_lead_lifecycle.py
git diff --check
```

Relevant output:

```text
Success: no issues found in 55 source files
159 passed, 10 warnings in 3.34s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
6 passed in 0.91s
```

The ten warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Findings

- Scope: the implementation is limited to lead lifecycle, explicit party
  links, assignment history, stage history, minimal next-action commitment,
  documentation, admin read surface, and tests. CRM-008 interactions/tasks,
  imports, merges, reporting, revenue, quotes, contracts, and clinical data
  were not introduced.
- Security: all lead mutation services and list visibility re-check enabled
  identity plus action scope; URL/body identifiers do not bypass policy.
- Architecture: `simple_crm.crm` owns the aggregate and uses CRM-005 identity
  policy rather than duplicating authorization logic. Cross-feature next-task
  expansion is explicitly deferred to CRM-008.
- Regression: full harness, migration drift, system checks, repository safety,
  vendored asset checks, and focused lifecycle tests pass.
- Environment limitation: PostgreSQL-specific runtime evidence for the partial
  assignment index was not available in this sandbox; the generic constraint
  tests pass and the dedicated PostgreSQL 18 acceptance run remains a staging
  follow-up. No shared or application database was touched.
- No unresolved changes requested.
