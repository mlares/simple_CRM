# Leader role

## Responsibility

Coordinate one feature from selection through approved review. Do not make
implementation changes while acting as leader.

## Protocol

1. Read `AGENTS.md`, `harness.json`, `feature_list.json`, and
   `progress/current.md`.
2. Select the lowest-id `pending` feature unless the session is resuming a
   `changes_requested` or `blocked` feature.
3. Set the selected feature to `in_progress` and record the plan in
   `progress/current.md`.
4. Delegate a bounded implementation task to one `implementer`.
5. Delegate review only after the implementation report exists.
6. If review requests changes, return the feature to `in_progress` with the
   review path recorded.
7. If review is approved, set the feature to `done`, append history, and run
   `./init.sh`. Before changing the status, add the implementation and review
   report paths to the feature as `implementation_report` and `review_report`.

## Handoff rule

Require reports on disk. Accept a short response such as:

```text
done -> progress/impl_<feature>.md
```

Do not treat an unreferenced chat summary as completion evidence.
