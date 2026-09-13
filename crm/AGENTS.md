# Agent Operating Contract

This is the canonical, provider-neutral entry point for agents working in
`CRM`.

The application domain is intentionally unspecified. The harness defines how
work is selected, delegated, verified, and recorded. Provider adapters such as
`CLAUDE.md` must point back to this file instead of duplicating the contract.

## Start here

1. Read `progress/current.md`.
2. Read `feature_list.json` and choose exactly one `pending` feature.
3. Read the relevant files in `docs/` before changing the project.
4. Run `./init.sh` before starting implementation.
5. Follow the role specification in `agents/roles/` for your current role.

## Non-negotiable rules

- Work on one feature at a time.
- The orchestrator alone owns feature-state transitions in `feature_list.json`
  and session state in `progress/current.md` and `progress/history.md`.
- The implementer alone owns implementation changes within its delegated scope
  and `progress/impl_<feature>.md`.
- The validator is independent of the implementer and writes only
  `progress/validation_<feature>.md`; it never edits implementation files.
- Implementers write tests or other executable verification with their change.
- Validators do not edit implementation files.
- Do not mark a feature `done` without a passing verification run and an
  approved validation report.
- Subagents return a short pointer to their report; the report itself lives on
  disk under `progress/`.

## Persisted runtime assignment policy

`harness.json` is the persisted source of supported models, reasoning efforts,
and role defaults. Before delegation, the orchestrator must resolve the active
role assignments in the task envelope's `agent_assignments` object. Active
tasks require assignments for orchestrator, implementer, and validator; an
explorer is recorded when one is used.

Each assignment records an `agent_id`, `model`, `reasoning_effort`, and
`source`. A `role_default` assignment must exactly match the corresponding
default in `harness.json`. Any `override` must use a supported combination and
include a nonblank `override_reason`. The implementer and validator assignment
agent IDs must differ.

Launch each delegated role with its persisted assignment, rather than an
inherited session default. Every role report and handoff must record the actual
model and reasoning effort used; if the runtime cannot honor an assignment,
record the discrepancy and its reason before continuing or blocking work.

## Canonical workflow and state transitions

The canonical sequence is:

```text
orchestrator -> explorer (optional) -> implementer -> validator -> orchestrator closure
                                                   ^              |
                                                   |-- changes ---|
```

Only the orchestrator changes feature state:

```text
pending -> in_progress -> review -> done
                       -> changes_requested -> in_progress
```

`review` remains the compatibility state name while the validator role is
canonical. A validator's `CHANGES_REQUESTED` verdict returns the feature to
the orchestrator, which records `changes_requested` and delegates the bounded
revision to the implementer. An `APPROVED` verdict permits the orchestrator to
record `done`.

## Delegation protocol

The orchestrator may use any runtime-supported delegation mechanism. Every
delegated task must include:

- feature ID, requirement IDs, and acceptance-criterion IDs;
- completed dependencies and any unresolved assumption;
- allowed files or subsystem, plus explicit out-of-scope files;
- the baseline revision or explicitly recorded worktree baseline;
- expected report path;
- exact verification commands and any justified manual verification;
- for validators, the implementation report path and the validator's
  report-only write boundary.

The delegated role must write its report before returning. If the runtime
cannot launch subagents, execute the roles sequentially and write the same
reports. The persisted protocol matters more than the API used to run it.

Reusable report templates are in `progress/templates/`.

## Closing a feature

1. The implementer records changed files and verification evidence in
   `progress/impl_<feature>.md`.
2. The validator writes `progress/validation_<feature>.md` with an explicit
   `APPROVED` or `CHANGES_REQUESTED` verdict.
3. Only after approval, the orchestrator changes
   the feature status to `done` and appends a summary to `progress/history.md`.
4. Run `./init.sh` once more and reset `progress/current.md` if the session is
   complete.
