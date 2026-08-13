# Generic agent adapter

For an agent runtime without a standard repository-instruction file:

1. Load `AGENTS.md` at session start.
2. Use `agents/roles/` as the role prompt source.
3. Use `feature_list.json` and `progress/current.md` as the persisted state.
4. Require implementation and validation reports under `progress/`.
5. Run `./init.sh` before accepting a feature as complete.

The runtime may use subagents, separate conversations, queued jobs, or one
agent executing the roles in sequence. The file protocol remains unchanged.

For every role, load its persisted assignment from the active task envelope
and apply the recorded model and reasoning effort when the runtime supports
them. A different selection is permitted only as a justified recorded override;
the report must name the actual model and reasoning effort used.
