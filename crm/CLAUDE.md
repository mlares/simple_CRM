# Claude Code adapter

`AGENTS.md` is the canonical contract for this repository. Read it first and
follow the role files under `agents/roles/`.

When Claude Code subagents are available, map them as follows:

- the main session acts as `orchestrator`;
- an implementation subagent acts as `implementer`;
- a separate validation subagent acts as `validator`;
- optional read-only research subagents act as `explorer`.

Do not pass large reports through the conversation. Ask each subagent to write
its report to the path specified in the task and return only that path.

Before starting or delegating, read the persisted assignment in the active task
envelope and the supported policy in `harness.json`. Launch every role with
its recorded model and reasoning effort, honor a justified override only when
the envelope records it, and report the actual model and reasoning effort used
in the role report.
