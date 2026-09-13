# Implementation report — `CRM-023`

## Task envelope

- Baseline: `fcbe3b4ea14e155084019f9248a909826397d188` dirty worktree baseline;
  existing CRM-001, CRM-002, and staged bytecode-deletion work was preserved.
- Requirement IDs: `CRM-023-R01`, `CRM-023-R02`, `CRM-023-R03`,
  `CRM-023-R04`, `CRM-023-R05`.
- Acceptance-criterion IDs: `CRM-023-AC01`, `CRM-023-AC02`,
  `CRM-023-AC03`, `CRM-023-AC04`, `CRM-023-AC05`.
- Allowed scope: the harness, role/adapter contracts, task template, harness
  tests, fast verification script, and this report only.
- Out of scope: feature/session state, task envelopes, CRM application code,
  dependency metadata, and business functionality.
- Dependencies and assumptions: CRM-001 is complete. The active CRM-023 task
  already persists the orchestrator, implementer, and validator assignments.
- Persisted assignment: `crm023_policy_implementer` / `gpt-5.6-terra` /
  `high` / `role_default`.
- Actual runtime: `gpt-5.6-terra` with reasoning effort `high` (no override).

## Changed files and decisions

- `crm/harness.json`: added the supported GPT-5.6 Sol, Terra, and Luna model
  catalog, supported reasoning efforts, and canonical role defaults.
- `crm/scripts/harness_check.py`: validates policy metadata and active-task
  assignments, including required roles, supported combinations, default
  consistency, override reasons, and implementer/validator independence.
- `crm/progress/templates/task_envelope.json`: documents resolved assignment
  entries, including optional explorer assignment.
- `crm/AGENTS.md`, `crm/agents/`, `crm/CLAUDE.md`, and `crm/adapters/`:
  require runtime delegation from the persisted assignment and actual-runtime
  model/reasoning reporting.
- `crm/tests/test_harness_check.py` and `crm/tests/test_agent_contracts.py`:
  cover the positive policy and isolated negative policy fixtures.
- `scripts/verify-fast.sh`: performs `uv sync --locked --offline` and invokes
  `.venv/bin` tools directly, avoiding the hanging `uv run` wrapper.

## Acceptance evidence

| Acceptance ID | Implementation evidence | Verification evidence | Result |
| --- | --- | --- | --- |
| `CRM-023-AC01` | `agent_policy.role_defaults` records Sol/high orchestrator and validator, Terra/high implementer, and Luna/medium explorer. | Harness check passed; policy-default fixture passed. | Pass |
| `CRM-023-AC02` | Checker rejects missing active roles, unsupported models/efforts, default mismatches, shared implementer/validator IDs, and blank override reasons. | Isolated positive and negative fixtures passed in the 108-test suite. | Pass |
| `CRM-023-AC03` | Active `CRM-023` envelope contains exact resolved assignments; checker cross-checks implementer/validator aliases and agent IDs. | `python3 crm/scripts/harness_check.py` exited 0. | Pass |
| `CRM-023-AC04` | Canonical role files and adapters require persisted assignments, justified overrides, and actual-runtime reporting. | Focused contract tests passed in the 108-test suite. | Pass |
| `CRM-023-AC05` | `scripts/verify-fast.sh` uses locked offline sync and direct `.venv/bin` tools. | `timeout 60s ./crm/init.sh` exited 0 and printed `[harness] ready`. | Pass |

## Verification

```text
$ python3 crm/scripts/harness_check.py
[OK] harness metadata is valid

$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q
108 passed in 1.32s

$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff check .
All checks passed!

$ PYTHONDONTWRITEBYTECODE=1 .venv/bin/ruff format --check .
58 files already formatted

$ timeout 60s ./crm/init.sh
[OK] harness metadata is valid
Resolved 76 packages in 1ms
Checked 74 packages in 1ms
108 passed in 1.28s
[harness] ready

$ git diff --check
(no output; exited 0)
```

## Risks and follow-up

The model catalog is intentionally limited to the supported GPT-5.6 Sol,
Terra, and Luna entries currently used by this harness. A later model addition
must update `harness.json` and pass the same checker validation before it can
be assigned to an active task.
