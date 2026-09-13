"""Landing page and dependency-safe health probes."""

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import DatabaseError, connection
from django.db.transaction import non_atomic_requests
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import render
from django.utils.crypto import constant_time_compare
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_http_methods

from simple_crm.config.observability import metrics_snapshot
from simple_crm.crm.models import Campaign, LeadStatus
from simple_crm.identity.models import IdentityProfile
from simple_crm.reporting.metrics import dashboard
from simple_crm.reporting.search import SearchInputError
from simple_crm.reporting.search import search as global_search
from simple_crm.reporting.services import (
    create_saved_view,
    execute_definition,
    execute_saved_view,
    list_saved_views,
)

from .jobs import (
    get_notification_preferences,
    operator_jobs,
    update_notification_preferences,
)
from .workspace import lead_detail, today_workspace


@require_GET
@non_atomic_requests
def home(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "platform/home.html",
        {
            "has_workspace": request.user.is_authenticated,
            "nav_items": _nav_items(),
        },
    )


@require_GET
def help_page(request: HttpRequest) -> HttpResponse:
    return render(request, "platform/help.html", {"nav_items": _nav_items()})


def _identity(request: HttpRequest) -> IdentityProfile:
    user_id = request.user.pk
    if user_id is None:
        raise PermissionDenied("La identidad no está habilitada.")
    try:
        return IdentityProfile.objects.get(user_id=user_id)
    except IdentityProfile.DoesNotExist as exc:
        raise PermissionDenied("La identidad no está habilitada.") from exc


@login_required
@require_GET
def today(request: HttpRequest) -> HttpResponse:
    profile = _identity(request)
    workspace = today_workspace(
        profile, only_mine=request.GET.get("view") == "my-leads"
    )
    return render(
        request,
        "platform/today.html",
        {
            "workspace": workspace,
            "nav_items": _nav_items(),
            "only_mine": request.GET.get("view") == "my-leads",
        },
    )


@login_required
@require_GET
def lead_detail_page(request: HttpRequest, lead_number: str) -> HttpResponse:
    detail = lead_detail(actor=_identity(request), lead_number=lead_number)
    return render(
        request,
        "platform/lead_detail.html",
        {"detail": detail, "nav_items": _nav_items()},
    )


@login_required
@require_GET
def search_page(request: HttpRequest) -> HttpResponse:
    profile = _identity(request)
    query = request.GET.get("q", "")
    error = ""
    try:
        page = global_search(
            actor=profile,
            query=query,
            cursor=request.GET.get("cursor"),
        )
    except (SearchInputError, ValidationError) as exc:
        page = None
        error = str(exc.messages[0]) if isinstance(exc, ValidationError) else str(exc)
    return render(
        request,
        "platform/search.html",
        {
            "page": page,
            "query": query,
            "error": error,
            "nav_items": _nav_items(),
        },
    )


@login_required
def segments_page(request: HttpRequest) -> HttpResponse:
    profile = _identity(request)
    error = ""
    saved_id = request.GET.get("view", "")
    try:
        if saved_id:
            page = execute_saved_view(actor=profile, view_id=int(saved_id))
        else:
            conditions = []
            for field in ("stage", "campaign", "readiness", "source"):
                value = request.GET.get(field, "").strip()
                if value:
                    conditions.append(
                        {"field": field, "operator": "eq", "value": value}
                    )
            definition = {
                "and": conditions,
                "or": [],
                "sort": request.GET.get("sort", "created_desc"),
            }
            page = execute_definition(actor=profile, definition=definition)
            if request.method == "POST" and request.POST.get("save_name", "").strip():
                create_saved_view(
                    actor=profile,
                    name=request.POST["save_name"],
                    definition=definition,
                    shared=request.POST.get("shared") == "on",
                )
        saved_views = list_saved_views(profile)
    except (PermissionDenied, ValidationError, ValueError) as exc:
        page = None
        saved_views = list_saved_views(profile)
        error = str(exc.messages[0]) if isinstance(exc, ValidationError) else str(exc)
    return render(
        request,
        "platform/segments.html",
        {
            "page": page,
            "error": error,
            "saved_views": saved_views,
            "stages": LeadStatus.objects.filter(is_active=True),
            "campaigns": Campaign.objects.filter(is_active=True),
            "selected": request.GET,
            "nav_items": _nav_items(),
        },
    )


@login_required
@require_GET
def reports_page(request: HttpRequest) -> HttpResponse:
    profile = _identity(request)
    error = ""
    report = None
    try:
        from_value = request.GET.get("from", "")
        to_value = request.GET.get("to", "")
        from datetime import date

        report = dashboard(
            actor=profile,
            start_date=date.fromisoformat(from_value) if from_value else None,
            end_date=date.fromisoformat(to_value) if to_value else None,
        )
    except (ValidationError, ValueError) as exc:
        error = str(exc.messages[0]) if isinstance(exc, ValidationError) else str(exc)
    return render(
        request,
        "platform/reports.html",
        {
            "report": report,
            "error": error,
            "selected": request.GET,
            "nav_items": _nav_items(),
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
def notification_settings_page(request: HttpRequest) -> HttpResponse:
    profile = _identity(request)
    preferences = get_notification_preferences(profile)
    error = ""
    saved = False
    if request.method == "POST":
        try:
            preferences = update_notification_preferences(
                actor=profile,
                target=profile,
                digest_enabled=request.POST.get("digest_enabled") == "on",
                escalation_enabled=request.POST.get("escalation_enabled") == "on",
                daily_digest_hour=int(request.POST.get("daily_digest_hour", "8")),
            )
            saved = True
        except (PermissionDenied, ValidationError, ValueError) as exc:
            error = (
                str(exc.messages[0]) if isinstance(exc, ValidationError) else str(exc)
            )
    try:
        failed_jobs = operator_jobs(profile)
    except PermissionDenied:
        failed_jobs = []
    return render(
        request,
        "platform/notifications.html",
        {
            "preferences": preferences,
            "failed_jobs": failed_jobs,
            "error": error,
            "saved": saved,
            "nav_items": _nav_items(),
        },
    )


def _nav_items() -> tuple[dict[str, str | bool], ...]:
    return (
        {"label": "Hoy", "url": "/today/", "available": True},
        {"label": "Mis leads", "url": "/today/?view=my-leads", "available": True},
        {"label": "Buscar", "url": "/buscar/", "available": True},
        {"label": "Segmentos", "url": "/segmentos/", "available": True},
        {"label": "Informes", "url": "/informes/", "available": True},
        {
            "label": "Notificaciones",
            "url": "/configuracion/notificaciones/",
            "available": True,
        },
        {"label": "Calidad de datos", "url": "#proximamente", "available": False},
        {"label": "Ayuda", "url": "/ayuda/", "available": True},
    )


@require_GET
@never_cache
@non_atomic_requests
def liveness(request: HttpRequest) -> JsonResponse:
    """Report process availability without touching external dependencies."""
    return JsonResponse({"status": "ok"})


@require_GET
@never_cache
def readiness(request: HttpRequest) -> JsonResponse:
    """Report generic database readiness without exposing diagnostics."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except DatabaseError:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ready"})


@require_GET
@never_cache
def metrics(request: HttpRequest) -> JsonResponse:
    """Expose only aggregate metrics when an internal token is configured."""

    configured_token = getattr(settings, "OBSERVABILITY_METRICS_TOKEN", "")
    supplied_token = request.headers.get("X-Metrics-Token", "")
    if not configured_token or not constant_time_compare(
        supplied_token, configured_token
    ):
        return JsonResponse({"detail": "No encontrado."}, status=404)
    return JsonResponse({"metrics": metrics_snapshot()})
