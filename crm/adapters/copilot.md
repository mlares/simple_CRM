# GitHub Copilot adapter

Use `AGENTS.md` as the canonical project contract. If this project is used
with GitHub Copilot repository instructions, expose the same short pointer from
`.github/copilot-instructions.md` or configure the host to load `AGENTS.md`.

Map planning, implementation, and validation prompts to the `orchestrator`,
`implementer`, and `validator` role files. Keep reports and feature state in
the paths defined by the canonical contract.

Resolve the persisted assignment in the active task envelope before starting a
role. Configure the available runtime with the recorded model and reasoning
effort, allow only a justified recorded override, and include the actual model
and reasoning effort used in each report.
