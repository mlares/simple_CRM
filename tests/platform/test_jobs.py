import json
from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from simple_crm.activity.models import Task, TaskStatus
from simple_crm.activity.services import (
    NextTaskSpec,
    cancel_task,
    complete_task,
    quick_contact,
    reschedule_task,
)
from simple_crm.config.observability import (
    JsonLogFormatter,
    job_correlation_id,
    safe_job_reference,
)
from simple_crm.crm.lead_services import create_lead
from simple_crm.crm.models import Campaign, LeadPartyRole
from simple_crm.crm.services import create_organization_party
from simple_crm.identity.models import (
    IdentityProfile,
    Role,
    RoleAssignment,
    ScopeGrant,
    ScopeType,
)
from simple_crm.platform.jobs import (
    claim_jobs,
    get_notification_preferences,
    operator_jobs,
    recover_expired_leases,
    run_worker_once,
    schedule_task_reminder,
    update_notification_preferences,
)
from simple_crm.platform.models import (
    JobState,
    JobType,
    NotificationDelivery,
    OutboxJob,
)


def _profile(username: str, role_code: str = "sales_representative") -> IdentityProfile:
    user = get_user_model().objects.create_user(username=username, password="safe-pass")
    profile = IdentityProfile.objects.get(user=user)
    RoleAssignment.objects.create(
        identity=profile, role=Role.objects.get(code=role_code)
    )
    return profile


def _lead(actor: IdentityProfile):
    campaign = Campaign.objects.get(code="GENERAL")
    ScopeGrant.objects.create(
        identity=actor, scope_type=ScopeType.CAMPAIGN, campaign=campaign
    )
    party, _ = create_organization_party(display_name="Hospital de trabajos")
    lead, _ = create_lead(
        actor=actor,
        campaign=campaign,
        owner=actor,
        parties=((party, LeadPartyRole.ACCOUNT),),
    )
    return lead


def _task(actor: IdentityProfile, *, due_date: date | None = None) -> Task:
    return Task.objects.create(
        lead=_lead(actor),
        owner=actor,
        description="Enviar seguimiento",
        due_date=due_date or date.today(),
    )


@pytest.mark.django_db
def test_reminder_idempotency_and_worker_delivery_receipt() -> None:
    actor = _profile("jobs-idempotent")
    task = _task(actor)
    first = schedule_task_reminder(task)
    second = schedule_task_reminder(task)

    assert first is not None and second is not None
    assert OutboxJob.objects.filter(idempotency_key=first.idempotency_key).count() == 1
    assert OutboxJob.objects.count() == 1

    results = run_worker_once(now=timezone.now() + timedelta(days=1))
    assert results[0].state == JobState.SUCCEEDED
    assert NotificationDelivery.objects.filter(job=first).count() == 1
    assert run_worker_once(now=timezone.now() + timedelta(days=1)) == []


@pytest.mark.django_db
def test_claim_lease_recovery_retry_and_dead_letter_are_bounded() -> None:
    actor = _profile("jobs-recovery")
    task = _task(actor)
    job = schedule_task_reminder(task)
    assert job is not None
    now = timezone.now() + timedelta(days=1)
    claimed = claim_jobs(now=now, limit=1, lease_seconds=1)
    assert [item.pk for item in claimed] == [job.pk]
    recovered = recover_expired_leases(now=now + timedelta(seconds=2))
    assert recovered == 1
    job.refresh_from_db()
    assert job.state == JobState.FAILED
    assert job.last_error == "La reserva expiró; se programó un reintento."

    job.scheduled_at = now - timedelta(seconds=1)
    job.max_attempts = job.attempts + 1
    job.save(update_fields=("scheduled_at", "max_attempts", "updated_at"))
    claim_jobs(now=now, limit=1, lease_seconds=1)
    recover_expired_leases(now=now + timedelta(seconds=2))
    job.refresh_from_db()
    assert job.state == JobState.DEAD


@pytest.mark.django_db
def test_failed_sender_never_persists_exception_payload_and_retries() -> None:
    actor = _profile("jobs-sender")
    job = schedule_task_reminder(_task(actor))
    assert job is not None

    def broken_sender(_job: OutboxJob) -> None:
        raise RuntimeError("secret personal payload must not leak")

    failed = run_worker_once(
        now=timezone.now() + timedelta(days=1), sender=broken_sender
    )[0]
    assert failed.state == JobState.FAILED
    assert "secret" not in failed.last_error.lower()
    assert "personal" not in failed.last_error.lower()
    assert NotificationDelivery.objects.count() == 0


@pytest.mark.django_db
def test_failed_job_logs_share_a_bounded_correlation_and_redact_payload(caplog) -> None:  # type: ignore[no-untyped-def]
    caplog.set_level("INFO", logger="simple_crm.observability")
    actor = _profile("jobs-correlation")
    job = schedule_task_reminder(_task(actor))
    assert job is not None
    expected_correlation = job_correlation_id(
        job_id=job.pk, idempotency_key=job.idempotency_key
    )
    expected_reference = safe_job_reference(
        job_id=job.pk, idempotency_key=job.idempotency_key
    )

    def broken_sender(_job: OutboxJob) -> None:
        raise RuntimeError("secret personal payload must not leak")

    failed = run_worker_once(
        now=timezone.now() + timedelta(days=1), sender=broken_sender
    )[0]
    events = [
        record
        for record in caplog.records
        if getattr(record, "observability_event", "") == "jobs.failed"
    ]

    assert failed.state == JobState.FAILED
    assert len(events) == 1
    payload = json.loads(JsonLogFormatter().format(events[0]))
    assert payload["correlation_id"] == expected_correlation
    assert payload["job_reference"] == expected_reference
    assert "secret personal payload" not in json.dumps(payload)
    assert "job_id" not in payload
    assert job.idempotency_key not in json.dumps(payload)


@pytest.mark.django_db
def test_crash_after_receipt_retries_with_same_provider_key() -> None:
    actor = _profile("jobs-provider-retry")
    job = schedule_task_reminder(_task(actor))
    assert job is not None

    def send_then_crash(current: OutboxJob) -> None:
        NotificationDelivery.objects.create(
            job=current,
            identity=actor,
            provider_idempotency_key=current.provider_idempotency_key,
            metadata={"job_type": current.job_type},
        )
        raise RuntimeError("worker stopped after provider accepted the key")

    failed = run_worker_once(
        now=timezone.now() + timedelta(days=1), sender=send_then_crash
    )[0]
    assert failed.state == JobState.FAILED
    failed.scheduled_at = timezone.now() - timedelta(seconds=1)
    failed.save(update_fields=("scheduled_at", "updated_at"))

    retried = run_worker_once(now=timezone.now() + timedelta(days=1))[0]
    assert retried.state == JobState.SUCCEEDED
    assert NotificationDelivery.objects.filter(job=job).count() == 1


@pytest.mark.django_db
def test_task_lifecycle_replaces_and_cancels_obsolete_reminders() -> None:
    actor = _profile("jobs-lifecycle")
    lead = _lead(actor)
    result = quick_contact(
        actor=actor,
        lead=lead,
        occurrence_date=date.today(),
        direction="OUTBOUND",
        channel_code="EMAIL",
        outcome_code="CONTACTADO",
        result="COMPLETED",
        note="Se acordó seguimiento.",
        next_task=NextTaskSpec(
            description="Preparar propuesta", due_date=date.today() + timedelta(days=1)
        ),
    )
    assert result.task is not None
    assert OutboxJob.objects.filter(state=JobState.PENDING).count() == 1
    completed = complete_task(actor=actor, task=result.task)
    assert completed.status == TaskStatus.COMPLETED
    assert OutboxJob.objects.filter(state=JobState.CANCELLED).count() == 1

    second = Task.objects.create(
        lead=lead,
        owner=actor,
        description="Revisar presupuesto",
        due_date=date.today() + timedelta(days=2),
    )
    original = schedule_task_reminder(second)
    assert original is not None
    rescheduled = reschedule_task(
        actor=actor,
        task=second,
        due_date=date.today() + timedelta(days=3),
        reason="El cliente pidió más tiempo",
    )
    original.refresh_from_db()
    replacement = (
        OutboxJob.objects.filter(
            idempotency_key__startswith=f"reminder:task:{second.pk}:"
        )
        .exclude(pk=original.pk)
        .get()
    )
    assert rescheduled.status == TaskStatus.RESCHEDULED
    assert original.state == JobState.CANCELLED
    assert replacement.state == JobState.PENDING
    cancel_task(actor=actor, task=second, reason="La oportunidad se cerró")
    assert OutboxJob.objects.filter(pk=replacement.pk).get().state == JobState.CANCELLED


@pytest.mark.django_db
def test_preferences_default_to_digest_and_escalation_is_restricted() -> None:
    actor = _profile("jobs-preferences")
    preferences = get_notification_preferences(actor)
    assert preferences.digest_enabled is True
    assert preferences.escalation_enabled is False
    with pytest.raises(PermissionDenied):
        update_notification_preferences(
            actor=actor,
            target=actor,
            digest_enabled=False,
            escalation_enabled=True,
            daily_digest_hour=9,
        )
    updated = update_notification_preferences(
        actor=actor,
        target=actor,
        digest_enabled=False,
        escalation_enabled=False,
        daily_digest_hour=18,
    )
    assert updated.digest_enabled is False
    assert updated.daily_digest_hour == 18


@pytest.mark.django_db
def test_operator_projection_requires_scope_and_redacts_payload_values() -> None:
    actor = _profile("jobs-operator", "privacy_audit_reviewer")
    ScopeGrant.objects.create(identity=actor, scope_type=ScopeType.GLOBAL)
    job = OutboxJob.objects.create(
        job_type=JobType.REMINDER,
        recipient=actor,
        payload_reference={
            "task_id": 7,
            "lead_id": 9,
            "note": "private note",
            "token": "provider-secret",
        },
        idempotency_key="operator-redaction-job",
        scheduled_at=timezone.now(),
        state=JobState.DEAD,
        attempts=5,
    )
    projection = operator_jobs(actor)[0]
    assert projection.job_id == job.pk
    assert projection.reference_fields == ("lead_id", "note", "task_id", "token")
    assert "private note" not in str(projection)
    assert "provider-secret" not in str(projection)
