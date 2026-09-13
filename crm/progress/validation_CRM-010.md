# Validation report — CRM-010

## Verdict

`APPROVED`

## Independence and scope

- Validator: `crm010_import_validator_sol`
- Persisted validator assignment: `gpt-5.6-sol`, high reasoning; implementer assignment was the distinct `crm010_import_implementer_terra` / `gpt-5.6-terra`.
- Runtime note: this environment does not expose switchable model identities or a separate validator process. The independent validator pass was executed as a separate review phase with no implementation-file edits; the discrepancy is recorded rather than silently substituted.
- Implementer: `crm010_import_implementer_terra`
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188` plus the dirty worktree baseline recorded in the task envelope.
- Allowed validator write target: `progress/validation_CRM-010.md`

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-010-AC01 | Preview transaction, source-only models/services, canonical count assertions, and staged-state test. | Pass | Upload/preview creates source evidence only; canonical parties and leads remain unchanged before approval. |
| CRM-010-AC02 | Batch uniqueness constraint and checksum/parser/application-version reuse path. | Pass | Reprocessing returns the original batch and does not duplicate rows, documents, or upload audit events. |
| CRM-010-AC03 | SourceRecord coordinate/raw/checksum/classification/error/link fields and exact lineage assertions. | Pass | Sheet, row, source coordinate, raw value, and formula-error evidence are retained. |
| CRM-010-AC04 | Extension/size/empty/parser/header guards and row-level Excel error classification. | Pass | Invalid inputs fail with Spanish validation errors; formula errors remain visible as row evidence. |
| CRM-010-AC05 | Steward role/global scope gate, approval/application state services, separate reasons, and immutable audit model/test. | Pass | Sales managers cannot approve/apply; uploaded, approved, and applied events are distinct and ordered. |

## Verification

Exact commands run:

```text
python -m json.tool crm/feature_list.json >/dev/null
python -m json.tool crm/progress/tasks/CRM-010.json >/dev/null
timeout 60s ./crm/init.sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/data_quality/test_import_staging.py
git diff --check
```

Relevant output:

```text
Success: no issues found in 66 source files
173 passed, 13 warnings in 4.25s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
5 passed in 1.29s
```

The thirteen warnings are the existing non-fatal WhiteNoise warning for the
absent default `staticfiles/` directory during test-client setup.

## Findings

- Scope: implementation is limited to source documents, staged batches/rows,
  preview/idempotency, lineage, audit, admin read surface, docs, and tests.
  Matching/merge and cutover application are not silently folded into this
  feature.
- Security: steward role plus global import scope is checked for all import
  operations; approval/application reasons and actors are retained, and raw
  workbook bytes are not exposed through user-facing responses.
- Architecture: canonical business records are not written during upload or
  preview. Approved application commits staged state atomically; ambiguous
  canonical correction is explicitly deferred to the governed downstream
  workflow.
- Regression: full harness, mypy, migration drift, system checks, repository
  safety, vendored assets, and focused import tests pass.
- Environment limitation: PostgreSQL-specific runtime evidence for new import
  uniqueness constraints was not available in this sandbox; generic constraint
  tests pass and dedicated PostgreSQL 18 acceptance remains a staging follow-up.
- No unresolved changes requested.
