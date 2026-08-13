# Validation report — CRM-001 verification slice

## Verdict

**APPROVED** for the user-authorized lint and test-command slice only.

CRM-001 remains `in_progress`; this validation does not approve closure of its
remaining agent-workflow requirements.

## Scope reviewed

- The two Ruff findings in `crm/scripts/harness_check.py`.
- The non-empty test command in `crm/harness.json`.
- The new pytest coverage in `crm/tests/test_harness_check.py`.
- The implementation report at `progress/impl_CRM-001.md`.

## Acceptance evidence

| Requested outcome | Evidence | Result |
| --- | --- | --- |
| Fix import-block lint finding | `UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .` completed with no findings. | Pass |
| Fix exception-type lint finding | `load_json()` now raises `TypeError`; pytest verifies a JSON list is rejected. | Pass |
| Configure a real test command | `crm/harness.json` invokes `UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q`; `crm/init.sh` runs it. | Pass |
| Execute a real test suite | `cd crm && ./init.sh` completed with `2 passed`. | Pass |

## Verification executed

```text
cd crm && ./init.sh
[OK] harness metadata is valid
[harness] running configured verification command
..                                                                       [100%]
2 passed in 0.04s
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

## Scope and repository notes

- The pre-existing staged deletion of
  `src/simple_crm/__pycache__/__init__.cpython-312.pyc` was not reviewed as
  part of this slice and remains untouched.
- The harness still declares `main` as its primary branch despite the project
  convention being `master`; address that in the remaining CRM-001 work.
- The broader CRM-001 requirements (canonical role names, stricter state and
  dependency checks, report templates, and adapter updates) remain open.

---

# Validation report — CRM-001 workflow-contract slice (2026-08-07)

## Verdict

**CHANGES_REQUESTED**

## Scope reviewed

- R01: canonical `orchestrator`, `implementer`, and `validator` roles with
  optional `explorer`.
- R02: exclusive ownership and documented state transitions.
- R05 documentation: canonical adapter mapping and reusable report templates.
- AC01 and the instruction portion of AC03.

## Evidence and findings

| Criterion | Evidence inspected | Result |
| --- | --- | --- |
| R01 / AC01 canonical workflow | `crm/agents/roles/` still contains only `leader.md`, `implementer.md`, `reviewer.md`, and `explorer.md`; `AGENTS.md` and `agents/README.md` still describe leader/reviewer. | Fail |
| R02 ownership and state transitions | `AGENTS.md` continues to assign `progress/current.md` updates to implementers and does not define exclusive orchestrator/validator ownership or the changes-requested loop. | Fail |
| R05 adapters and templates | `CLAUDE.md` and files in `adapters/` still map to leader/reviewer; no reusable report templates exist under `progress/`. | Fail |
| AC03 validator instruction boundary | `reviewer.md` says it must not edit implementation files, but no canonical `validator.md` exists and no report-only validator write boundary is defined. | Fail |
| Focused contract coverage | `crm/tests/` contains only metadata-check tests; no test covers canonical roles, sequence, or validator write boundary. | Fail |

No scoped workflow-contract implementation diff is present. The existing
changes are the separately reviewed Ruff/test-command slice, feature/session
state, and the user-staged bytecode deletion; they do not satisfy this slice.

## Verification executed

```text
cd crm && ./init.sh
[OK] harness metadata is valid
[harness] running configured verification command
..                                                                       [100%]
2 passed in 0.05s
```

```text
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .
```

Result: failed with two `I001` import-order findings in
`crm/scripts/harness_check.py` and `crm/tests/test_harness_check.py`.

```text
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
```

Result: passed; `2 passed in 0.05s`.

```text
git diff --check
```

Result: passed with no whitespace errors.

## Required remediation

Implement the scoped canonical role documents, ownership/state-transition
contract, adapter mappings, reusable templates, and focused contract tests.
Also restore Ruff compliance without altering the user-staged deletion.
