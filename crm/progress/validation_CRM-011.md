# Validation report — CRM-011

## Verdict

`APPROVED`

## Independence and scope

- Validator: `crm011_quality_validator_sol`
- Persisted validator assignment: `gpt-5.6-sol`, high reasoning; implementer assignment was the distinct `crm011_quality_implementer_terra` / `gpt-5.6-terra`.
- Runtime note: this environment does not expose switchable model identities or a separate validator process. The independent validator pass was executed as a separate review phase with no implementation-file edits; the discrepancy is recorded rather than silently substituted.
- Implementer: `crm011_quality_implementer_terra`
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188` plus the dirty worktree baseline recorded in the task envelope.
- Allowed validator write target: `progress/validation_CRM-011.md`

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-011-AC01 | Quality issue severity/state/owner/reason fields, deterministic queue ordering, transition service, and focused queue test. | Pass | Issues sort by severity then age; resolve, accept-with-reason, and reopen transitions are audited. |
| CRM-011-AC02 | Exact/fuzzy candidate services, review-only state, approval gate, and negative mutation test. | Pass | Fuzzy matching records confidence/evidence but does not mutate canonical relationships before steward approval. |
| CRM-011-AC03 | `MergePreview` implementation and fixture-backed preview test. | Pass | Preview enumerates leads, interactions, tasks, contact points, aliases, and source links. |
| CRM-011-AC04 | Atomic approved-merge service and preservation assertions. | Pass | Related links redirect, aliases and source lineage remain traceable, and suppressed contact points remain suppressed. |
| CRM-011-AC05 | Immutable quality audit model, issue/candidate/merge audit writes, and focused audit assertions. | Pass | Actor, reason, before state, after state, and source evidence are retained for governed decisions. |

## Verification

Exact commands run:

```text
python -m json.tool crm/feature_list.json >/dev/null
python -m json.tool crm/progress/tasks/CRM-011.json >/dev/null
timeout 60s ./crm/init.sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/data_quality/test_quality_merge.py
git diff --check
```

Relevant output:

```text
Success: no issues found in 67 source files
176 passed, 13 warnings in 4.46s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
3 passed in 1.56s
```

The thirteen warnings are the existing non-fatal WhiteNoise warning for the
absent default `staticfiles/` directory during test-client setup.

## Findings

- Scope: implementation is limited to quality issues, candidate matching,
  review decisions, merge preview/application, lineage and suppression
  preservation, audit, admin, docs, and tests. Automatic fuzzy merging and
  destructive source deletion remain out of scope.
- Security: quality operations require an enabled data-steward or system
  administrator role with active global resolve-quality scope.
- Architecture: fuzzy matching never mutates canonical relationships; approved
  merges are transactionally bounded and reject conflicting relationships for
  explicit steward resolution.
- Regression: full harness, formatting/linting, type checks, migration drift,
  system checks, repository safety, vendored assets, and focused quality tests
  pass.
- Environment limitation: PostgreSQL-specific runtime evidence for quality
  constraints was not available in this sandbox; dedicated PostgreSQL staging
  coverage remains a follow-up.
- No unresolved changes requested.
