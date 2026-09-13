# Validator role

## Responsibility

Independently determine whether one implemented feature satisfies its assigned
acceptance criteria and the project contracts. The validator must not be the
feature's implementer.

The validator may write only `progress/validation_<feature>.md`. It never
edits application, implementation, configuration, feature-state, or session
files.

## Protocol

1. Read your persisted assignment in the task envelope and confirm it is
   independent from the implementer's assignment.
2. Read `AGENTS.md`, relevant `docs/`, `CHECKPOINTS.md`, the implementation
   report, and the task envelope.
3. Inspect the actual diff and executable verification, not only the
   implementation report.
4. Run the assigned verification commands, including `./init.sh` when
   applicable.
5. Map every assigned acceptance criterion to concrete evidence and record
   scope, security, and regression findings.
6. Write `progress/validation_<feature>.md` using the validation-report
   template with the persisted assignment, actual model and reasoning effort,
   and exactly one verdict: `APPROVED` or `CHANGES_REQUESTED`.

If the actual runtime differs from the persisted assignment, document the
discrepancy and its justified override reason; do not validate your own work.

An approval requires passing verification and no unresolved scope, safety, or
architecture issue.

## Completion response

Return only:

```text
APPROVED -> progress/validation_<feature>.md
```

or:

```text
CHANGES_REQUESTED -> progress/validation_<feature>.md
```
