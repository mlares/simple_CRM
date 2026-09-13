"""Bounded, permission-scoped global search for the seller workspace."""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Iterable

from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import Q, QuerySet

from simple_crm.activity.models import Interaction, Task
from simple_crm.crm.lead_services import visible_leads
from simple_crm.crm.models import (
    ContactKind,
    Lead,
    Party,
    PartyAlias,
)
from simple_crm.crm.normalization import comparison_key, normalize_contact_value
from simple_crm.identity.models import IdentityProfile

MAX_QUERY_LENGTH = 120
MAX_PAGE_SIZE = 50
MAX_CURSOR = 10_000
MAX_FUZZY_CANDIDATES = 2_000
MAX_NOTE_CANDIDATES = 2_000


class SearchInputError(ValidationError):
    """Raised when search input could produce an abusive or ambiguous query."""


@dataclass(frozen=True)
class SearchResult:
    """A safe, permission-checked result suitable for a rendered result card."""

    result_type: str
    object_id: int
    title: str
    subtitle: str
    url: str
    match_reason: str
    score: float
    snippet: str = ""


@dataclass(frozen=True)
class SearchPage:
    """A stable page of search results with an offset cursor."""

    query: str
    results: tuple[SearchResult, ...]
    total: int
    next_cursor: int | None


def _bounded_query(raw_query: str) -> str:
    if not isinstance(raw_query, str):
        raise SearchInputError("La búsqueda no es válida.")
    query = raw_query.strip()
    if len(query) > MAX_QUERY_LENGTH:
        raise SearchInputError(
            f"La búsqueda no puede superar {MAX_QUERY_LENGTH} caracteres."
        )
    wildcard_count = sum(query.count(mark) for mark in ("*", "?", "%", "_"))
    if wildcard_count >= 3:
        raise SearchInputError("La búsqueda contiene demasiados comodines.")
    return query


def _cursor(raw_cursor: int | str | None) -> int:
    if raw_cursor in (None, ""):
        return 0
    try:
        value = int(raw_cursor)
    except (TypeError, ValueError) as exc:
        raise SearchInputError("El cursor de búsqueda no es válido.") from exc
    if value < 0 or value > MAX_CURSOR:
        raise SearchInputError("El cursor de búsqueda está fuera de rango.")
    return value


def _page_size(raw_page_size: int | str) -> int:
    try:
        value = int(raw_page_size)
    except (TypeError, ValueError) as exc:
        raise SearchInputError("El tamaño de página no es válido.") from exc
    if value < 1 or value > MAX_PAGE_SIZE:
        raise SearchInputError(
            f"La página debe tener entre 1 y {MAX_PAGE_SIZE} resultados."
        )
    return value


def _terms(value: str) -> tuple[str, ...]:
    normalized = comparison_key(value)
    return tuple(part for part in normalized.split() if part)


def _excerpt(value: str, normalized_query: str, limit: int = 180) -> str:
    clean = " ".join(value.split())
    if len(clean) <= limit:
        return clean
    needle = normalized_query.casefold()
    position = comparison_key(clean).find(needle) if needle else 0
    start = max(0, position - 50)
    excerpt = clean[start : start + limit]
    return (
        ("…" if start else "") + excerpt + ("…" if start + limit < len(clean) else "")
    )


def _similarity(query: str, value: str) -> float:
    return SequenceMatcher(None, query, comparison_key(value)).ratio()


def _postgres_party_pool(
    queryset: QuerySet[Party], normalized_query: str
) -> QuerySet[Party]:
    """Use PostgreSQL's indexed text/trigram operators when available.

    SQLite remains the deterministic test backend and uses the bounded Python
    fallback below. Importing these expressions only on PostgreSQL keeps the
    local developer harness portable while preserving the production query
    strategy.
    """

    if connection.vendor != "postgresql" or not normalized_query:
        return queryset
    from django.contrib.postgres.search import (
        SearchQuery,
        SearchRank,
        SearchVector,
        TrigramSimilarity,
    )

    vector = SearchVector(
        "display_name",
        "canonical_name",
        "aliases__alias_normalized",
        config="simple",
    )
    search_query = SearchQuery(normalized_query, config="simple")
    return (
        queryset.annotate(
            _text_rank=SearchRank(vector, search_query),
            _trigram_rank=TrigramSimilarity("canonical_name", normalized_query),
        )
        .filter(Q(_text_rank__gt=0) | Q(_trigram_rank__gte=0.30))
        .order_by("canonical_name", "pk")
    )


def _party_terms(party: Party, aliases: Iterable[PartyAlias]) -> tuple[str, ...]:
    alias_terms: list[str] = []
    for alias in aliases:
        alias_terms.append(alias.alias_normalized)
        if "(" in alias.alias_normalized:
            alias_terms.append(alias.alias_normalized.split("(", 1)[0].strip())
    return (party.display_name, party.canonical_name, *alias_terms)


def _first_lead(lead_by_party: dict[int, list[Lead]], party_id: int) -> Lead | None:
    leads = lead_by_party.get(party_id, [])
    return leads[0] if leads else None


def _party_url(lead_by_party: dict[int, list[Lead]], party_id: int) -> str:
    lead = _first_lead(lead_by_party, party_id)
    if lead is None:
        return "/today/"
    lead_number = lead.lead_number or f"LEAD-{lead.pk:06d}"
    return f"/leads/{lead_number}/"


def _party_context(
    actor: IdentityProfile,
) -> tuple[list[Lead], dict[int, list[Lead]], set[int]]:
    leads = list(
        visible_leads(actor)
        .select_related("campaign", "current_stage")
        .prefetch_related("party_links__party")
    )
    lead_by_party: dict[int, list[Lead]] = defaultdict(list)
    for lead in leads:
        for link in lead.party_links.all():
            lead_by_party[link.party_id].append(lead)
    return leads, dict(lead_by_party), {lead.pk for lead in leads}


def search(
    *,
    actor: IdentityProfile,
    query: str,
    cursor: int | str | None = None,
    page_size: int = 20,
) -> SearchPage:
    """Search only records reachable through the actor's active VIEW grants."""

    raw_query = _bounded_query(query)
    normalized_query = comparison_key(raw_query)
    page_start = _cursor(cursor)
    page_size = _page_size(page_size)
    if not normalized_query:
        return SearchPage(raw_query, (), 0, None)

    leads, lead_by_party, lead_ids = _party_context(actor)
    if not lead_ids:
        return SearchPage(raw_query, (), 0, None)

    visible_party_ids = set(lead_by_party)
    party_queryset = (
        Party.objects.active()
        .filter(pk__in=visible_party_ids)
        .select_related("person", "organization")
        .prefetch_related("aliases", "contact_point_links__contact_point")
        .order_by("canonical_name", "pk")
    )
    exact_email, email_quality = normalize_contact_value(ContactKind.EMAIL, raw_query)
    exact_phone, phone_quality = normalize_contact_value(ContactKind.PHONE, raw_query)
    identifier_values = {
        value
        for value, quality in (
            (exact_email, email_quality),
            (exact_phone, phone_quality),
        )
        if value and quality == "VALID"
    }
    direct_filter = (
        Q(display_name__icontains=normalized_query)
        | Q(canonical_name__icontains=normalized_query)
        | Q(aliases__alias_normalized__icontains=normalized_query)
    )
    if identifier_values:
        direct_filter |= Q(
            contact_point_links__contact_point__normalized_value__in=identifier_values
        )
    direct_party_ids = set(
        party_queryset.filter(direct_filter).values_list("pk", flat=True)
    )
    party_pool = _postgres_party_pool(party_queryset, normalized_query)
    if direct_party_ids:
        party_pool = party_pool.filter(pk__in=direct_party_ids)
    else:
        party_pool = party_pool[:MAX_FUZZY_CANDIDATES]

    result_by_key: dict[tuple[str, int], SearchResult] = {}

    def add_result(result: SearchResult) -> None:
        key = (result.result_type, result.object_id)
        previous = result_by_key.get(key)
        if previous is None or result.score > previous.score:
            result_by_key[key] = result

    for party in party_pool:
        aliases = tuple(party.aliases.all())
        contacts = tuple(party.contact_point_links.all())
        terms = _party_terms(party, aliases)
        contact_match = any(
            link.contact_point.normalized_value in identifier_values
            for link in contacts
        )
        exact_text = any(comparison_key(term) == normalized_query for term in terms)
        contains_text = any(normalized_query in comparison_key(term) for term in terms)
        score = (
            1.0
            if contact_match
            else 0.98
            if exact_text
            else 0.82
            if contains_text
            else 0.0
        )
        reason = "Correo o teléfono exacto" if contact_match else "Nombre normalizado"
        if exact_text:
            reason = "Nombre o alias exacto"
        if score == 0.0:
            ratio = max(
                (_similarity(normalized_query, term) for term in terms), default=0.0
            )
            if ratio < 0.84:
                continue
            score = 0.50 + ratio * 0.30
            reason = "Nombre similar; revisar coincidencia"
        lead = _first_lead(lead_by_party, party.pk)
        if lead is None:
            continue
        add_result(
            SearchResult(
                result_type="party",
                object_id=party.pk,
                title=party.display_name,
                subtitle=f"{party.get_party_type_display()} · {lead.lead_number}",
                url=_party_url(lead_by_party, party.pk),
                match_reason=reason,
                score=score,
            )
        )

    normalized_terms = set(_terms(normalized_query))
    for lead in leads:
        lead_number = lead.lead_number or f"LEAD-{lead.pk:06d}"
        source_text = " ".join(str(value) for value in lead.source_attribution.values())
        lead_terms = (
            lead_number,
            source_text,
            lead.current_stage.label,
            lead.campaign.label,
        )
        exact_lead = comparison_key(lead_number) == normalized_query
        contains_lead = any(
            normalized_query in comparison_key(term) for term in lead_terms
        )
        if exact_lead or contains_lead:
            linked_party = lead.party_links.select_related("party").first()
            title = linked_party.party.display_name if linked_party else lead_number
            add_result(
                SearchResult(
                    result_type="lead",
                    object_id=lead.pk,
                    title=title,
                    subtitle=f"{lead_number} · {lead.current_stage.label}",
                    url=f"/leads/{lead_number}/",
                    match_reason="Número de lead o fuente",
                    score=0.97 if exact_lead else 0.72,
                )
            )

    interaction_qs = (
        Interaction.objects.filter(lead_id__in=lead_ids)
        .select_related("lead")
        .only("pk", "lead_id", "lead__lead_number", "note", "occurrence_date")
        .order_by("lead_id", "-occurrence_date", "-pk")[:MAX_NOTE_CANDIDATES]
    )
    for interaction in interaction_qs:
        if normalized_query not in comparison_key(
            interaction.note
        ) and not normalized_terms.intersection(_terms(interaction.note)):
            continue
        add_result(
            SearchResult(
                result_type="activity",
                object_id=interaction.pk,
                title=f"Actividad en {interaction.lead.lead_number}",
                subtitle=interaction.occurrence_date.strftime("%d/%m/%Y"),
                url=f"/leads/{interaction.lead.lead_number}/",
                match_reason="Nota autorizada",
                score=0.68,
                snippet=_excerpt(interaction.note, normalized_query),
            )
        )

    task_qs = (
        Task.objects.filter(lead_id__in=lead_ids)
        .select_related("lead")
        .only("pk", "lead_id", "lead__lead_number", "description", "due_date")
        .order_by("lead_id", "due_date", "pk")[:MAX_NOTE_CANDIDATES]
    )
    for task in task_qs:
        if normalized_query not in comparison_key(
            task.description
        ) and not normalized_terms.intersection(_terms(task.description)):
            continue
        add_result(
            SearchResult(
                result_type="task",
                object_id=task.pk,
                title=f"Tarea en {task.lead.lead_number}",
                subtitle=task.due_date.strftime("%d/%m/%Y"),
                url=f"/leads/{task.lead.lead_number}/",
                match_reason="Tarea autorizada",
                score=0.66,
                snippet=_excerpt(task.description, normalized_query),
            )
        )

    ordered = sorted(
        result_by_key.values(),
        key=lambda result: (-result.score, result.result_type, result.object_id),
    )
    total = len(ordered)
    page = ordered[page_start : page_start + page_size]
    next_cursor = page_start + page_size if page_start + page_size < total else None
    return SearchPage(raw_query, tuple(page), total, next_cursor)
