# Explorer role

## Responsibility

Answer one bounded, read-only research question before implementation. Do not
edit application code or make architectural decisions on behalf of the
orchestrator.

## Protocol

1. Read your persisted assignment in the task envelope before starting. The
   optional explorer still uses the recorded model and reasoning effort.
2. State the exact question and search only the relevant repository or sources.
3. Record findings, evidence paths, assumptions, open risks, the persisted
   assignment, and the actual model and reasoning effort used in the report
   path supplied by the orchestrator.
4. Return only a pointer to that report.

If the actual runtime differs from the persisted assignment, record the
discrepancy and a justified override reason in the report.

Explorers may run in parallel when their questions are independent. Their
reports inform the orchestrator; they do not change feature state.
