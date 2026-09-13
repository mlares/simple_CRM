# Orchestrator role

## Responsibility

Coordinate one feature from readiness through independent validation and
closure. Do not edit implementation files while acting as orchestrator.

The orchestrator exclusively owns feature selection and status transitions in
`feature_list.json`, along with `progress/current.md` and
`progress/history.md`.

## Protocol

1. Read the persisted assignment for each role from the task envelope and the
   supported policy in `harness.json`; launch every role with that persisted
   assignment, including its model and reasoning effort.
2. Confirm that the feature is ready: requirements and acceptance IDs are
   clear, dependencies are complete, scope is bounded, and verification is
   defined.
3. Record the feature as `in_progress` and the baseline revision or current
   worktree baseline in `progress/current.md`.
4. Delegate an optional explorer only for a bounded, read-only question.
5. Delegate one implementer using the complete task envelope in `AGENTS.md`.
6. After the implementation report exists, set the compatibility state to
   `review` and delegate an independent validator.
7. For `CHANGES_REQUESTED`, record `changes_requested`, then delegate the
   bounded revision to the implementer and repeat validation.
8. For `APPROVED`, record the implementation and validation report paths,
   change the feature to `done`, append history, and run `./init.sh`.

Record the actual model and reasoning effort used for orchestration and each
delegated role in the relevant task record or report. An override requires the
persisted nonblank reason; do not silently substitute an inherited default.

## Handoff rule

Require persisted reports. Do not accept an unreferenced chat summary as
completion evidence.
