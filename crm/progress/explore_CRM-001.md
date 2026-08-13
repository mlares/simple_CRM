# Explorer report — CRM-001 remaining harness gaps

## Question

What remains to satisfy `CRM-001-R03`, `CRM-001-R04`, `CRM-001-R06`, and
`CRM-001-AC02` through `CRM-001-AC04` after the workflow-contract remediation?

## Current evidence

- The canonical roles, ownership boundaries, changes-requested loop, adapters,
  and report templates now exist. This substantially covers the documentation
  portions of R01, R02, R03, R05, AC01, and AC03.
- `./init.sh` currently succeeds: harness metadata is reported valid and
  pytest reports `4 passed`.
- `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` currently reports
  `All checks passed!`.
- CRM-001 and `progress/current.md` both say `in_progress`; every other feature
  is `pending`.
- The current branch is `feature/first_version_with_agents`, based on the
  repository's `master` primary branch. `harness.json` incorrectly declares
  `primary_branch` as `main`.

## Remaining gaps

### R03 — enforceable task envelope

`AGENTS.md` documents the required envelope, but the harness cannot verify that
a delegation actually contains it. There is no structured envelope path or
metadata for feature ID, requirement/acceptance IDs, dependencies, allowed and
excluded scope, baseline, report path, and exact verification commands. The
implementation template contains most of these concepts, but it is a free-form
post-implementation report, not a validated pre-implementation assignment;
it also lacks explicit envelope fields for the expected report path and exact
verification commands.

Add a machine-readable per-feature task-envelope artifact (or equivalent
structured fields in `feature_list.json`) and make it mandatory for every
active feature. Validate its IDs against the selected feature and validate its
report path and non-empty command list.

### R04 / AC02 — metadata and lifecycle enforcement

`scripts/harness_check.py` currently checks duplicate feature IDs, recognized
status strings, at most one `in_progress` feature, and mere existence of two
legacy report paths for `done`. It does **not** check:

- missing, self-referential, duplicate, or non-string dependencies;
- dependency cycles or that dependencies are `done` before activation;
- more than one active feature across `in_progress`, `review`,
  `changes_requested`, and any explicitly defined active `blocked` state;
- the documented legal transition graph (no durable transition record exists);
- canonical `implementation_report` and `validation_report` paths at the
  appropriate lifecycle states;
- an exact `APPROVED` validator verdict before `done`;
- evidence for each acceptance ID in both implementation and validation;
- implementer/validator identity or their required independence;
- canonical role files/templates in `REQUIRED_FILES` (the checker still
  requires legacy `leader.md` and `reviewer.md` instead).

Define the legal status graph in one canonical place and persist structured
transition history so transitions can be checked rather than merely
documented. Add structured implementer, validator, report, verdict, and
acceptance-evidence metadata; parsing free-form Markdown tables would be
fragile. Keep legacy role files optional compatibility pointers, while making
the canonical role files and templates required.

### R06 / AC03 / AC04 — negative tests and deterministic verification

The configured pytest command is real and deterministic, but the checker only
asserts that `test_command` is a string; an empty or whitespace-only command
would pass. The four tests cover the valid repository, a non-object JSON root,
workflow text, and the validator's written boundary. They do not exercise any
AC02 rejection case or machine-check implementer/validator independence.

Make `check()` accept an explicit root (defaulting to the repository root) so
tests can build isolated metadata fixtures. Add positive and negative tests
for duplicate IDs, missing dependencies, cycles, multiple active features,
illegal transitions, missing reports/evidence, non-approved validation, and
same-agent implementation/validation. Require a non-blank test command and
add an assertion that the configured primary branch is `master`. Retain an
end-to-end test or captured run proving `./init.sh` invokes both the harness
checker and pytest.

## Report and state consistency

- `progress/impl_CRM-001.md` documents the completed slices but explicitly
  leaves R03/R04 open.
- The only validation artifact is the legacy
  `progress/review_CRM-001.md`; its latest verdict is `CHANGES_REQUESTED` and
  predates the visible remediation. There is no canonical
  `progress/validation_CRM-001.md`, so CRM-001 cannot be closed yet.
- `progress/current.md` still says to await remediation even though the
  remediation files and appended implementation report now exist. The
  orchestrator should update it before delegating the harness-enforcement
  slice.
- CRM-001 currently has no structured implementation/validation report fields;
  those should be populated only at the lifecycle point required by the final
  schema and never inferred from filenames alone.

## Recommended next bounded slice

Delegate R03, R04, R06, AC02, the enforcement portion of AC03, and AC04 to one
implementer. Limit changes to `harness.json`, `scripts/harness_check.py`,
focused tests, task/report metadata or templates, and the implementation
report. Then assign a different validator to write
`progress/validation_CRM-001.md`. Only after an `APPROVED` verdict and a final
successful `./init.sh` run should the orchestrator record canonical report
paths, move CRM-001 to `done`, and append session history.
