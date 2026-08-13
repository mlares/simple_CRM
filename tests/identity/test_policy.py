from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.utils import timezone

from simple_crm.crm.models import Campaign
from simple_crm.identity.models import (
    Action,
    ElevationUse,
    IdentityProfile,
    Role,
    RoleAssignment,
    ScopeGrant,
    ScopeType,
    Team,
    TeamMembership,
    TemporaryElevation,
)
from simple_crm.identity.permissions import ROLE_ACTIONS
from simple_crm.identity.policy import (
    ScopeSpec,
    can_access,
    grant_temporary_elevation,
    has_action_permission,
    scoped_queryset,
)


def _identity(username: str, role_code: str) -> IdentityProfile:
    user = get_user_model().objects.create_user(username=username, password="safe-pass")
    profile = IdentityProfile.objects.get(user=user)
    role = Role.objects.get(code=role_code)
    RoleAssignment.objects.create(identity=profile, role=role)
    return profile


def _global_scope(profile: IdentityProfile) -> None:
    ScopeGrant.objects.create(identity=profile, scope_type=ScopeType.GLOBAL)


@pytest.mark.django_db
def test_every_seeded_role_has_an_explicit_action_matrix() -> None:
    for role_code, actions in ROLE_ACTIONS.items():
        profile = _identity(role_code, role_code)
        _global_scope(profile)
        for action in Action:
            assert can_access(profile, action, ScopeSpec.global_scope()) is (
                action in actions
            )


@pytest.mark.django_db
def test_team_campaign_and_exact_object_scope_hide_cross_owner_records() -> None:
    profile = _identity("seller", "sales_representative")
    team = Team.objects.create(code="TEAM-A", label="Equipo A")
    TeamMembership.objects.create(identity=profile, team=team)
    assert can_access(profile, Action.VIEW, ScopeSpec.team_scope(team.pk))
    assert not can_access(profile, Action.VIEW, ScopeSpec.team_scope(team.pk + 1))

    campaign = Campaign.objects.get(code="GENERAL")
    other_campaign = Campaign.objects.exclude(pk=campaign.pk).first()
    if other_campaign is None:
        other_campaign = Campaign.objects.create(code="OTRA", label="Otra")
    ScopeGrant.objects.create(
        identity=profile, scope_type=ScopeType.CAMPAIGN, campaign=campaign
    )
    assert can_access(profile, Action.VIEW, ScopeSpec.campaign_scope(campaign.pk))
    assert not can_access(
        profile, Action.VIEW, ScopeSpec.campaign_scope(other_campaign.pk)
    )

    content_type = ContentType.objects.get_for_model(Campaign)
    ScopeGrant.objects.create(
        identity=profile,
        scope_type=ScopeType.OBJECT,
        content_type=content_type,
        object_id=str(campaign.pk),
    )
    assert can_access(
        profile,
        Action.VIEW,
        ScopeSpec.object_scope(content_type.pk, campaign.pk),
    )
    assert not can_access(
        profile,
        Action.VIEW,
        ScopeSpec.object_scope(content_type.pk, other_campaign.pk),
    )

    visible = scoped_queryset(Campaign.objects.all(), profile, Action.VIEW)
    assert list(visible.values_list("pk", flat=True)) == [campaign.pk]


@pytest.mark.django_db
def test_view_only_never_implies_sensitive_actions_or_catalog_management() -> None:
    profile = _identity("reader", "report_viewer")
    _global_scope(profile)
    assert has_action_permission(profile, Action.VIEW)
    for action in (
        Action.BULK_EXPORT,
        Action.MERGE,
        Action.IMPORT,
        Action.REASSIGN,
        Action.MANAGE_CATALOG,
    ):
        assert not can_access(profile, action, ScopeSpec.global_scope())


@pytest.mark.django_db
def test_temporary_elevation_requires_approval_expires_and_audits_use() -> None:
    approver = _identity("admin", "system_administrator")
    target = _identity("temporary", "report_viewer")
    _global_scope(approver)
    expires_at = timezone.now() + timedelta(hours=1)
    elevation = grant_temporary_elevation(
        approver,
        target=target,
        action=Action.MERGE,
        scope=ScopeSpec.global_scope(),
        reason="Resolver una excepción aprobada",
        expires_at=expires_at,
    )

    assert can_access(target, Action.MERGE, ScopeSpec.global_scope())
    usage = ElevationUse.objects.get(elevation=elevation)
    assert usage.actor == target.user
    assert usage.approved_by == approver.user
    assert usage.reason == "Resolver una excepción aprobada"
    assert usage.scope_snapshot["scope_type"] == ScopeType.GLOBAL

    expired = TemporaryElevation.objects.create(
        identity=target,
        action=Action.IMPORT,
        scope_type=ScopeType.GLOBAL,
        reason="Ventana ya vencida",
        approved_by=approver.user,
        starts_at=timezone.now() - timedelta(hours=2),
        expires_at=timezone.now() - timedelta(hours=1),
    )
    assert not can_access(target, Action.IMPORT, ScopeSpec.global_scope())
    assert not ElevationUse.objects.filter(elevation=expired).exists()


@pytest.mark.django_db
def test_elevation_requires_distinct_approver_and_matching_scope() -> None:
    approver = _identity("manager", "sales_manager")
    target = _identity("target", "report_viewer")
    with pytest.raises(PermissionDenied):
        grant_temporary_elevation(
            approver,
            target=target,
            action=Action.MERGE,
            scope=ScopeSpec.global_scope(),
            reason="Sin alcance",
            expires_at=timezone.now() + timedelta(hours=1),
        )
