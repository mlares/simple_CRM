# Validation report — CRM-020

## Verdict

`CHANGES_REQUESTED`

## Independence, assignment, and scope

- Validation date: `2026-08-13`.
- Validator: `crm020_operations_validator_sol`.
- Implementer: `crm020_operations_implementer_terra`; the agent ID and model
  lane are independent from the validator.
- Persisted validator assignment: `gpt-5.6-sol`, reasoning effort `high`,
  source `role_default`.
- Actual validator runtime: `gpt-5.6-sol`, reasoning effort `high`; no
  assignment discrepancy.
- Runtime/session ID: `CODEX_THREAD_ID=019ffb37-c820-73e2-a088-907e0b11afdc`.
- Implementer runtime recorded in the implementation report:
  `gpt-5.6-terra`, reasoning effort `high`.
- Baseline inspected: `HEAD fcbe3b4ea14e155084019f9248a909826397d188`
  plus the preserved completed-feature worktree identified by the task
  envelope.
- Allowed validator write target:
  `crm/progress/validation_CRM-020.md` only.
- Inspected the task envelope, implementation and prior validation reports,
  CRM-020 requirements and criteria, harness checkpoints, relevant
  architecture/conventions/verification/operations contracts, runbooks,
  current worktree status, actual image/runtime/observability/worker/restore
  implementation, and executable tests. Most implementation files are
  untracked relative to the recorded baseline, so validation used their actual
  contents and runtime behavior rather than relying on the tracked diff alone.

## Requirement mapping

| Requirement ID | Evidence inspected | Result | Finding |
| --- | --- | --- | --- |
| CRM-020-R01 | Digest-pinned multi-stage `Dockerfile`; Gunicorn web and bounded worker entrypoints; image metadata; live non-root image smoke. | PASS | Local image ID `sha256:774334d7f5a70ea289eb3d645cf6f1a41fe9d551bac198dca5f061224ec6ed72` runs as `10001:10001`, defaults to `/app/docker/entrypoint.sh web`, and contains the separate `worker` path. |
| CRM-020-R02 | Separate settings modules, fail-closed deployed settings, deployment/migration/rollback runbook, production image smoke, and evidence search. | FAIL | Repository configuration and procedures exist, but no controlled staging promotion or migration/rollback rehearsal record was supplied. |
| CRM-020-R03 | JSON formatter and middleware, query timing, aggregate metrics, instrumentation call sites, per-job context, failed-job tests, and evidence search. | FAIL | Local structured correlation and redaction controls pass. No operator observability walkthrough record proves deployed ingestion and end-to-end tracing. |
| CRM-020-R04 | `ops/observability.yaml`, protected aggregate metrics endpoint, operations verifier, and evidence search. | PASS | Required SLI and alert definitions are versioned. Controlled alert execution is separately unproved under CRM-020-AC05. |
| CRM-020-R05 | Backup/PITR and retention runbooks, exact-name-gated restore adapter, fail-closed invocation, and evidence search. | FAIL | No managed backup/PITR record, encrypted recovery-artifact record, signed isolated restore, measured RPO, or measured RTO was supplied. |
| CRM-020-R06 | `ops/runbooks.md` and `crm/docs/operations.md`. | PASS | Deployment, rollback, migration, incident, restore, credential-rotation, and worker-recovery procedures are present. |

## Acceptance mapping

| Acceptance ID | Evidence inspected | Result | Finding or required evidence |
| --- | --- | --- | --- |
| CRM-020-AC01 | Current image build/smoke and image inspection; repository-wide evidence search. | FAIL | The local image is versioned, non-root, externally configured, and uses Gunicorn. No genuine record shows this same image digest staged and then promoted to production. |
| CRM-020-AC02 | Production rendered-page/static/control-path smoke; deploy, preflight, migration, readiness, and rollback procedures; evidence search. | FAIL | The repository-side deployment path now works, but the required staging deployment rehearsal is absent. |
| CRM-020-AC03 | Request correlation tests; per-job opaque correlation/reference implementation; failed-job formatter/redaction test; repository-wide evidence search. | FAIL | Tests prove stable bounded job correlation, an opaque job reference, and exclusion of the job ID, idempotency key, and exception payload. No deployed observability walkthrough demonstrates that an operator can follow a failed request or job through the actual logging/trace system. |
| CRM-020-AC04 | Restore adapter source and contract test; unconfigured fail-closed execution; runbook; evidence search. | FAIL | No authorized disposable managed-backup/PITR input was supplied, so no restore was attempted. There is no signed isolated restore record proving login, row counts, lineage, a representative report, approved RPO/RTO, or encrypted artifacts. |
| CRM-020-AC05 | Versioned alert definitions, operations verifier, runbook, and evidence search. | FAIL | No controlled alert test record shows fire and recovery for web failure, database unavailability, stale backup, and excessive job backlog. |

The explicit evidence types named by the acceptance criteria are mandatory
gates. Provider-neutral source code, local tests, and runbook text cannot stand
in for staging, production, managed-backup, monitoring, or signed operational
records.

## Bounded revision verification

- `PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest -q tests/config/test_observability.py tests/platform/test_observability_requests.py tests/platform/test_pages_and_health.py tests/platform/test_jobs.py tests/integration/test_verify_operations_script.py tests/integration/test_verify_production_image_script.py tests/integration/test_restore_drill_script.py`
  — exit 0; `24 passed, 7 warnings`. The warnings are local WhiteNoise
  missing-directory warnings under non-image test settings. The suite includes
  stable opaque per-job correlation/reference, failed-job redaction, rendered
  home page, dependency-safe health checks, and verifier contracts.
- `bash scripts/verify-operations.sh` — exit 0; `Operations artifact
  verification passed`.
- `bash scripts/verify-production-image.sh` — the first sandboxed attempt could
  not access `/var/run/docker.sock`; the authorized local-daemon rerun exited
  0. It built the current image, served `/health/live/`, rendered `/`, extracted
  a manifest-hashed Bootstrap path, fetched that asset successfully, confirmed
  `/app/staticfiles/staticfiles.json`, confirmed that UID/GID 10001 can write
  `/tmp/simplecrm-runtime`, and confirmed the live
  `/tmp/simplecrm-runtime/gunicorn.ctl` socket. The initial readiness polling
  observed one transient connection reset while Gunicorn started, then the
  bounded retry and all assertions passed. The uniquely named smoke container
  was removed by the script trap.
- `docker image inspect simple-crm:production-smoke --format ...` — exit 0;
  image ID
  `sha256:774334d7f5a70ea289eb3d645cf6f1a41fe9d551bac198dca5f061224ec6ed72`,
  user `10001:10001`, entrypoint `/app/docker/entrypoint.sh`, command `web`,
  `DJANGO_STATIC_ROOT=/app/staticfiles`, and
  `XDG_RUNTIME_DIR=/tmp/simplecrm-runtime`.
- `timeout 120s ./crm/init.sh` — exit 0; harness metadata, Ruff, formatting,
  djLint, mypy, all tests, Django checks, migration drift, repository safety,
  and vendored assets passed; `229 passed, 28 warnings`.
- `bash scripts/restore-drill.sh` without explicit opt-in — expected fail-closed
  exit 2 with `SIMPLE_CRM_RESTORE_DRILL must equal 1`. Running an actual drill
  was neither safe nor evidentiary without authorized exact-name disposable
  databases and a genuine managed backup/PITR artifact.
- `git diff --check` — exit 0 with no output. Because CRM-020 files are largely
  untracked against the baseline, this command does not replace direct source
  inspection and runtime verification.
- Final worktree inspection showed the preserved pre-existing dirty worktree;
  validation runs introduced no intentional application, task/state,
  documentation, or implementation-file changes.

## Findings

- Bounded fixes: the prior static-root mismatch, production landing-page/static
  failure, non-root Gunicorn control-path failure, and untraceable failed-job
  event are resolved by current runtime and test evidence.
- External blockers: supply a staging and production promotion record for one
  image digest, a staging deployment rehearsal, an observability walkthrough,
  a signed managed-backup/PITR isolated restore record with encrypted artifacts
  and measured approved RPO/RTO, and alert fire/recovery records for all four
  required scenarios. None was found or inferred.
- Security: image execution is non-root; deployment secrets remain external;
  metrics are token-protected; logs use allow-listed fields; request IDs are
  bounded; failed-job events expose opaque hashes rather than job IDs,
  idempotency keys, payloads, or exception arguments; restore execution fails
  closed and is exact-name-gated.
- Architecture and scope: the provider-neutral image, settings,
  observability, outbox worker, and restore adapter follow the documented
  modular-monolith operations boundary. No unrelated work is attributed to
  CRM-020 merely because the baseline worktree is extensively dirty.
- Regression: the targeted suite and full harness pass. Local test settings
  still warn that the repository-level `staticfiles/` directory is absent;
  the production image uses and successfully serves its collected
  `/app/staticfiles` manifest.
- Documentation consistency: `crm/docs/verification.md` still describes the
  static-root and Gunicorn warnings as unresolved and reports the older
  224-test result, while the current implementation and image smoke resolve
  them and the harness has 229 tests. `README.md` also retains the older test
  count. This does not substitute for or remove any external evidence gate.
