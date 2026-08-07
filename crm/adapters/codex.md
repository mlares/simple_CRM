# Codex adapter

Codex reads `AGENTS.md` as the repository contract. Keep this file as a
provider-specific reminder, not a second source of truth.

Map the runtime to the roles in `agents/roles/`:

- main session → `leader`;
- delegated coding session → `implementer`;
- independent read-only validation session → `reviewer`;
- optional research session → `explorer`.

If delegated sessions are unavailable, run the roles sequentially and preserve
the same reports and state transitions.
