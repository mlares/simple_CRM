"""Read-only governed metric and dashboard projections."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any

from django.core.exceptions import ValidationError
from django.db.models import Count, Q
from django.db.models.query import QuerySet
from django.utils import timezone

from simple_crm.activity.models import (
    Interaction,
    InteractionDirection,
    InteractionResult,
    Task,
    TaskStatus,
)
from simple_crm.crm.lead_services import visible_leads
from simple_crm.crm.models import Lead, PartyContactPoint
from simple_crm.identity.models import IdentityProfile

from .models import MetricDefinition

DEFAULT_WINDOW_DAYS = 30
STALE_DAYS = 14
PLACEHOLDER_NOTES = ("Sin acción", "Sin accion", "Sin acción.", "Sin accion.")


@dataclass(frozen=True)
class MetricResult:
    code: str
    label: str
    value: float
    numerator: int
    denominator: int
    definition: MetricDefinition


@dataclass(frozen=True)
class ReportRow:
    label: str
    value: int | float


@dataclass(frozen=True)
class ReportSection:
    code: str
    title: str
    rows: tuple[ReportRow, ...]


@dataclass(frozen=True)
class Dashboard:
    start_date: date
    end_date: date
    as_of: Any
    scope_label: str
    freshness_label: str
    result_count: int
    metrics: tuple[MetricResult, ...]
    sections: tuple[ReportSection, ...]


def _window(start_date: date | None, end_date: date | None) -> tuple[date, date]:
    end = end_date or timezone.localdate()
    start = start_date or end - timedelta(days=DEFAULT_WINDOW_DAYS - 1)
    if start > end or (end - start).days > 366:
        raise ValidationError("El período debe ser válido y no superar un año.")
    return start, end


def _definitions() -> dict[str, MetricDefinition]:
    return {
        definition.code: definition
        for definition in MetricDefinition.objects.filter(is_active=True)
    }


def _eligible_interactions(queryset: QuerySet[Interaction]) -> QuerySet[Interaction]:
    placeholders = Q()
    for note in PLACEHOLDER_NOTES:
        placeholders |= Q(note__iexact=note)
    return queryset.exclude(placeholders)


def _metric(
    definitions: dict[str, MetricDefinition],
    code: str,
    numerator: int,
    denominator: int,
    value: float | None = None,
) -> MetricResult:
    definition = definitions[code]
    calculated = (
        value
        if value is not None
        else (numerator / denominator if denominator else 0.0)
    )
    return MetricResult(
        code, definition.label, round(calculated, 4), numerator, denominator, definition
    )


def _stage_age_metrics(leads: list[Lead], end_date: date) -> dict[int, float]:
    age_by_stage: dict[int, list[int]] = {}
    for lead in leads:
        history = lead.stage_history.order_by("-occurred_at", "-pk").first()
        if history is None:
            continue
        age = max(0, (end_date - history.occurred_at.date()).days)
        age_by_stage.setdefault(lead.current_stage_id, []).append(age)
    return {
        stage_id: round(sum(ages) / len(ages), 2)
        for stage_id, ages in age_by_stage.items()
    }


def dashboard(
    *,
    actor: IdentityProfile,
    start_date: date | None = None,
    end_date: date | None = None,
) -> Dashboard:
    """Calculate approved metrics from the caller's visible lead set only."""

    start, end = _window(start_date, end_date)
    definitions = _definitions()
    visible = visible_leads(actor).select_related("campaign", "current_stage")
    leads = list(visible.filter(created_at__date__range=(start, end)))
    lead_ids = [lead.pk for lead in leads]
    all_visible_leads = list(visible)
    all_visible_ids = [lead.pk for lead in all_visible_leads]
    interactions = _eligible_interactions(
        Interaction.objects.filter(
            lead_id__in=lead_ids, occurrence_date__range=(start, end)
        )
    )
    valid_contact_leads = set(
        PartyContactPoint.objects.filter(
            party__lead_links__lead_id__in=lead_ids,
            contact_point__quality_state="VALID",
            contact_point__is_active=True,
            contact_point__is_suppressed=False,
        ).values_list("party__lead_links__lead_id", flat=True)
    )
    contacted_leads = set(
        interactions.filter(
            result__in=(InteractionResult.COMPLETED, InteractionResult.RESPONSE)
        ).values_list("lead_id", flat=True)
    )
    outbound = interactions.filter(direction=InteractionDirection.OUTBOUND).exclude(
        result=InteractionResult.ATTEMPTED
    )
    responses = interactions.filter(
        direction=InteractionDirection.INBOUND, result=InteractionResult.RESPONSE
    )
    stale_cutoff = timezone.make_aware(
        datetime.combine(end - timedelta(days=STALE_DAYS), time.min)
    )
    stale_leads = [lead for lead in all_visible_leads if lead.updated_at < stale_cutoff]
    tasks = Task.objects.filter(lead_id__in=all_visible_ids)
    overdue_tasks = tasks.filter(
        status__in=(TaskStatus.OPEN, TaskStatus.RESCHEDULED), due_date__lt=end
    ).count()
    cohort_closed = sum(lead.current_stage.code == "CERRADO" for lead in leads)
    metrics = (
        _metric(definitions, "CONTACTABLE_LEAD", len(valid_contact_leads), len(leads)),
        _metric(definitions, "CONTACTED_LEAD", len(contacted_leads), len(leads)),
        _metric(definitions, "RESPONSE_RATE", responses.count(), outbound.count()),
        _metric(definitions, "STALE_LEAD", len(stale_leads), len(all_visible_leads)),
        _metric(definitions, "OVERDUE_TASK", overdue_tasks, tasks.count()),
        _metric(definitions, "COHORT_CONVERSION", cohort_closed, len(leads)),
    )
    stage_age = _stage_age_metrics(all_visible_leads, end)
    pipeline = tuple(
        ReportRow(stage.label, sum(lead.current_stage_id == stage.pk for lead in leads))
        for stage in sorted(
            {lead.current_stage for lead in leads}, key=lambda item: item.sort_order
        )
    )
    activity_by_channel = tuple(
        ReportRow(row["channel__label"], row["total"])
        for row in interactions.values("channel__label")
        .annotate(total=Count("pk"))
        .order_by("channel__label")
    )
    source_counts: dict[str, int] = {}
    for lead in leads:
        source = str(lead.source_attribution.get("source", "No informado"))
        source_counts[source] = source_counts.get(source, 0) + 1
    source_rows = tuple(
        ReportRow(label, value) for label, value in sorted(source_counts.items())
    )
    follow_up_gaps = sum(
        not lead.has_next_action
        and not tasks.filter(
            lead_id=lead.pk, status__in=(TaskStatus.OPEN, TaskStatus.RESCHEDULED)
        ).exists()
        for lead in leads
    )
    research_needs = sum(lead.data_readiness == "NEEDS_RESEARCH" for lead in leads)
    stage_rows = tuple(
        ReportRow(stage.label, stage_age.get(stage.pk, 0))
        for stage in sorted(
            {lead.current_stage for lead in all_visible_leads},
            key=lambda item: item.sort_order,
        )
    )
    sections = (
        ReportSection(
            "attention_today",
            "Atención y seguimiento",
            (
                ReportRow("Tareas vencidas", overdue_tasks),
                ReportRow("Brechas de seguimiento", follow_up_gaps),
                ReportRow("Requieren investigación", research_needs),
            ),
        ),
        ReportSection("pipeline", "Distribución de pipeline", pipeline),
        ReportSection("activity", "Actividad de contacto", activity_by_channel),
        ReportSection(
            "response",
            "Respuesta",
            (
                ReportRow("Interacciones salientes elegibles", outbound.count()),
                ReportRow("Respuestas entrantes", responses.count()),
            ),
        ),
        ReportSection("source", "Rendimiento por origen", source_rows),
        ReportSection("stage_age", "Tiempo promedio en etapa (días)", stage_rows),
    )
    return Dashboard(
        start_date=start,
        end_date=end,
        as_of=timezone.now(),
        scope_label="Alcance autorizado actual",
        freshness_label="Calculado en vivo",
        result_count=len(leads),
        metrics=metrics,
        sections=sections,
    )
