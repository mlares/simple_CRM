# Validation report — CRM-015

## Verdict

`APPROVED`

## Independence and scope

- Validator: `crm015_exports_validator_sol`
- Persisted validator assignment: `gpt-5.6-sol`, high reasoning; implementer
  assignment was the distinct `crm015_exports_implementer_terra` /
  `gpt-5.6-terra`.
- Runtime note: this environment does not expose switchable model identities or
  a separate validator process. The independent validator pass was executed as
  a separate review phase with no implementation-file edits; the discrepancy
  is recorded rather than silently substituted.
- Implementer: `crm015_exports_implementer_terra`
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188` plus the dirty
  worktree baseline recorded in the task envelope.
- Allowed validator write target: `progress/validation_CRM-015.md`

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-015-AC01 | Separate `BULK_EXPORT` checks at request/materialize/download boundaries and denial audit. | Pass | View-capable users without export permission cannot create or retrieve an artifact. |
| CRM-015-AC02 | Definition/field/scope snapshots, idempotency key, and materialization through current scoped definitions. | Pass | Repeated keys reuse one request and later definition mutation does not alter the captured snapshot. |
| CRM-015-AC03 | Safe explicit field layout, CSV/XLSX serialization, and formula-control neutralization. | Pass | Formula vectors are prefixed safely; contact/note fields are not part of the export layout. |
| CRM-015-AC04 | State/expiry/checksum fields, bounded rows, and download expiry transition. | Pass | Expired files are denied while request and audit metadata remain retained. |
| CRM-015-AC05 | Append-only audit events and metadata-only payload handling. | Pass | Request, denial, materialization, failure, and download actions are auditable without file contents. |

## Verification

Exact commands run:

```text
python -m json.tool crm/feature_list.json >/dev/null
python -m json.tool crm/progress/tasks/CRM-015.json >/dev/null
timeout 60s ./crm/init.sh
PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/reporting/test_exports.py
git diff --check
```

Relevant output:

```text
Success: no issues found in 76 source files
193 passed, 19 warnings in 5.19s
System check identified no issues (0 silenced).
No changes detected
repository safety scan passed
vendored assets verified
[harness] ready
3 passed in 1.67s
```

The warnings are the existing non-fatal WhiteNoise warning for the absent
default `staticfiles/` directory during test-client setup.

## Findings

- Scope: implementation is limited to permissioned bounded CSV/XLSX exports,
  snapshots, checksums, expiry, audit, tests, and documentation. Public links,
  unlimited synchronous exports, and worker infrastructure remain separate.
- Security: export permission is independent from view permission; materialize
  re-evaluates the requesting identity's visible leads and safe fields.
- Architecture: idempotency and definition snapshots prevent mutable saved-view
  state from changing a queued artifact; formula controls are neutralized before
  serialization.
- Regression: full harness, formatting/linting, type checks, template checks,
  migration drift, system checks, repository safety, vendored assets, and
  focused export tests pass.
- Environment limitation: PostgreSQL-volume performance/storage evidence and
  durable worker crash recovery remain staging/CRM-017 follow-ups.
- No unresolved changes requested.
