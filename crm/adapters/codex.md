# Codex adapter

Codex reads `AGENTS.md` as the repository contract. Keep this file as a
provider-specific reminder, not a second source of truth.

Map the runtime to the roles in `agents/roles/`:

- main session → `orchestrator`;
- delegated coding session → `implementer`;
- independent validation session → `validator`;
- optional research session → `explorer`.

If delegated sessions are unavailable, run the roles sequentially and preserve
the same reports and state transitions.

Before each launch, read the persisted assignment from the active task envelope
and pass its model and reasoning effort to the Codex session. Use only a
justified override recorded in that envelope, keep implementer and validator
agent IDs independent, and require every report to state the actual model and
reasoning effort used.
