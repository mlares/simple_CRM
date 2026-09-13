# Role system

The role files under `agents/roles/` are provider-neutral operating
specifications. They describe responsibilities, inputs, outputs, and handoff
rules without assuming a particular agent API.

A provider adapter should map its own concepts to these roles. For example, an
adapter may map a spawned worker, a separate conversation, or a subprocess to
the `implementer` role. The adapter must preserve the report paths and state
transitions.

Canonical execution order:

```text
orchestrator -> explorer [optional] -> implementer -> validator -> orchestrator closure
                                                    ^              |
                                                    |-- changes ---|
```

Parallel explorers are appropriate only for independent read-only questions.
There must be one implementation owner for a feature and one independent
validator. The orchestrator is the only role that changes feature state. The
implementer writes its implementation report, and the validator writes only
its validation report.

Every role reads its persisted assignment from the active task envelope before
running. Reports identify the actual model and reasoning effort used and any
justified override from the role defaults in `harness.json`.
