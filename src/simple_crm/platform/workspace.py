"""Scope-aware query and classification helpers for the seller workspace."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from django.core.exceptions import PermissionDenied
from django.db.models import QuerySet
from django.utils import timezone

from simple_crm.activity.models import Interaction, InteractionResult, Task, TaskStatus
from simple_crm.activity.services import TimelineEvent, lead_timeline
from simple_crm.crm.lead_services import visible_leads
from simple_crm.crm.models import Lead, LeadLifecycle
from simple_crm.identity.models import Action, IdentityProfile
from simple_crm.identity.policy import has_action_permission


@dataclass(frozen=True)
class TodayItem:
    category: str
    title: str
    detail: str
    lead: Lead
    rank: int
    due_date: date | None = None
    task: Task | None = None
    interaction: Interaction | None = None


@dataclass(frozen=True)
class TodayWorkspace:
    items: tuple[TodayItem, ...]
    today: date
    shows_unassigned: bool
    empty_message: str


@dataclass(frozen=True)
class LeadDetail:
    lead: Lead
    party_links: tuple[Any, ...]
    owner: Any | None
    tasks: tuple[Task, ...]
    timeline: tuple[TimelineEvent, ...]


def _local_now(now: datetime | None = None) -> datetime:
    current = now or timezone.now()
    return timezone.localtime(current)


def _assigned_lead_ids(queryset: QuerySet[Lead], actor: IdentityProfile) -> set[int]:
    return set(
        queryset.filter(
            assignments__identity=actor,
            assignments__unassigned_at__isnull=True,
        ).values_list("pk", flat=True)
    )


def today_workspace(
    actor: IdentityProfile, *, now: datetime | None = None, only_mine: bool = False
) -> TodayWorkspace:
    """Return fixed-urgency, scope-authorized work for the current seller."""

    current = _local_now(now)
    today = current.date()
    leads = visible_leads(actor).select_related("campaign", "current_stage", "team")
    if only_mine:
        leads = leads.filter(
            assignments__identity=actor,
            assignments__unassigned_at__isnull=True,
        ).distinct()
    lead_ids = list(leads.values_list("pk", flat=True))
    lead_by_id = {lead.pk: lead for lead in leads}
    items: list[TodayItem] = []

    tasks = Task.objects.filter(
        lead_id__in=lead_ids,
        status__in=(TaskStatus.OPEN, TaskStatus.RESCHEDULED),
    ).select_related("lead", "owner__user")
    for task in tasks:
        lead = lead_by_id.get(task.lead_id)
        if lead is None:
            continue
        if task.due_date < today:
            items.append(
                TodayItem(
                    category="overdue",
                    title="Tarea vencida",
                    detail=task.description,
                    lead=lead,
                    rank=0,
                    due_date=task.due_date,
                    task=task,
                )
            )
        elif task.due_date == today:
            items.append(
                TodayItem(
                    category="due_today",
                    title="Tarea para hoy",
                    detail=task.description,
                    lead=lead,
                    rank=1,
                    due_date=task.due_date,
                    task=task,
                )
            )

    response_cutoff = today - timedelta(days=7)
    responses = (
        Interaction.objects.filter(
            lead_id__in=lead_ids,
            result=InteractionResult.RESPONSE,
            occurrence_date__gte=response_cutoff,
        )
        .select_related("lead")
        .order_by("-occurrence_date", "-created_at", "-pk")
    )
    for interaction in responses:
        lead = lead_by_id.get(interaction.lead_id)
        if lead is not None:
            items.append(
                TodayItem(
                    category="response",
                    title="Nueva respuesta",
                    detail=interaction.note or interaction.outcome.label,
                    lead=lead,
                    rank=2,
                    due_date=interaction.occurrence_date,
                    interaction=interaction,
                )
            )

    stale_cutoff = current - timedelta(days=14)
    for lead in lead_by_id.values():
        if lead.current_stage.code == "EN_GESTION" and lead.updated_at < stale_cutoff:
            items.append(
                TodayItem(
                    category="stale",
                    title="Lead sin movimiento reciente",
                    detail="Revisar el próximo paso",
                    lead=lead,
                    rank=3,
                )
            )

    shows_unassigned = has_action_permission(actor, Action.REASSIGN)
    if shows_unassigned:
        for lead in lead_by_id.values():
            if not lead.assignments.filter(unassigned_at__isnull=True).exists():
                items.append(
                    TodayItem(
                        category="unassigned",
                        title="Lead sin responsable",
                        detail="Asignar un responsable",
                        lead=lead,
                        rank=4,
                    )
                )

    items.sort(
        key=lambda item: (
            item.rank,
            item.due_date or date.max,
            -item.lead.created_at.timestamp(),
            item.lead.pk,
        )
    )
    return TodayWorkspace(
        items=tuple(items),
        today=today,
        shows_unassigned=shows_unassigned,
        empty_message=(
            "No hay nada urgente para hoy. Tu seguimiento está al día."
            if not items
            else ""
        ),
    )


def lead_detail(*, actor: IdentityProfile, lead_number: str) -> LeadDetail:
    leads = visible_leads(actor).select_related("campaign", "current_stage", "team")
    lead = leads.filter(lead_number=lead_number, lifecycle=LeadLifecycle.ACTIVE).first()
    if lead is None:
        raise PermissionDenied("No tiene autorización para este lead.")
    party_links = tuple(
        lead.party_links.select_related("party", "party__person", "party__organization")
    )
    owner = (
        lead.assignments.filter(assignment_role="PRIMARY", unassigned_at__isnull=True)
        .select_related("identity__user")
        .first()
    )
    tasks = tuple(
        Task.objects.filter(lead=lead)
        .select_related("owner__user")
        .order_by("due_date", "-created_at")
    )
    return LeadDetail(
        lead=lead,
        party_links=party_links,
        owner=owner,
        tasks=tasks,
        timeline=tuple(lead_timeline(actor=actor, lead=lead)),
    )
