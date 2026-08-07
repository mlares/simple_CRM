# Role system

The role files under `agents/roles/` are provider-neutral operating
specifications. They describe responsibilities, inputs, outputs, and handoff
rules without assuming a particular agent API.

A provider adapter should map its own concepts to these roles. For example, an
adapter may map a spawned worker, a separate conversation, or a subprocess to
the `implementer` role. The adapter must preserve the report paths and state
transitions.

Recommended execution order:

```text
leader -> explorer(s) [optional] -> implementer -> reviewer
                                      ^             |
                                      |-- changes --|
```

Parallel explorers are appropriate only for independent read-only questions.
There should be one implementation owner for a feature and one independent
reviewer.
