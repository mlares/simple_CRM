# Provider adapters

The harness contract is provider-neutral. Add a small adapter here when a
runtime needs a special entry point or invocation convention.

An adapter should:

- point to `AGENTS.md` as the source of truth;
- map provider concepts to the roles in `agents/roles/`;
- preserve the feature and progress file paths;
- explain how the provider starts or sequences roles;
- avoid copying the full workflow contract.

Existing adapters:

- `codex.md` — Codex-style repository instructions;
- `generic.md` — runtimes with no standard instruction filename.
