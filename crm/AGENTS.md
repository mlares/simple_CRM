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
- Keep feature state in `feature_list.json`, not only in chat.
- Keep live session state in `progress/current.md`.
- Implementers write tests or other executable verification with their change.
- Reviewers do not edit implementation files.
- Do not mark a feature `done` without a passing verification run and an
  approved review report.
- Subagents return a short pointer to their report; the report itself lives on
  disk under `progress/`.

## Delegation protocol

The leader may use any runtime-supported mechanism to delegate work. The
message sent to a role must include:

- the feature id and acceptance criteria;
- the files or subsystem in scope;
- the expected report path;
- the required verification command.

The delegated role must write its report before returning. If the runtime
cannot launch subagents, execute the roles sequentially and write the same
reports. The persisted protocol matters more than the API used to run it.

## Closing a feature

1. The implementer records changed files and verification evidence in
   `progress/impl_<feature>.md`.
2. The reviewer writes `progress/review_<feature>.md` with an explicit
   `APPROVED` or `CHANGES_REQUESTED` verdict.
3. Only after approval, the leader (or the designated workflow owner) changes
   the feature status to `done` and appends a summary to `progress/history.md`.
4. Run `./init.sh` once more and reset `progress/current.md` if the session is
   complete.
