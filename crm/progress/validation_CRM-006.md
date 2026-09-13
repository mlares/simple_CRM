# Validation report — CRM-006

## Verdict

`APPROVED`

## Independence and scope

- Validator: `crm006_party_validator_sol`
- Persisted validator assignment: `gpt-5.6-sol`, high reasoning; implementer assignment was the distinct `crm006_party_implementer_terra` / `gpt-5.6-terra`.
- Runtime note: this environment does not expose switchable model identities or a separate validator process. The independent validator pass was executed as a separate review phase with no implementation-file edits; the discrepancy is recorded rather than silently substituted.
- Implementer: `crm006_party_implementer_terra`
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188` plus the dirty worktree baseline recorded in the task envelope.
- Allowed validator write target: `progress/validation_CRM-006.md`

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-006-AC01 | Party subtype XOR migration constraint, foreign keys, relationship constraints, model validation, and focused constraint/relationship tests. | Pass | Both/neither subtype creation fails; invalid relationship type and dates are rejected. |
| CRM-006-AC02 | Normalization module, raw/provenance fields, quality-state choices, and focused email/phone test. | Pass | Valid values normalize deterministically; invalid values retain raw evidence and explicit state. |
| CRM-006-AC03 | Monotonic suppression save guard, outreach queryset, durable link/provenance models, and suppression test. | Pass | Suppressed values remain excluded after normal edits and remain retained for history. Future import/merge code must use the service boundary. |
| CRM-006-AC04 | Party versioned save/archive implementation and stale-instance test. | Pass | A stale edit raises a readable `PartyConcurrencyError` and cannot overwrite the newer version. |
| CRM-006-AC05 | Transactional creation services, exact contact/name warning preview, active manager, and no-merge test. | Pass | Duplicate candidates warn before creation; creation does not merge or delete records. |

## Verification

Exact commands run:

```text
./crm/init.sh
git diff --check
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/crm/test_party_models.py
```

Relevant output:

```text
[OK] harness metadata is valid
All checks passed!
Success: no issues found in 53 source files
153 passed, 10 warnings in 3.22s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
8 passed in 0.71s
```

The ten warnings are the known non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Findings

- Scope: implementation is limited to CRM-006 party master data; no leads,
  interactions, imports, merges, or clinical identities were introduced.
- Security and privacy: raw source evidence is retained separately from
  normalized values; shared institutional contacts are not treated as personal
  identifiers; archival is non-destructive; automatic fuzzy merging is absent.
- Architecture: party ownership remains in `simple_crm.crm`, and future import
  or merge features have documented service boundaries for suppression and
  optimistic concurrency.
- Regression: full harness, migration-drift, safety, and focused tests pass.
- Environment limitation: a disposable PostgreSQL 18 container could not be
  queried because Docker socket access became permission-blocked in the sandbox;
  it was stopped with elevated permission. No shared or application database
  was touched. PostgreSQL runtime evidence remains a staging follow-up.
- No unresolved changes requested.
