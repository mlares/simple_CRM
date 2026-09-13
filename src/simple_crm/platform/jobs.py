"""Transactional outbox services and the bounded in-process worker adapter."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time, timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import connection, transaction
from django.utils import timezone

from simple_crm.activity.models import Task, TaskStatus
from simple_crm.config.observability import (
    correlation_context,
    job_correlation_id,
    record_event,
    record_metric,
    safe_job_reference,
)
from simple_crm.identity.models import Action, IdentityProfile
from simple_crm.identity.policy import ScopeSpec, can_access, has_action_permission

from .models import (
    JobState,
    JobType,
    NotificationDelivery,
    NotificationPreference,
    OutboxJob,
)

MAX_POLL_LIMIT = 100
MAX_OPERATOR_LIMIT = 100
DEFAULT_LEASE_SECONDS = 60
DEFAULT_MAX_ATTEMPTS = 5


@dataclass(frozen=True)
class JobOperatorView:
    """Redacted projection suitable for an operator screen or audit response."""

    job_id: int
    job_type: str
    state: str
    scheduled_at: datetime
    attempts: int
    max_attempts: int
    last_error: str
    reference_fields: tuple[str, ...]


def _bounded(value: int, *, default: int, maximum: int) -> int:
    if value <= 0:
        return default
    return min(value, maximum)


def _safe_error(error: BaseException) -> str:
    """Return a stable operational message without exception arguments or payloads."""

    name = type(error).__name__
    allowed = {
        "ConnectionError",
        "DatabaseError",
        "TimeoutError",
        "ValidationError",
    }
    return f"Error de entrega ({name if name in allowed else 'Worker'})."


def _reminder_idempotency_key(task: Task) -> str:
    if task.updated_at is None:
        raise ValidationError("La tarea debe estar guardada antes de programar.")
    return f"reminder:task:{task.pk}:{task.updated_at.isoformat()}"


def _task_schedule(task: Task) -> datetime:
    local_midnight = datetime.combine(task.due_date, time.min)
    return timezone.make_aware(local_midnight, timezone.get_current_timezone())


@transaction.atomic
def cancel_task_reminders(task_id: int) -> int:
    """Cancel pending or leased reminders while preserving their audit trail."""

    jobs = OutboxJob.objects.select_for_update().filter(
        job_type=JobType.REMINDER,
        idempotency_key__startswith=f"reminder:task:{task_id}:",
        state__in=(JobState.PENDING, JobState.CLAIMED, JobState.FAILED),
    )
    return jobs.update(
        state=JobState.CANCELLED,
        lease_until=None,
        last_error="Cancelado por cambio de estado de la tarea.",
        updated_at=timezone.now(),
    )


@transaction.atomic
def schedule_task_reminder(task: Task) -> OutboxJob | None:
    """Replace obsolete task reminders inside the caller's transaction."""

    if task.status not in (TaskStatus.OPEN, TaskStatus.RESCHEDULED):
        cancel_task_reminders(task.pk)
        return None

    cancel_task_reminders(task.pk)
    idempotency_key = _reminder_idempotency_key(task)
    job, created = OutboxJob.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            "job_type": JobType.REMINDER,
            "recipient": task.owner,
            "payload_reference": {"task_id": task.pk, "lead_id": task.lead_id},
            "scheduled_at": _task_schedule(task),
            "max_attempts": DEFAULT_MAX_ATTEMPTS,
            "provider_idempotency_key": f"provider:{idempotency_key}"[:220],
        },
    )
    if not created and job.state == JobState.CANCELLED:
        job.state = JobState.PENDING
        job.lease_until = None
        job.last_error = ""
        job.scheduled_at = _task_schedule(task)
        job.save(
            update_fields=(
                "state",
                "lease_until",
                "last_error",
                "scheduled_at",
                "updated_at",
            )
        )
    return job


def _retry_delay(attempts: int) -> timedelta:
    return timedelta(minutes=min(60, 2 ** max(0, attempts - 1)))


@transaction.atomic
def recover_expired_leases(*, now: datetime | None = None) -> int:
    """Return crashed claims to the retry queue or dead-letter them."""

    now = now or timezone.now()
    expired = OutboxJob.objects.select_for_update().filter(
        state=JobState.CLAIMED,
        lease_until__isnull=False,
        lease_until__lte=now,
    )
    recovered = 0
    for job in expired:
        recovered += 1
        if job.attempts >= job.max_attempts:
            job.state = JobState.DEAD
            job.lease_until = None
            job.last_error = "La reserva expiró después del máximo de intentos."
        else:
            job.state = JobState.FAILED
            job.lease_until = None
            job.scheduled_at = now + _retry_delay(job.attempts)
            job.last_error = "La reserva expiró; se programó un reintento."
        job.save(
            update_fields=(
                "state",
                "lease_until",
                "scheduled_at",
                "last_error",
                "updated_at",
            )
        )
    return recovered


@transaction.atomic
def claim_jobs(
    *, now: datetime | None = None, limit: int = 25, lease_seconds: int = 60
) -> list[OutboxJob]:
    """Claim a bounded batch using row locks and skip-locked PostgreSQL polling."""

    now = now or timezone.now()
    limit = _bounded(limit, default=25, maximum=MAX_POLL_LIMIT)
    lease_seconds = _bounded(lease_seconds, default=DEFAULT_LEASE_SECONDS, maximum=3600)
    recover_expired_leases(now=now)
    candidates = OutboxJob.objects.filter(
        state__in=(JobState.PENDING, JobState.FAILED), scheduled_at__lte=now
    ).order_by("scheduled_at", "created_at", "pk")
    if connection.features.has_select_for_update_skip_locked:
        candidates = candidates.select_for_update(skip_locked=True)
    else:
        candidates = candidates.select_for_update()
    claimed: list[OutboxJob] = []
    for job in candidates[:limit]:
        job.state = JobState.CLAIMED
        job.attempts += 1
        job.lease_until = now + timedelta(seconds=lease_seconds)
        job.last_error = ""
        job.save(
            update_fields=(
                "state",
                "attempts",
                "lease_until",
                "last_error",
                "updated_at",
            )
        )
        claimed.append(job)
    return claimed


def _mark_job_failed(job_id: int, error: BaseException) -> OutboxJob:
    with transaction.atomic():
        job = OutboxJob.objects.select_for_update().get(pk=job_id)
        job.lease_until = None
        job.last_error = _safe_error(error)
        job.state = (
            JobState.DEAD if job.attempts >= job.max_attempts else JobState.FAILED
        )
        if job.state == JobState.FAILED:
            job.scheduled_at = timezone.now() + _retry_delay(job.attempts)
        job.save(
            update_fields=(
                "state",
                "lease_until",
                "scheduled_at",
                "last_error",
                "updated_at",
            )
        )
        return job


def _job_reference(job: OutboxJob) -> str:
    return safe_job_reference(job_id=job.pk, idempotency_key=job.idempotency_key)


def _record_job_completed(job: OutboxJob) -> None:
    record_event(
        "jobs.completed",
        component="worker",
        job_type=job.job_type,
        state=job.state,
        attempts=job.attempts,
        job_reference=_job_reference(job),
    )


def process_claimed_job(
    job_id: int,
    *,
    sender: Callable[[OutboxJob], None] | None = None,
) -> OutboxJob:
    """Process one claim with a stable provider key and idempotent receipt."""

    job = OutboxJob.objects.get(pk=job_id)
    if job.state != JobState.CLAIMED:
        return job
    correlation_id = job_correlation_id(
        job_id=job.pk, idempotency_key=job.idempotency_key
    )
    with correlation_context(correlation_id):
        if NotificationDelivery.objects.filter(job=job).exists():
            with transaction.atomic():
                job = OutboxJob.objects.select_for_update().get(pk=job_id)
                job.state = JobState.SUCCEEDED
                job.lease_until = None
                job.last_error = ""
                job.save(
                    update_fields=("state", "lease_until", "last_error", "updated_at")
                )
            _record_job_completed(job)
            return job
        try:
            if sender is not None:
                sender(job)
            with transaction.atomic():
                job = OutboxJob.objects.select_for_update().get(pk=job_id)
                if not NotificationDelivery.objects.filter(job=job).exists():
                    recipient = job.recipient
                    if recipient is None:
                        raise ValidationError("El trabajo no tiene destinatario.")
                    NotificationDelivery.objects.create(
                        job=job,
                        identity=recipient,
                        provider_idempotency_key=job.provider_idempotency_key
                        or f"provider:{job.idempotency_key}"[:220],
                        metadata={"job_type": job.job_type},
                    )
                job.state = JobState.SUCCEEDED
                job.lease_until = None
                job.last_error = ""
                job.save(
                    update_fields=("state", "lease_until", "last_error", "updated_at")
                )
            _record_job_completed(job)
            return job
        except Exception as error:
            failed = _mark_job_failed(job_id, error)
            record_event(
                "jobs.failed",
                component="worker",
                job_type=failed.job_type,
                state=failed.state,
                attempts=failed.attempts,
                error_type=type(error).__name__,
                job_reference=_job_reference(failed),
            )
            return failed


def run_worker_once(
    *,
    now: datetime | None = None,
    limit: int = 25,
    lease_seconds: int = DEFAULT_LEASE_SECONDS,
    sender: Callable[[OutboxJob], None] | None = None,
) -> list[OutboxJob]:
    """Run one bounded poll; deployment can invoke this from a separate process."""

    claims = claim_jobs(now=now, limit=limit, lease_seconds=lease_seconds)
    record_metric("jobs.claimed", len(claims))
    record_event("jobs.poll", component="worker", count=len(claims))
    return [process_claimed_job(job.pk, sender=sender) for job in claims]


def _require_operator(actor: IdentityProfile) -> None:
    if not can_access(actor, Action.AUDIT_VIEW, ScopeSpec.global_scope()):
        raise PermissionDenied("No tiene autorización para revisar trabajos.")


def operator_jobs(
    actor: IdentityProfile, *, limit: int = MAX_OPERATOR_LIMIT
) -> list[JobOperatorView]:
    """Return only operational metadata; payload values and provider keys stay hidden."""

    _require_operator(actor)
    limit = _bounded(limit, default=MAX_OPERATOR_LIMIT, maximum=MAX_OPERATOR_LIMIT)
    jobs = OutboxJob.objects.filter(
        state__in=(JobState.FAILED, JobState.DEAD)
    ).order_by("-updated_at", "-pk")[:limit]
    return [
        JobOperatorView(
            job_id=job.pk,
            job_type=job.job_type,
            state=job.state,
            scheduled_at=job.scheduled_at,
            attempts=job.attempts,
            max_attempts=job.max_attempts,
            last_error=job.last_error,
            reference_fields=tuple(sorted(job.payload_reference.keys())),
        )
        for job in jobs
    ]


def get_notification_preferences(identity: IdentityProfile) -> NotificationPreference:
    preferences, _ = NotificationPreference.objects.get_or_create(identity=identity)
    return preferences


def update_notification_preferences(
    *,
    actor: IdentityProfile,
    target: IdentityProfile,
    digest_enabled: bool,
    escalation_enabled: bool,
    daily_digest_hour: int,
) -> NotificationPreference:
    if actor.pk != target.pk and not has_action_permission(
        actor, Action.ELEVATE_ACCESS
    ):
        raise PermissionDenied("Sólo puede cambiar sus propias preferencias.")
    if escalation_enabled and not has_action_permission(actor, Action.ELEVATE_ACCESS):
        raise PermissionDenied("La escalada requiere autorización administrativa.")
    if not 0 <= daily_digest_hour <= 23:
        raise ValidationError("La hora del resumen debe estar entre 0 y 23.")
    preferences = get_notification_preferences(target)
    preferences.digest_enabled = digest_enabled
    preferences.escalation_enabled = escalation_enabled
    preferences.daily_digest_hour = daily_digest_hour
    preferences.save()
    return preferences
