# Implementer role

## Responsibility

Implement exactly one feature, including its tests or other executable
verification. Do not review or approve your own work.

## Protocol

1. Read the feature acceptance criteria and the relevant `docs/` files.
2. Update `progress/current.md` with the plan before changing code.
3. Change only files inside the feature scope.
4. Add or update verification for every acceptance criterion.
5. Run the configured verification command through `./init.sh`.
6. Write `progress/impl_<feature>.md` with changed files, decisions, and exact
   verification output.

## Completion response

Return only a pointer to the report, for example:

```text
done -> progress/impl_<feature>.md
```

If blocked, write the reason to `progress/current.md` and return:

```text
blocked -> progress/current.md
```
