# Transactional jobs and notifications

CRM-017 uses a database-backed transactional outbox. A task reminder is
created by `schedule_task_reminder()` in the same transaction as the task. A
rollback therefore removes the task and its reminder together. Completion and
cancellation cancel pending, leased, or retrying reminders; rescheduling
cancels the old idempotency key and creates a replacement.

Each job stores a type, a stable idempotency key, a scheduled timestamp,
bounded attempts, state, lease, safe last error, and a provider idempotency
key. `payload_reference` is deliberately limited to stable identifiers such as
`task_id` and `lead_id`; it is not a message body, note, credential, or export
content.

The deployable worker adapter is `simple_crm.platform.jobs.run_worker_once()`.
An external process may invoke it repeatedly with a bounded limit. Claims use
database row locks and PostgreSQL skip-locked polling when supported. A worker
crash leaves a lease; the next poll returns an expired claim to a bounded
retry schedule or marks it dead after the configured attempt limit. Delivery
receipts use the same provider key, so a retry does not create a second
internal delivery receipt after a send has already been recorded.

Notification preferences belong to an identity. Daily digest is enabled by
default, while escalation is restricted to identities with administrative
elevation permission. Sellers can change their own digest flag and local hour
at `/configuracion/notificaciones/`. Authorized operators see only job type,
state, attempts, schedule, safe error, and reference field names; payload
values and provider credentials are never rendered.

The MVP intentionally does not send external email/SMS and does not add
Redis, RabbitMQ, Celery, marketing campaigns, or arbitrary broker semantics.
