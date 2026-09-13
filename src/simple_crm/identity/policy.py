"""Single authorization policy for actions and object/team/campaign scope."""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, TypeVar

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q, QuerySet
from django.http import HttpRequest, HttpResponse
from django.utils import timezone

from .models import (
    Action,
    ElevationUse,
    IdentityProfile,
    ScopeGrant,
    ScopeType,
    TemporaryElevation,
)


@dataclass(frozen=True)
class ScopeSpec:
    """The normalized scope passed by every visibility-sensitive caller."""

    scope_type: str
    team_id: int | None = None
    campaign_id: int | None = None
    content_type_id: int | None = None
    object_id: str | None = None

    @classmethod
    def global_scope(cls) -> "ScopeSpec":
        return cls(ScopeType.GLOBAL)

    @classmethod
    def team_scope(cls, team_id: int) -> "ScopeSpec":
        return cls(ScopeType.TEAM, team_id=team_id)

    @classmethod
    def campaign_scope(cls, campaign_id: int) -> "ScopeSpec":
        return cls(ScopeType.CAMPAIGN, campaign_id=campaign_id)

    @classmethod
    def object_scope(cls, content_type_id: int, object_id: str | int) -> "ScopeSpec":
        return cls(
            ScopeType.OBJECT,
            content_type_id=content_type_id,
            object_id=str(object_id),
        )

    def as_dict(self) -> dict[str, int | str | None]:
        return {
            "scope_type": self.scope_type,
            "team_id": self.team_id,
            "campaign_id": self.campaign_id,
            "content_type_id": self.content_type_id,
            "object_id": self.object_id,
        }


def _profile_for(subject: Any) -> IdentityProfile | None:
    if isinstance(subject, IdentityProfile):
        return subject
    if not getattr(subject, "is_authenticated", False):
        return None
    try:
        return IdentityProfile.objects.get(user=subject)
    except IdentityProfile.DoesNotExist:
        return None


def identity_is_enabled(subject: Any) -> bool:
    profile = _profile_for(subject)
    return profile is not None and profile.is_enabled


def _active_range(
    queryset: QuerySet[Any], now: Any, end_field: str = "expires_at"
) -> QuerySet[Any]:
    return queryset.filter(
        starts_at__lte=now,
    ).filter(Q(**{f"{end_field}__isnull": True}) | Q(**{f"{end_field}__gt": now}))


def _active_assignments(profile: IdentityProfile, now: Any) -> QuerySet[Any]:
    return profile.role_assignments.filter(
        starts_at__lte=now,
    ).filter(Q(ends_at__isnull=True) | Q(ends_at__gt=now), role__is_active=True)


def has_action_permission(subject: Any, action: str | Action, now: Any = None) -> bool:
    """Return whether an enabled identity has the requested role action."""

    profile = _profile_for(subject)
    if profile is None or not profile.is_enabled:
        return False
    normalized_action = str(action)
    now = now or timezone.now()
    return (
        _active_assignments(profile, now)
        .filter(role__action_permissions__action=normalized_action)
        .exists()
    )


def _grant_matches(grant: ScopeGrant, scope: ScopeSpec) -> bool:
    if grant.scope_type == ScopeType.GLOBAL:
        return True
    if grant.scope_type != scope.scope_type:
        return False
    if scope.scope_type == ScopeType.TEAM:
        return grant.team_id == scope.team_id
    if scope.scope_type == ScopeType.CAMPAIGN:
        return grant.campaign_id == scope.campaign_id
    return (
        grant.content_type_id == scope.content_type_id
        and grant.object_id == scope.object_id
    )


def _has_scope(profile: IdentityProfile, scope: ScopeSpec, now: Any) -> bool:
    if scope.scope_type not in ScopeType.values:
        return False
    grants = _active_range(profile.scope_grants.all(), now).select_related(
        "team", "campaign"
    )
    if any(_grant_matches(grant, scope) for grant in grants):
        return True
    if scope.scope_type == ScopeType.TEAM:
        memberships = _active_range(profile.team_memberships.all(), now, "ends_at")
        return memberships.filter(team_id=scope.team_id, team__is_active=True).exists()
    return False


def _elevation_matches(elevation: TemporaryElevation, scope: ScopeSpec) -> bool:
    if elevation.scope_type == ScopeType.GLOBAL:
        return True
    if elevation.scope_type != scope.scope_type:
        return False
    if scope.scope_type == ScopeType.TEAM:
        return elevation.team_id == scope.team_id
    if scope.scope_type == ScopeType.CAMPAIGN:
        return elevation.campaign_id == scope.campaign_id
    return (
        elevation.content_type_id == scope.content_type_id
        and elevation.object_id == scope.object_id
    )


def _active_elevations(
    profile: IdentityProfile, action: str | Action, now: Any
) -> QuerySet[TemporaryElevation]:
    return _active_range(
        profile.elevations.filter(action=str(action), revoked_at__isnull=True),
        now,
    )


def _record_elevation_use(
    elevation: TemporaryElevation,
    subject: Any,
    scope: ScopeSpec,
) -> None:
    with transaction.atomic():
        ElevationUse.objects.create(
            elevation=elevation,
            actor=subject.user if isinstance(subject, IdentityProfile) else subject,
            action=elevation.action,
            reason=elevation.reason,
            scope_type=scope.scope_type,
            scope_snapshot=scope.as_dict(),
            approved_by=elevation.approved_by,
        )


def can_access(
    subject: Any,
    action: str | Action,
    scope: ScopeSpec,
    now: Any = None,
) -> bool:
    """Require both an action grant and an active scope, by default."""

    profile = _profile_for(subject)
    if profile is None or not profile.is_enabled:
        return False
    normalized_action = str(action)
    now = now or timezone.now()
    if has_action_permission(profile, normalized_action, now) and _has_scope(
        profile, scope, now
    ):
        return True
    for elevation in _active_elevations(profile, normalized_action, now):
        if _elevation_matches(elevation, scope):
            _record_elevation_use(elevation, profile, scope)
            return True
    return False


def grant_temporary_elevation(
    subject: Any,
    *,
    target: IdentityProfile,
    action: str | Action,
    scope: ScopeSpec,
    reason: str,
    expires_at: Any,
    starts_at: Any = None,
) -> TemporaryElevation:
    """Create a bounded, approved elevation after an admin authorization check."""

    approver = _profile_for(subject)
    if approver is None or not approver.is_enabled:
        raise PermissionDenied("No tiene autorización para elevar acceso.")
    starts_at = starts_at or timezone.now()
    if not reason.strip():
        raise ValueError("La elevación requiere un motivo.")
    if expires_at <= starts_at:
        raise ValueError("La expiración debe ser posterior al inicio.")
    if not has_action_permission(approver, Action.ELEVATE_ACCESS, starts_at):
        raise PermissionDenied("No tiene autorización para elevar acceso.")
    if not _has_scope(approver, scope, starts_at):
        raise PermissionDenied("El aprobador no tiene el alcance solicitado.")
    if not target.is_enabled:
        raise PermissionDenied("La identidad destino está deshabilitada.")
    if approver.pk == target.pk:
        raise PermissionDenied("La elevación requiere un aprobador distinto.")
    return TemporaryElevation.objects.create(
        identity=target,
        action=str(action),
        scope_type=scope.scope_type,
        team_id=scope.team_id,
        campaign_id=scope.campaign_id,
        content_type_id=scope.content_type_id,
        object_id=scope.object_id,
        reason=reason.strip(),
        approved_by=approver.user,
        starts_at=starts_at,
        expires_at=expires_at,
    )


def scoped_queryset(
    queryset: QuerySet[Any],
    subject: Any,
    action: str | Action,
    *,
    team_field: str | None = None,
    campaign_field: str | None = None,
    now: Any = None,
) -> QuerySet[Any]:
    """Apply the same visibility policy to search, lists, reports, and exports."""

    profile = _profile_for(subject)
    if profile is None or not profile.is_enabled:
        return queryset.none()
    normalized_action = str(action)
    now = now or timezone.now()
    has_role_action = has_action_permission(profile, normalized_action, now)
    elevations = list(_active_elevations(profile, normalized_action, now))
    if not has_role_action and not elevations:
        return queryset.none()

    model_content_type = ContentType.objects.get_for_model(
        queryset.model, for_concrete_model=False
    )
    filters = Q()
    unrestricted = False
    grants = list(_active_range(profile.scope_grants.all(), now))
    for grant in grants:
        if grant.scope_type == ScopeType.GLOBAL:
            unrestricted = True
        elif grant.scope_type == ScopeType.OBJECT:
            if grant.content_type_id == model_content_type.pk:
                filters |= Q(pk=grant.object_id)
        elif grant.scope_type == ScopeType.TEAM and team_field and grant.team_id:
            filters |= Q(**{f"{team_field}__exact": grant.team_id})
        elif (
            grant.scope_type == ScopeType.CAMPAIGN
            and campaign_field
            and grant.campaign_id
        ):
            filters |= Q(**{f"{campaign_field}__exact": grant.campaign_id})

    if team_field:
        team_ids = (
            _active_range(profile.team_memberships.all(), now, "ends_at")
            .filter(team__is_active=True)
            .values_list("team_id", flat=True)
        )
        filters |= Q(**{f"{team_field}__in": team_ids})

    for elevation in elevations:
        if elevation.scope_type == ScopeType.GLOBAL:
            unrestricted = True
        elif elevation.scope_type == ScopeType.OBJECT:
            if elevation.content_type_id == model_content_type.pk:
                filters |= Q(pk=elevation.object_id)
        elif (
            elevation.scope_type == ScopeType.TEAM and team_field and elevation.team_id
        ):
            filters |= Q(**{f"{team_field}__exact": elevation.team_id})
        elif (
            elevation.scope_type == ScopeType.CAMPAIGN
            and campaign_field
            and elevation.campaign_id
        ):
            filters |= Q(**{f"{campaign_field}__exact": elevation.campaign_id})

    if unrestricted:
        return queryset
    return queryset.filter(filters).distinct() if filters else queryset.none()


View = TypeVar("View", bound=Callable[..., HttpResponse])


def require_access(
    action: str | Action,
    scope_resolver: Callable[[HttpRequest, tuple[Any, ...], dict[str, Any]], ScopeSpec],
) -> Callable[[View], View]:
    """Protect a server endpoint without allowing callers to bypass scope policy."""

    def decorator(view: View) -> View:
        @wraps(view)
        def wrapped(request: HttpRequest, *args: Any, **kwargs: Any) -> HttpResponse:
            scope = scope_resolver(request, args, kwargs)
            if not can_access(request.user, action, scope):
                raise PermissionDenied("No tiene autorización para esta operación.")
            return view(request, *args, **kwargs)

        return wrapped  # type: ignore[return-value]

    return decorator
