# DigPatho Sales Hub operational runbooks

These provider-neutral procedures are the promotion contract. The deployment
platform supplies the image digest, secret facility, managed PostgreSQL,
encrypted object storage, alert routing, and isolated restore environment.
No credential, customer row, or provider-specific endpoint belongs in this
repository.

## Deploy and promote

1. Build the image from the committed `Dockerfile` and `uv.lock`; record the
   content digest in the release record.
2. Scan the image and dependencies, then deploy that same digest to staging
   and production. Supply `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`,
   `DATABASE_URL`, OIDC values, and `OBSERVABILITY_METRICS_TOKEN` externally.
3. Run `docker/entrypoint.sh web` as the non-root `simplecrm` user and run the
   worker command as a separate process type from the same digest.
4. Run `python manage.py check --deploy --fail-level WARNING`, then the
   migration preflight. Apply migrations once with the migration role; web
   processes never run migrations at startup.
5. Verify `/health/live/`, `/health/ready/`, the release correlation header,
   structured event ingestion, and the SLI dashboards before promotion.
   Also confirm that the runtime static directory is configured without a
   WhiteNoise missing-directory warning and that Gunicorn can create its
   control-server path as the non-root runtime user.

## Rollback and migration

Application rollback is a pointer change to the prior approved image digest.
Do not roll back migrations automatically. If a migration is backward
compatible, deploy the prior digest and open a follow-up repair. If it is not,
stop promotion, preserve the incident timeline, and restore into an isolated
database before any destructive action. Migration changes require an explicit
forward-fix or an approved database recovery plan.

## Incident response

1. Page the on-call owner from the SLI alert and record the release digest,
   environment, start time, and correlation ID.
2. Use the correlation ID to find the JSON event; filter on route, status,
   job type, and error type only. Never copy request bodies, notes, workbook
   rows, tokens, SQL parameters, or personal identifiers into the incident.
3. Check readiness, database saturation, job backlog, import/export failure
   rates, and backup freshness. Contain by rolling back the image or pausing
   the worker; preserve audit records.
4. Close only after the alert recovers, the customer-facing state is known,
   and the incident review records a cause and preventive action.

## Restore drill and recovery

Managed PostgreSQL must retain encrypted backups with point-in-time recovery,
at least 35 days of retention, and a 15-minute backup freshness target. Run
`scripts/restore-drill.sh` quarterly against an isolated database named by the
drill, never against staging or production. The drill restores a backup,
checks login/readiness, compares representative row counts and source lineage,
and runs a representative governed report. Record RPO, RTO, backup timestamp,
image digest, operator, and signed approval in the recovery record.

## Credential rotation

Create replacement credentials in the deployment secret facility, deploy them
to staging, run readiness and worker checks, promote, then revoke the previous
credential. Rotate Django, OIDC, database, object-storage, and metrics tokens;
never place values in logs, jobs, exports, shell history, or this repository.

## Worker recovery

Check the outbox backlog and lease age first. Restart the worker from the same
image digest with `docker/entrypoint.sh worker --once` for a bounded probe, then
resume normal polling. Expired leases are recovered by the service; dead-letter
jobs require an operator review and a redacted reason before replay. Do not
manually edit payloads or provider credentials.
