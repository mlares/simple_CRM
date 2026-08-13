"""Typed filters and saved-view lifecycle for scoped lead reporting."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Mapping

from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, QuerySet
from django.utils import timezone

from simple_crm.activity.models import InteractionResult
from simple_crm.crm.lead_services import visible_leads
from simple_crm.crm.models import Lead
from simple_crm.identity.models import IdentityProfile

from .models import SavedView, SavedViewVisibility

MAX_AND_CONDITIONS = 8
MAX_OR_GROUPS = 3
MAX_OR_CONDITIONS = 4
MAX_PAGE_SIZE = 50
MAX_CURSOR = 10_000

SORT_OPTIONS: dict[str, tuple[str, ...]] = {
    "created_desc": ("-created_at", "-pk"),
    "created_asc": ("created_at", "pk"),
    "lead_number": ("lead_number", "pk"),
    "next_action": ("next_task_due_at", "pk"),
    "stage": ("current_stage__sort_order", "lead_number", "pk"),
}
SORT_LABELS = {
    "created_desc": "Más nuevos primero",
    "created_asc": "Más antiguos primero",
    "lead_number": "Número de lead",
    "next_action": "Próximo paso",
    "stage": "Etapa y número de lead",
}
FIELD_LABELS = {
    "stage": "etapa",
    "owner": "responsable",
    "campaign": "campaña",
    "readiness": "preparación de datos",
    "source": "origen",
    "age_days": "antigüedad",
    "staleness_days": "inactividad",
    "province": "provincia",
    "specialty": "especialidad",
    "contactability": "contactabilidad",
    "activity": "actividad",
    "response": "respuesta",
    "task": "tarea",
}
ALLOWED_OPERATORS = {
    "stage": {"eq", "in"},
    "owner": {"eq", "in"},
    "campaign": {"eq", "in"},
    "readiness": {"eq", "in"},
    "source": {"eq"},
    "age_days": {"gte", "lte"},
    "staleness_days": {"gte", "lte"},
    "province": {"eq", "in"},
    "specialty": {"eq", "in"},
    "contactability": {"eq"},
    "activity": {"eq"},
    "response": {"eq"},
    "task": {"eq"},
}


@dataclass(frozen=True)
class FilterCondition:
    field: str
    operator: str
    value: Any


@dataclass(frozen=True)
class SegmentPage:
    definition: dict[str, Any]
    results: tuple[Lead, ...]
    total: int
    next_cursor: int | None
    summary: str
    sort_label: str


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool):
        raise ValidationError(f"El valor de {label} no es válido.")
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"El valor de {label} no es válido.") from exc
    if parsed < 0 or parsed > 3650:
        raise ValidationError(f"El valor de {label} está fuera de rango.")
    return parsed


def _string(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 120:
        raise ValidationError(f"El valor de {label} no es válido.")
    return value.strip()


def _values(value: Any, label: str) -> tuple[Any, ...]:
    if not isinstance(value, list) or not value or len(value) > 20:
        raise ValidationError(f"La lista de {label} no es válida.")
    return tuple(value)


def _validate_condition(raw: Any) -> FilterCondition:
    if not isinstance(raw, dict) or set(raw) != {"field", "operator", "value"}:
        raise ValidationError("El filtro tiene una estructura no permitida.")
    field = raw["field"]
    operator = raw["operator"]
    if field not in ALLOWED_OPERATORS or operator not in ALLOWED_OPERATORS[field]:
        raise ValidationError("El campo u operador de filtro no está permitido.")
    value: Any = raw["value"]
    if operator == "in":
        value = _values(value, FIELD_LABELS[field])
    elif field in {"age_days", "staleness_days"}:
        value = _positive_int(value, FIELD_LABELS[field])
    elif field == "owner":
        values = value if operator == "in" else [value]
        parsed = tuple(_positive_int(item, FIELD_LABELS[field]) for item in values)
        value = parsed if operator == "in" else parsed[0]
    elif field in {
        "stage",
        "campaign",
        "readiness",
        "province",
        "specialty",
        "source",
        "task",
        "contactability",
        "activity",
        "response",
    }:
        if operator == "in":
            value = tuple(_string(item, FIELD_LABELS[field]) for item in value)
        else:
            value = _string(value, FIELD_LABELS[field])
    return FilterCondition(field, operator, value)


def validate_definition(definition: Mapping[str, Any]) -> dict[str, Any]:
    """Validate and normalize the public structured filter contract."""

    if not isinstance(definition, Mapping) or set(definition) - {"and", "or", "sort"}:
        raise ValidationError("La definición de vista no está permitida.")
    raw_and = definition.get("and", [])
    if not isinstance(raw_and, list) or len(raw_and) > MAX_AND_CONDITIONS:
        raise ValidationError("La vista supera el máximo de filtros AND.")
    and_conditions = [_validate_condition(item) for item in raw_and]
    raw_or = definition.get("or", [])
    if not isinstance(raw_or, list) or len(raw_or) > MAX_OR_GROUPS:
        raise ValidationError("La vista supera el máximo de grupos OR.")
    or_groups: list[list[FilterCondition]] = []
    for raw_group in raw_or:
        if (
            not isinstance(raw_group, list)
            or not raw_group
            or len(raw_group) > MAX_OR_CONDITIONS
        ):
            raise ValidationError("El grupo OR no es válido.")
        or_groups.append([_validate_condition(item) for item in raw_group])
    sort = definition.get("sort", "created_desc")
    if sort not in SORT_OPTIONS:
        raise ValidationError("El orden de la vista no está permitido.")
    return {
        "and": [condition.__dict__ for condition in and_conditions],
        "or": [[condition.__dict__ for condition in group] for group in or_groups],
        "sort": sort,
    }


def _condition_q(condition: FilterCondition, now: Any) -> Q:
    field, operator, value = condition.field, condition.operator, condition.value
    if field == "stage":
        path = "current_stage__code"
    elif field == "owner":
        path = "assignments__identity_id"
    elif field == "campaign":
        path = "campaign__code"
    elif field == "readiness":
        path = "data_readiness"
    elif field == "source":
        path = "source_attribution__source"
    elif field == "province":
        path = "party_links__party__addresses__province__code"
    elif field == "specialty":
        path = "party_links__party__specialties__specialty__code"
    elif field == "task":
        path = "tasks__status"
    elif field == "age_days":
        cutoff = now - timedelta(days=int(value))
        return (
            Q(created_at__lte=cutoff)
            if operator == "gte"
            else Q(created_at__gte=cutoff)
        )
    elif field == "staleness_days":
        cutoff = now - timedelta(days=int(value))
        return (
            Q(updated_at__lte=cutoff)
            if operator == "gte"
            else Q(updated_at__gte=cutoff)
        )
    elif field == "contactability":
        if value == "CONTACTABLE":
            return Q(
                party_links__party__contact_point_links__contact_point__quality_state="VALID"
            )
        if value == "NO_CONTACT":
            return ~Q(
                party_links__party__contact_point_links__contact_point__quality_state="VALID"
            )
        raise ValidationError("La contactabilidad no está permitida.")
    elif field == "activity":
        return Q(interactions__isnull=value != "ANY")
    elif field == "response":
        return (
            Q(interactions__result=InteractionResult.RESPONSE)
            if value == "YES"
            else ~Q(interactions__result=InteractionResult.RESPONSE)
        )
    else:
        raise ValidationError("El campo de filtro no está permitido.")
    if operator == "eq":
        if field == "owner":
            return Q(**{f"{path}": value, "assignments__unassigned_at__isnull": True})
        return Q(**{path: value})
    return Q(**{f"{path}__in": value})


def _conditions(definition: Mapping[str, Any], now: Any) -> Q:
    result = Q()
    for raw in definition.get("and", []):
        result &= _condition_q(_validate_condition(raw), now)
    for group in definition.get("or", []):
        group_query = Q()
        for raw in group:
            group_query |= _condition_q(_validate_condition(raw), now)
        result &= group_query
    return result


def _summary(definition: Mapping[str, Any]) -> str:
    labels: list[str] = []
    for raw in definition.get("and", []):
        condition = _validate_condition(raw)
        labels.append(f"{FIELD_LABELS[condition.field]}: {condition.value}")
    for group in definition.get("or", []):
        labels.append(
            " o ".join(
                f"{FIELD_LABELS[_validate_condition(raw).field]}: {_validate_condition(raw).value}"
                for raw in group
            )
        )
    return ", ".join(labels) if labels else "Todos los leads visibles"


def execute_definition(
    *,
    actor: IdentityProfile,
    definition: Mapping[str, Any],
    cursor: int = 0,
    page_size: int = 20,
) -> SegmentPage:
    normalized = validate_definition(definition)
    if page_size < 1 or page_size > MAX_PAGE_SIZE or cursor < 0 or cursor > MAX_CURSOR:
        raise ValidationError("La paginación no es válida.")
    sort = str(normalized["sort"])
    queryset = (
        visible_leads(actor).filter(_conditions(normalized, timezone.now())).distinct()
    )
    queryset = queryset.order_by(*SORT_OPTIONS[sort])
    total = queryset.count()
    page = tuple(
        queryset.select_related("campaign", "current_stage")[
            cursor : cursor + page_size
        ]
    )
    next_cursor = cursor + page_size if cursor + page_size < total else None
    return SegmentPage(
        normalized, page, total, next_cursor, _summary(normalized), SORT_LABELS[sort]
    )


def _is_manager(actor: IdentityProfile) -> bool:
    return (
        actor.is_enabled
        and actor.role_assignments.filter(
            role__code__in=("sales_manager", "system_administrator"),
            role__is_active=True,
        ).exists()
    )


def _require_saved_view_access(actor: IdentityProfile, view: SavedView) -> None:
    if not actor.is_enabled or view.is_archived:
        raise PermissionDenied("La vista no está disponible.")
    if view.owner_id != actor.pk and not (
        view.visibility == SavedViewVisibility.SHARED and view.approved_by_id
    ):
        raise PermissionDenied("No tiene autorización para esta vista.")


def list_saved_views(actor: IdentityProfile) -> QuerySet[SavedView]:
    if not actor.is_enabled:
        return SavedView.objects.none()
    return SavedView.objects.filter(is_archived=False).filter(
        Q(owner=actor)
        | Q(visibility=SavedViewVisibility.SHARED, approved_by__isnull=False)
    )


def create_saved_view(
    *,
    actor: IdentityProfile,
    name: str,
    definition: Mapping[str, Any],
    shared: bool = False,
) -> SavedView:
    normalized = validate_definition(definition)
    if not actor.is_enabled:
        raise PermissionDenied("La identidad no está habilitada.")
    if shared and not _is_manager(actor):
        raise PermissionDenied("Sólo un gerente puede aprobar vistas compartidas.")
    return SavedView.objects.create(
        owner=actor,
        name=name.strip(),
        definition=normalized,
        visibility=SavedViewVisibility.SHARED
        if shared
        else SavedViewVisibility.PRIVATE,
        approved_by=actor.user if shared else None,
    )


def get_saved_view(*, actor: IdentityProfile, view_id: int) -> SavedView:
    try:
        view = SavedView.objects.get(pk=view_id)
    except SavedView.DoesNotExist as exc:
        raise PermissionDenied("La vista no está disponible.") from exc
    _require_saved_view_access(actor, view)
    return view


def execute_saved_view(
    *, actor: IdentityProfile, view_id: int, cursor: int = 0, page_size: int = 20
) -> SegmentPage:
    view = get_saved_view(actor=actor, view_id=view_id)
    return execute_definition(
        actor=actor, definition=view.definition, cursor=cursor, page_size=page_size
    )


def rename_saved_view(
    *,
    actor: IdentityProfile,
    view_id: int,
    name: str,
    expected_version: int | None = None,
) -> SavedView:
    view = get_saved_view(actor=actor, view_id=view_id)
    if view.owner_id != actor.pk and not _is_manager(actor):
        raise PermissionDenied(
            "Sólo el propietario o un gerente puede renombrar la vista."
        )
    if expected_version is not None and view.version != expected_version:
        raise ValidationError("La vista cambió; recárguela antes de renombrarla.")
    view.name = name.strip()
    view.save(update_fields=("name",))
    return view


def copy_saved_view(*, actor: IdentityProfile, view_id: int, name: str) -> SavedView:
    source = get_saved_view(actor=actor, view_id=view_id)
    return create_saved_view(actor=actor, name=name, definition=source.definition)


def archive_saved_view(*, actor: IdentityProfile, view_id: int) -> SavedView:
    view = get_saved_view(actor=actor, view_id=view_id)
    if view.owner_id != actor.pk and not _is_manager(actor):
        raise PermissionDenied(
            "Sólo el propietario o un gerente puede archivar la vista."
        )
    view.is_archived = True
    view.save(update_fields=("is_archived",))
    return view
