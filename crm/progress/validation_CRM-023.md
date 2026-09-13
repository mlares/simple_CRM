# Validation report — `CRM-023`

## Verdict

`APPROVED`

## Independence and scope

- Validator: `crm023_policy_validator`.
- Persisted validator assignment: `gpt-5.6-sol` / `high` /
  `role_default`.
- Actual validator runtime: `gpt-5.6-sol` with reasoning effort `high`; the
  runtime matched the persisted assignment and no override was used.
- Implementer: `crm023_policy_implementer`, assigned and reported as
  `gpt-5.6-terra` / `high` / `role_default`. The validator agent ID differs
  from the implementer agent ID.
- Orchestrator: `crm023_policy_orchestrator`, persisted as `gpt-5.6-sol` /
  `high` / `role_default`.
- Baseline inspected: `fcbe3b4ea14e155084019f9248a909826397d188`;
  this is the current `HEAD` and the recorded dirty-worktree baseline.
- Dependency: `CRM-001` is `done` and records
  `progress/validation_CRM-001.md`.
- Implementation report inspected: `progress/impl_CRM-023.md`.
- Allowed validator write target: `progress/validation_CRM-023.md` only.

## Requirement traceability

| Requirement ID | Evidence inspected | Result | Independent finding |
| --- | --- | --- | --- |
| `CRM-023-R01` | `harness.json` `agent_policy.supported_models` and `role_defaults`; policy fixtures in `crm/tests/test_harness_check.py` | Pass | Sol, Terra, and Luna are catalogued with the supported reasoning-effort schema. Defaults are exactly Sol/high orchestrator, Terra/high implementer, Sol/high validator, and Luna/medium explorer. |
| `CRM-023-R02` | Active `progress/tasks/CRM-023.json`; `_validate_task_envelope` and `_validate_agent_assignments` in `crm/scripts/harness_check.py`; task-envelope template | Pass | The active envelope resolves orchestrator, implementer, and validator with agent ID, model, reasoning effort, and source. Explorer remains optional and is represented in the template. `role_default` and `override` semantics are persisted. |
| `CRM-023-R03` | Checker assignment validation and isolated negative fixtures in `crm/tests/test_harness_check.py` | Pass | The checker rejects missing active roles, unsupported model/effort values, role-default mismatches, shared implementer/validator identity, and blank override reasons; a supported justified override is accepted. |
| `CRM-023-R04` | `AGENTS.md`; all canonical role files; `CLAUDE.md`; Codex, Copilot, generic, and provider adapter instructions; focused contract tests | Pass | Canonical instructions require launching from the persisted assignment, permit only a recorded justified override, preserve implementer/validator independence, and require actual model/reasoning reporting. |
| `CRM-023-R05` | `scripts/verify-fast.sh`, `harness.json.test_command`, `crm/init.sh`, and the terminating end-to-end run | Pass | Verification performs `uv sync --locked --offline`, invokes direct `.venv/bin` tools, contains no `uv run`, and `crm/init.sh` terminates successfully. |

## Acceptance evidence

| Acceptance ID | Evidence inspected | Result | Finding or follow-up |
| --- | --- | --- | --- |
| `CRM-023-AC01` | Actual `harness.json` values and canonical-default fixture | Pass | Exact defaults are Sol/high for orchestrator and validator, Terra/high for implementer, and Luna/medium for explorer. |
| `CRM-023-AC02` | Checker source plus focused isolated negative/positive pytest cases | Pass | The focused run exercised every required rejection class and the valid-override path: 12 tests passed. |
| `CRM-023-AC03` | Active task envelope, implementation report, current orchestration record, and this independent validation runtime | Pass | Exact assignments are persisted and runtime reports match them: orchestrator Sol/high, implementer Terra/high, validator Sol/high, all from `role_default`; IDs are distinct where required. |
| `CRM-023-AC04` | Canonical role and adapter files plus `test_agent_contracts.py` | Pass | Persisted assignment, justified deviation, and actual-runtime reporting requirements are explicit; focused contract tests pass. |
| `CRM-023-AC05` | `timeout 60s ./crm/init.sh` | Pass | Exited 0 in about 3.7 seconds, ran the complete configured suite, and printed `[harness] ready`. |

## Verification

All task-envelope commands were run independently from the repository root.

```text
$ python3 crm/scripts/harness_check.py
[OK] harness metadata is valid
(exit 0)

$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q
108 passed in 1.13s
(exit 0)

$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check .
All checks passed!
(exit 0)

$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check .
59 files already formatted
(exit 0)

$ timeout 60s ./crm/init.sh
[OK] harness metadata is valid
Resolved 76 packages in 0.90ms
Checked 74 packages in 0.93ms
All checks passed!
59 files already formatted
0 files would be updated.
Success: no issues found in 27 source files
108 passed in 1.18s
System check identified no issues (0 silenced).
No changes detected
System check identified no issues (0 silenced).
[harness] ready
(exit 0)

$ git diff --check
(no output; exit 0)
```

Additional focused evidence:

```text
$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q \
    <required assignment-negative cases, valid override, and role/adapter contracts>
12 passed in 0.13s
(exit 0)
```

## Findings

- Scope: the CRM-023 implementation remains within its delegated harness,
  policy, contract, test, template, and verification-script scope. CRM business
  functionality was not changed by this feature.
- Baseline preservation: the recorded baseline equals `HEAD`; the pre-existing
  dirty CRM-001/CRM-002 work remains present, and the staged deletion of
  `src/simple_crm/__pycache__/__init__.cpython-312.pyc` remains the only staged
  change.
- Security: the policy adds no credentials, account identifiers, network API
  calls, or application authorization surface. Assignment paths remain bounded
  by the existing task-envelope validation.
- Architecture: the implementation keeps policy metadata provider-neutral and
  adapters thin; role ownership and independent validation remain canonical.
- Regression: the full deterministic suite and focused policy tests pass. No
  unresolved scope, safety, architecture, or regression finding blocks
  approval.
