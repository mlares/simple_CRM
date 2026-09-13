# Validation report — CRM-001

## Verdict

APPROVED

## Independence and scope

- Validator: `crm001_harness_validator`
- Implementer: `crm001_harness_implementer`
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188` plus the preserved CRM-001 worktree recorded in `progress/tasks/CRM-001.json`
- Latest implementation evidence: the Python 3.8 closure-compatibility revision appended to `progress/impl_CRM-001.md` on 2026-08-08
- Allowed validator write target: `progress/validation_CRM-001.md`
- Actual validator writes: only this replaced canonical report

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-001-AC01 | `AGENTS.md`, canonical roles, compatibility pointers, adapters, and role-contract tests retain the orchestrator → optional explorer → implementer → validator → orchestrator workflow and changes-requested loop. The compatibility revision did not edit these files. | Pass | Prior approval remains satisfied and unaffected. |
| CRM-001-AC02 | The checker retains all duplicate-ID, dependency, active-feature, transition, report, approval, multi-section evidence, and path-containment checks. Done-state report labels now use the closed mapping `implementation_report -> implementation` and `validation_report -> validation`, avoiding Python 3.9-only string APIs. `test_system_python_validates_done_state_reports` executes a complete approved done fixture through system Python 3.8.10 and receives an empty diagnostic list with exit 0. | Pass | The Python 3.8 closure failure is resolved without weakening rejection or evidence semantics. |
| CRM-001-AC03 | Distinct implementer/validator enforcement, validator report-only ownership, and blocked-implementer handoff contracts and tests remain unchanged by the compatibility revision. | Pass | Prior approval remains satisfied and unaffected. |
| CRM-001-AC04 | `init.sh` invokes the checker with system `python3` before the configured UV command. The checker imports and completes under Python 3.8.10, after which the configured project verification reports 71 passing tests. | Pass | Bootstrap and configured verification both execute successfully. |

## Requirement evidence

| Requirement ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| CRM-001-R01 | Canonical roles and workflow contract | Satisfied | Unchanged by the compatibility revision. |
| CRM-001-R02 | Exclusive ownership and blocked-handoff contracts | Satisfied | Unchanged by the compatibility revision. |
| CRM-001-R03 | Structured task envelope and envelope validation | Satisfied | Unchanged by the compatibility revision. |
| CRM-001-R04 | Complete done-state fixture executed by system Python plus all existing lifecycle fixtures | Satisfied | Exact verdict and per-acceptance evidence checks now close successfully on Python 3.8. |
| CRM-001-R05 | Report templates and canonical adapter mappings | Satisfied | Unchanged by the compatibility revision. |
| CRM-001-R06 | System-interpreter regression plus complete 71-test suite and deterministic command | Satisfied | The focused test prevents reintroduction of `removesuffix` or `removeprefix` calls. |

## Verification

Executed from the repository root:

```text
cd crm && ./init.sh
[OK] harness metadata is valid
[harness] running configured verification command
.......................................................................  [100%]
71 passed in 0.28s
```

```text
UV_CACHE_DIR=/tmp/uv-cache uv run ruff check .
All checks passed!
```

```text
UV_CACHE_DIR=/tmp/uv-cache uv run pytest -q
.......................................................................  [100%]
71 passed in 0.29s
```

```text
git diff --check
```

Result: exited 0 with no whitespace errors.

Focused system-Python reproduction inspected:

```text
system python3: Python 3.8.10
complete approved done-state fixture -> []
exit status -> 0
```

## Findings

- **Compatibility failure and resolution:** an earlier closure attempt reached `str.removesuffix`, which is unavailable in system Python 3.8.10. The revision replaces it with a deterministic mapping over the two constrained report keys; diagnostic labels and iteration order are preserved.
- **Cross-interpreter regression:** `test_system_python_validates_done_state_reports` creates full implementation and validation evidence for a done feature, invokes the actual checker through `shutil.which("python3")`, requires exit 0 and `[]`, and prohibits both incompatible prefix/suffix methods in checker source.
- **Prior validation rounds:** the original changes-requested findings for canonical vocabulary, ownership, append-only evidence parsing, and symlink containment remain resolved. The subsequent approval of AC01–AC04 remains valid; this narrow revision changes only closure compatibility for AC02 and AC04.
- **Lifecycle:** the checker can now evaluate the exact approved verdict and all report evidence during `review -> done` under the interpreter selected by `init.sh`.
- **Security and determinism:** resolved-path containment, exact verdict handling, exact acceptance-ID matching, and stable diagnostics are unchanged; no bypass or order change was introduced.
- **Scope:** the revision is limited to `crm/scripts/harness_check.py`, its focused test, and the append-only implementation report. No role, adapter, state, task, validation, application, or unrelated file was modified by the implementer.
- **Preservation:** the pre-existing staged deletion of `src/simple_crm/__pycache__/__init__.cpython-312.pyc` remains staged and was not restored or otherwise modified.

