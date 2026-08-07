# Claude Code adapter

`AGENTS.md` is the canonical contract for this repository. Read it first and
follow the role files under `agents/roles/`.

When Claude Code subagents are available, map them as follows:

- the main session acts as `leader`;
- an implementation subagent acts as `implementer`;
- a separate validation subagent acts as `reviewer`;
- optional read-only research subagents act as `explorer`.

Do not pass large reports through the conversation. Ask each subagent to write
its report to the path specified in the task and return only that path.
