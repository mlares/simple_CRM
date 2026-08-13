# Current session

- Feature: CRM-020 — Deployment, observability, backups, and recovery
- Status: changes_requested
- Owner: crm020_operations_orchestrator_sol
- Started: 2026-08-13

## Plan

The bounded repository revision is complete. The orchestrator transitioned
CRM-020 from `in_progress` to `review` for independent validation, then to
`changes_requested` after the validator confirmed the code defects were fixed
but mandatory deployment-owned acceptance evidence was absent.

## Log

Dependencies CRM-002, CRM-003, CRM-017, and CRM-019 are done. The task envelope
remains bounded to deployment artifacts, operational documentation,
observability instrumentation, and opt-in disposable recovery evidence; no
cloud provider or production credential is selected.

Implementer `crm020_operations_implementer_terra` completed the bounded
revision as the persisted `gpt-5.6-terra/high` assignment and updated
`progress/impl_CRM-020.md`. Independent validator
`crm020_operations_validator_sol` ran as the persisted
`gpt-5.6-sol/high` assignment in runtime thread
`019ffb37-c820-73e2-a088-907e0b11afdc` and persisted
`progress/validation_CRM-020.md` with `CHANGES_REQUESTED`. This closing
orchestration runs as the persisted `gpt-5.6-sol/high` assignment in runtime
thread `019ffb3c-84c5-7c51-aadc-7042426008bb`; there is no assignment
discrepancy.

Repository evidence is green: the full harness passed with 229 tests, the
focused revision suite passed with 24 tests, and both the operations and
production-image verifiers passed. The previous production static-root,
rendered/static HTTP, non-root Gunicorn control-path, and failed-job correlation
defects are resolved. The local full suite still emits non-fatal WhiteNoise
warnings for an absent repository-level `staticfiles/` directory; the verified
production image serves its collected `/app/staticfiles` manifest.

The exact external blockers are:

- a staging and production promotion record for the same image digest;
- a controlled staging deployment, migration, readiness, and rollback
  rehearsal record;
- a deployed observability walkthrough tracing a failed request or job by
  correlation ID without exposing personal data;
- a signed isolated managed-backup/PITR restore record proving encrypted
  recovery artifacts, backup freshness, login, row counts, lineage, a
  representative report, and measured approved RPO/RTO; and
- controlled alert fire-and-recovery records for web failure, database
  unavailability, stale backup, and excessive job backlog.

CRM-021 remains `pending`: it depends on CRM-020, and no source workbook is
present. It has not been started.

## Next step

Obtain the mandatory external records above. Only then resume CRM-020 through
the legal `changes_requested -> in_progress -> review` sequence for independent
validation. Do not mark CRM-020 done or start CRM-021 without approved evidence.
