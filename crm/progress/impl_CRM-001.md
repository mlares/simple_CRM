# Implementation report — CRM-001 verification slice

## Scope

User-authorized subset of CRM-001:

- Correct the two existing Ruff findings in the harness checker.
- Configure a non-empty, deterministic test command.
- Add a minimal executable test that validates the current harness metadata.

The broader CRM-001 agent-workflow requirements remain open. This report does
not request feature closure.

## Changed files

- `crm/scripts/harness_check.py`
  - Removed the extra blank line that violated import-block formatting.
  - Raised `TypeError` when JSON content has the wrong top-level type.
- `crm/harness.json`
  - Configured `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q` as the test
    command run by `crm/init.sh`.
- `crm/tests/test_harness_check.py`
  - Added a pytest test that loads the repository harness checker by explicit
    path and asserts that current metadata is valid.

## Deliberate non-changes

- No agent-role contract, architecture document, or feature status change was
  made by the implementer slice.
- The pre-existing staged deletion of
  `src/simple_crm/__pycache__/__init__.cpython-312.pyc` was not touched.

## Verification

Executed from the repository root:

```text
cd crm && ./init.sh
[OK] harness metadata is valid
[harness] running configured verification command
.                                                                        [100%]
2 passed
```

```text
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .
```

Result: exited 0 with no findings.

```text
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
```

Result: exited 0; `2 passed`.

```text
git diff --check
```

Result: exited 0 with no whitespace errors.

---

# Implementation report — CRM-001 workflow-contract remediation (2026-08-07)

## Scope

This remediation implements the documented portions of CRM-001 R01, R02, and
R05, together with AC01 and the instruction portion of AC03. It does not alter
feature-state metadata, harness enforcement, application source, or the
user-staged bytecode deletion.

## Task envelope

- Baseline: the active CRM-001 worktree, including the separately approved
  Ruff/test-command slice.
- Requirement IDs: `CRM-001-R01`, `CRM-001-R02`, and the documentation portion
  of `CRM-001-R05`.
- Acceptance IDs: `CRM-001-AC01` and the instruction portion of
  `CRM-001-AC03`.
- Allowed scope: workflow contracts, adapters, reusable report templates,
  focused contract tests, and Ruff import ordering.
- Out of scope: `feature_list.json`, `harness.json`, harness enforcement,
  application source, and prior report content.

## Changed files and decisions

- `crm/AGENTS.md`
  - Defines the canonical orchestrator → optional explorer → implementer →
    validator → orchestrator closure sequence, exclusive ownership, state
    transitions, changes-requested loop, and required task-envelope fields.
- `crm/agents/README.md` and `crm/agents/roles/`
  - Adds canonical `orchestrator.md` and `validator.md`; updates
    `implementer.md` ownership; keeps `leader.md` and `reviewer.md` as explicit
    compatibility pointers.
- `crm/adapters/`, `crm/CLAUDE.md`, and `crm/CHECKPOINTS.md`
  - Maps runtime vocabulary and evidence checkpoints to the canonical roles.
- `crm/progress/templates/implementation_report.md` and
  `crm/progress/templates/validation_report.md`
  - Provide reusable, evidence-oriented report templates.
- `crm/tests/test_agent_contracts.py`
  - Adds focused regression coverage for the canonical sequence,
    changes-requested loop, role files, implementer/validator independence,
    and the validator report-only boundary.
- `crm/scripts/harness_check.py` and `crm/tests/test_harness_check.py`
  - Applies Ruff's required import ordering only; these files otherwise retain
    the prior approved verification-slice behavior.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| `CRM-001-AC01` | Canonical workflow and loop in `AGENTS.md`; canonical role files and adapter mappings. | `test_canonical_workflow_roles_and_changes_loop_are_documented` passes. | Pass |
| `CRM-001-AC03` (instruction portion) | `validator.md` requires an independent validator and restricts writes to `progress/validation_<feature>.md`. | `test_validator_write_boundary_is_explicit` passes. | Pass |
| `CRM-001-R05` documentation portion | Reusable implementation and validation templates exist beneath `progress/templates/`. | Full pytest suite passes. | Pass |

## Verification

Executed from the repository root:

```text
cd crm && ./init.sh
[OK] harness metadata is valid
[harness] running configured verification command
....                                                                     [100%]
4 passed in 0.05s
```

```text
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .
```

Result: `All checks passed!`

```text
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
```

Result: `4 passed in 0.04s`.

```text
git diff --check
```

Result: exited 0 with no whitespace errors.

## Remaining work

CRM-001 remains in progress. This slice deliberately leaves automated
task-envelope and metadata enforcement (R03/R04) to the subsequent harness
implementation work.

## Verification supplement

The final import-order correction places `sys` before `json`, as required by
the configured Ruff version. The requested checks were re-run from `crm`:

```text
./init.sh
[OK] harness metadata is valid
[harness] running configured verification command
..                                                                       [100%]
2 passed in 0.04s

UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .
```

Result: exited 0; Ruff reported no findings.

---

# Implementation report — CRM-001 structured harness enforcement (2026-08-08)

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188`, plus the preserved
  dirty CRM-001 worktree described in `progress/tasks/CRM-001.json`.
- Requirement IDs: `CRM-001-R03`, `CRM-001-R04`, `CRM-001-R06`.
- Acceptance-criterion IDs: `CRM-001-AC02`, `CRM-001-AC03`,
  `CRM-001-AC04`.
- Dependencies: none.
- Allowed scope: `crm/harness.json`, `crm/scripts/harness_check.py`,
  `crm/tests/test_harness_check.py`,
  `crm/progress/templates/task_envelope.json`, and this append-only report.
- Out of scope: feature/session state, role and adapter contracts,
  project-specific docs, application source, validation reports, and every
  unrelated dirty-worktree change.
- Implementation report: `progress/impl_CRM-001.md`.
- Validation report: `progress/validation_CRM-001.md`.
- Implementer: `crm001_harness_implementer`.
- Independent validator: `crm001_harness_validator`.
- Exact verification commands:
  `cd crm && ./init.sh`;
  `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`;
  `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q`;
  `git diff --check`.

## Changed files and decisions

- `crm/harness.json`
  - Sets the repository's actual primary branch to `master` and retains the
    deterministic pytest command executed by `init.sh`.
- `crm/scripts/harness_check.py`
  - Makes `check(root)` independently testable while keeping the repository
    root as the CLI default.
  - Requires the canonical role and task/implementation/validation template
    files.
  - Validates globally unique feature, requirement, and acceptance IDs;
    dependency list shape, uniqueness, existence, self-reference, cycles, and
    completion gates; the one-active-feature rule; legal status histories;
    active-feature task envelopes; canonical report paths; independent agent
    assignments; and exact nonblank verification commands.
  - Requires both canonical reports before `done`, an exact `APPROVED`
    validation verdict, and a populated positive evidence-table row for every
    acceptance ID in both reports.
  - Emits diagnostics in stable file, feature, field, dependency, and
    acceptance order. Pending features may omit `status_history` only as an
    implicit initial `pending` state; every later state must persist history.
  - Supports the system Python used by `init.sh`; the adjacent-history loop
    deliberately avoids the newer `itertools.pairwise` API.
- `crm/tests/test_harness_check.py`
  - Builds isolated temporary harness roots and supplies positive pending,
    active, and done cases.
  - Adds negative fixtures for canonical-file absence, every ID class,
    dependency shape/duplicates/missing/self-reference/cycles/completion,
    every active-status rule, status transitions, branch/command metadata,
    missing and malformed envelopes, every required envelope field, scope
    overlap, same-agent assignment, review/change/done report requirements,
    exact approval, and evidence absence from either report.
  - Confirms acceptance-ID mentions outside the evidence table do not count
    as evidence and that diagnostics are repeatable.
- `crm/progress/templates/task_envelope.json`
  - Provides a reusable structured envelope containing every field enforced
    for active features.
- `crm/progress/impl_CRM-001.md`
  - Appends this task envelope, decision record, acceptance mapping, and exact
    command results without altering prior evidence.

The pre-existing staged deletion of
`src/simple_crm/__pycache__/__init__.cpython-312.pyc` was preserved and was not
modified by this task.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| `CRM-001-AC02` | The checker rejects duplicate IDs, missing/invalid dependencies, dependency cycles, multiple active features, missing evidence, missing reports, and non-approved done state. | Isolated positive and negative cases in `crm/tests/test_harness_check.py`; complete suite reports 60 passing tests. | Pass |
| `CRM-001-AC03` | Active task envelopes require nonblank implementer and validator identities and reject equal assignments; canonical validator report paths are enforced. | `test_implementer_cannot_be_validator`, envelope-field tests, and the existing validator write-boundary contract test pass. | Pass |
| `CRM-001-AC04` | `harness.json` has a nonblank deterministic pytest command; `init.sh` invokes the checker before executing that command. | `cd crm && ./init.sh` reports valid metadata and 60 passing tests. | Pass |

## Requirement evidence

| Requirement ID | Evidence | Result |
| --- | --- | --- |
| `CRM-001-R03` | Structured envelope template plus active-state validation of IDs, dependencies, scope boundaries, baseline, canonical reports, agent identities, and exact commands. | Pass |
| `CRM-001-R04` | Root-parameterized checker and isolated fixtures cover dependency integrity, one active feature, report paths, legal transitions, approval, and per-acceptance evidence. | Pass |
| `CRM-001-R06` | Deterministic test command and 58 focused harness tests, alongside two workflow-contract tests. | Pass |

## Verification

Executed from the repository root after the implementation changes:

```text
cd crm && ./init.sh
[OK] harness metadata is valid
[harness] running configured verification command
............................................................             [100%]
60 passed in 0.23s
```

Result: exited 0. The script ran metadata validation before the configured
pytest command.

```text
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .
All checks passed!
```

Result: exited 0 with no Ruff findings.

```text
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
............................................................             [100%]
60 passed in 0.21s
```

Result: exited 0.

```text
git diff --check
```

Result: exited 0 with no whitespace errors.

## Risks and follow-up

- This slice enforces CRM-001's persisted delivery protocol; it does not mark
  the feature approved or done. The independent validator must inspect the
  diff and write `progress/validation_CRM-001.md` before orchestrator closure.
- Markdown evidence validation intentionally requires a positive populated
  table row, not arbitrary prose. Future report-format changes must update the
  checker and its fixtures together.

---

# Implementation report — CRM-001 validation revision (2026-08-08)

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188`, plus the preserved
  changes-requested CRM-001 worktree described in
  `progress/tasks/CRM-001.json`.
- Requirement IDs: `CRM-001-R01`, `CRM-001-R02`, `CRM-001-R04`.
- Acceptance-criterion IDs: `CRM-001-AC01`, `CRM-001-AC02`,
  `CRM-001-AC03`.
- Dependencies: none.
- Allowed scope: explorer and implementer role contracts, the harness checker,
  focused harness and agent-contract tests, and this append-only report.
- Out of scope: feature/session/history state, task-envelope contents,
  orchestrator and validator contracts, adapters, application source, and the
  validator's report.
- Implementation report: `progress/impl_CRM-001.md`.
- Validation report: `progress/validation_CRM-001.md`.
- Implementer: `crm001_harness_implementer`.
- Independent validator: `crm001_harness_validator`.
- Exact verification commands:
  `cd crm && ./init.sh`;
  `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`;
  `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q`;
  `git diff --check`.

## Changed files and decisions

- `crm/agents/roles/explorer.md`
  - Replaces all operational `leader` vocabulary with the canonical
    `orchestrator` role.
- `crm/agents/roles/implementer.md`
  - Routes a blocked implementer's evidence through
    `progress/impl_<feature>.md` and an orchestrator handoff.
  - Explicitly prohibits blocked implementers from editing the
    orchestrator-owned `progress/current.md`.
- `crm/scripts/harness_check.py`
  - Scans every appended `## Acceptance evidence` section and continues past
    incomplete or nonmatching rows until a concrete positive exact-ID row is
    found.
  - Resolves the harness root and candidate metadata path, then enforces real
    path containment. Literal traversal and absolute paths remain rejected,
    in-root files and symlinks remain accepted, and symlinks escaping the root
    are rejected.
- `crm/tests/test_harness_check.py`
  - Adds normal-path, in-root-symlink, and escaping-symlink containment cases.
  - Adds a synthetic append-only report with evidence in a later section.
  - Exercises the actual multi-section CRM-001 implementation report and
    requires AC01, AC02, AC03, and AC04 all to be discoverable.
- `crm/tests/test_agent_contracts.py`
  - Locks the explorer to canonical orchestrator vocabulary and the blocked
    implementer to its own report plus orchestrator handoff.
- `crm/progress/impl_CRM-001.md`
  - Appends this bounded revision record without altering earlier evidence.

No feature, session, history, task-envelope, validation-report, application,
or unrelated worktree file was edited. The staged deletion of
`src/simple_crm/__pycache__/__init__.cpython-312.pyc` remains preserved.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| `CRM-001-AC01` | The canonical explorer role now delegates, reports, and returns findings only through the orchestrator vocabulary. | `test_explorer_uses_only_canonical_orchestrator_vocabulary` passes. | Pass |
| `CRM-001-AC02` | Evidence discovery covers every appended evidence section, and real-path containment prevents canonical metadata symlinks from escaping the harness root. | Synthetic multi-section, actual CRM-001 report, direct path, in-root symlink, and escaping-symlink tests pass. The validator reproduction returns `True` for AC01–AC04. | Pass |
| `CRM-001-AC03` | The implementer contract records blockers only in its implementation report and hands them to the orchestrator without editing session state. | `test_blocked_implementer_reports_without_editing_session_state`, same-agent rejection, and validator-boundary tests pass. | Pass |

## Requirement evidence

| Requirement ID | Evidence | Result |
| --- | --- | --- |
| `CRM-001-R01` | Explorer instructions contain no legacy `leader` vocabulary and consistently name the orchestrator. | Pass |
| `CRM-001-R02` | Blocked implementer ownership no longer contradicts the orchestrator's exclusive ownership of `progress/current.md`. | Pass |
| `CRM-001-R04` | Append-only evidence and resolved containment are enforced with integration and security regression coverage. | Pass |

## Verification

Executed from the repository root after all bounded revision changes:

```text
cd crm && ./init.sh
[OK] harness metadata is valid
[harness] running configured verification command
......................................................................   [100%]
70 passed in 0.27s
```

Result: exited 0; metadata validation ran before the configured pytest suite.

```text
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .
All checks passed!
```

Result: exited 0 with no Ruff findings.

```text
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
......................................................................   [100%]
70 passed in 0.27s
```

Result: exited 0.

```text
git diff --check
```

Result: exited 0 with no whitespace errors.

The validator's original reproduction now produces:

```text
{'CRM-001-AC01': True, 'CRM-001-AC02': True, 'CRM-001-AC03': True, 'CRM-001-AC04': True}
```

## Risks and follow-up

- The previous validation verdict remains `CHANGES_REQUESTED` as immutable
  evidence of that pass. The independent validator must re-run its checks and
  append or replace its own report according to the orchestrator's validation
  protocol before CRM-001 can close.
- Evidence-table parsing remains intentionally Markdown-specific; the test
  suite now protects the append-only multi-section report shape used by this
  repository.

---

# Implementation report — CRM-001 Python 3.8 closure compatibility (2026-08-08)

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188`, plus the preserved
  changes-requested CRM-001 worktree described in
  `progress/tasks/CRM-001.json`.
- Requirement IDs: `CRM-001-R04`, `CRM-001-R06`.
- Acceptance-criterion IDs: `CRM-001-AC02`, `CRM-001-AC04`.
- Dependencies: none.
- Allowed scope: `crm/scripts/harness_check.py`,
  `crm/tests/test_harness_check.py`, and this append-only report.
- Out of scope: orchestrator state and history, task and validation files,
  roles, adapters, application source, and every unrelated worktree change.
- Implementation report: `progress/impl_CRM-001.md`.
- Validation report: `progress/validation_CRM-001.md`.
- Implementer: `crm001_harness_implementer`.
- Independent validator: `crm001_harness_validator`.
- Exact verification commands:
  `cd crm && ./init.sh`;
  `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .`;
  `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q`;
  `git diff --check`.

## Python 3.8 closure reproduction and strategy

The closure failure was reproduced by the orchestrator after CRM-001 entered
`done`: system `python3` is version `3.8.10`, and done-state report validation
reached this call:

```text
report_key.removesuffix("_report")
AttributeError: 'str' object has no attribute 'removesuffix'
```

`str.removesuffix` was introduced after Python 3.8. The harness itself must
remain executable by system `python3` because `crm/init.sh` invokes it before
the UV-managed Python 3.12 test environment exists in that process. The fix
uses a closed deterministic mapping from the two already constrained report
keys to their diagnostic labels:

```text
implementation_report -> implementation
validation_report -> validation
```

The adjacent checker scan covered `removeprefix`, `pairwise`, `zip(strict=)`,
`Path.is_relative_to`, structural pattern matching, `tomllib`, and related
post-3.8 runtime calls. No other such runtime API remains. Modern built-in
generic and union syntax appears only in annotations protected by
`from __future__ import annotations`, and the checker imports and executes
successfully under Python 3.8.10.

## Changed files and decisions

- `crm/scripts/harness_check.py`
  - Replaces `str.removesuffix` with the explicit two-key diagnostic-label
    mapping while preserving diagnostic text and iteration order.
- `crm/tests/test_harness_check.py`
  - Adds a complete approved `done` fixture and invokes the checker over that
    fixture with the same system `python3` resolved by `init.sh`.
  - Requires a zero exit, an empty diagnostic list, and absence of both
    `removesuffix` and `removeprefix` calls in checker source.
- `crm/progress/impl_CRM-001.md`
  - Appends this compatibility rationale and verification evidence.

No state, task, validation, role, adapter, application, or unrelated file was
edited. The staged deletion of
`src/simple_crm/__pycache__/__init__.cpython-312.pyc` remains preserved.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| `CRM-001-AC02` | Done-state implementation and validation report inspection now uses only Python-3.8-compatible runtime APIs while retaining exact verdict and acceptance-evidence enforcement. | `test_system_python_validates_done_state_reports` executes an approved done fixture through system Python 3.8.10 and receives `[]` with exit 0; the full suite passes. | Pass |
| `CRM-001-AC04` | The checker invoked directly by `crm/init.sh` remains compatible with system Python before the configured UV command runs. | `cd crm && ./init.sh` validates harness metadata and then reports 71 passing tests. | Pass |

## Requirement evidence

| Requirement ID | Evidence | Result |
| --- | --- | --- |
| `CRM-001-R04` | Done-state report-path and per-acceptance validation execute successfully under system Python 3.8.10. | Pass |
| `CRM-001-R06` | A focused cross-interpreter closure regression prevents reintroduction of the incompatible string APIs. | Pass |

## Verification

Executed from the repository root after the bounded compatibility change:

```text
cd crm && ./init.sh
[OK] harness metadata is valid
[harness] running configured verification command
.......................................................................  [100%]
71 passed in 0.31s
```

Result: exited 0; system-Python metadata validation completed before the
configured UV-managed pytest command.

```text
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .
All checks passed!
```

Result: exited 0 with no Ruff findings.

```text
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
.......................................................................  [100%]
71 passed in 0.31s
```

Result: exited 0.

```text
git diff --check
```

Result: exited 0 with no whitespace errors.

## Risks and follow-up

- CRM-001 remains under orchestrator control. The compatibility change is
  ready for independent revalidation and a fresh closure attempt.
- The regression intentionally uses system `python3`, matching `init.sh`; if
  that bootstrap interpreter changes, the same test continues to exercise the
  interpreter actually selected by the harness entry point.
