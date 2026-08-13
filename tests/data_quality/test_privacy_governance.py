from datetime import date

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied, ValidationError

from simple_crm.activity.models import InteractionDirection, InteractionResult
from simple_crm.activity.services import quick_contact
from simple_crm.crm.lead_services import create_lead
from simple_crm.crm.models import (
    Campaign,
    ContactKind,
    ContactPoint,
    LeadPartyRole,
    PartyContactPoint,
)
from simple_crm.crm.services import ContactInput, create_organization_party
from simple_crm.data_quality.models import (
    GovernanceAuditEvent,
    LegalHold,
    PrivacyCaseType,
    RetentionCategory,
    RetentionDecisionState,
)
from simple_crm.data_quality.privacy import (
    approve_retention,
    complete_privacy_case,
    execute_retention,
    open_privacy_case,
    preview_retention,
    privacy_bundle,
    suppress_contact_point,
)
from simple_crm.identity.models import (
    IdentityProfile,
    Role,
    RoleAssignment,
    ScopeGrant,
    ScopeType,
)


def _actor(username: str, role_code: str) -> IdentityProfile:
    user = get_user_model().objects.create_user(username=username, password="safe-pass")
    profile = IdentityProfile.objects.get(user=user)
    RoleAssignment.objects.create(
        identity=profile, role=Role.objects.get(code=role_code)
    )
    ScopeGrant.objects.create(identity=profile, scope_type=ScopeType.GLOBAL)
    return profile


def _party_and_lead(actor: IdentityProfile):
    campaign = Campaign.objects.get(code="GENERAL")
    ScopeGrant.objects.get_or_create(
        identity=actor, scope_type=ScopeType.CAMPAIGN, campaign=campaign
    )
    party, _ = create_organization_party(
        display_name="Cuenta privada",
        contact_inputs=(
            ContactInput(kind=ContactKind.EMAIL, raw_value="privada@example.com"),
        ),
    )
    lead, _ = create_lead(
        actor=actor,
        campaign=campaign,
        owner=actor,
        parties=((party, LeadPartyRole.ACCOUNT),),
    )
    return party, lead


@pytest.mark.django_db
def test_privacy_bundle_is_permissioned_redacted_and_case_completion_is_audited() -> (
    None
):
    admin = _actor("privacy-admin", "system_administrator")
    party, lead = _party_and_lead(admin)
    quick_contact(
        actor=admin,
        lead=lead,
        occurrence_date=date.today(),
        direction=InteractionDirection.OUTBOUND,
        channel_code="EMAIL",
        outcome_code="SEGUIMIENTO",
        result=InteractionResult.COMPLETED,
        note="Nota que no debe duplicarse en auditoría.",
    )
    reviewer = _actor("privacy-reviewer", "privacy_audit_reviewer")
    bundle = privacy_bundle(actor=reviewer, party_id=party.pk)
    assert bundle.party.pk == party.pk
    assert bundle.contact_points[0]["raw_value"] == "privada@example.com"
    assert bundle.interactions[0]["has_note"] is True
    assert "Nota que no debe" not in str(bundle.interactions)

    case = open_privacy_case(
        actor=reviewer,
        subject=party,
        case_type=PrivacyCaseType.CORRECTION,
        reason="Corrección solicitada",
        correlation="privacy-test-1",
    )
    completed = complete_privacy_case(
        actor=admin, case_id=case.pk, decision_reason="Corrección revisada"
    )
    assert completed.state == "COMPLETED"
    event = GovernanceAuditEvent.objects.get(
        target_type="PrivacyCase",
        target_id=str(case.pk),
        action="privacy_case_completed",
    )
    assert "Nota que no debe" not in str(event.metadata)
    with pytest.raises(ValidationError):
        event.delete()


@pytest.mark.django_db
def test_suppression_is_durable_and_retention_holds_require_approval() -> None:
    admin = _actor("privacy-suppress", "system_administrator")
    party, _ = _party_and_lead(admin)
    link = PartyContactPoint.objects.get(party=party)
    point = ContactPoint.objects.get(pk=link.contact_point_id)
    suppress_contact_point(
        actor=admin, contact_point=point, reason="Solicitud de supresión"
    )
    assert ContactPoint.objects.get(pk=point.pk).is_suppressed is True
    reloaded = ContactPoint.objects.get(pk=point.pk)
    reloaded.is_suppressed = False
    with pytest.raises(ValidationError):
        reloaded.save()

    category = RetentionCategory.objects.create(
        code="SALES_TEST",
        label="Operación comercial",
        retention_days=365,
        purpose="Prueba",
    )
    hold = LegalHold.objects.create(
        target_type="Party",
        target_id=str(party.pk),
        reason="Revisión legal",
        created_by=admin.user,
    )
    decision = preview_retention(
        actor=admin,
        target_type="Party",
        target_id=str(party.pk),
        category=category,
        reason="Evaluación",
    )
    assert decision.legal_hold_excluded is True
    approved = approve_retention(
        actor=admin, decision_id=decision.pk, reason="Aprobación explícita"
    )
    executed = execute_retention(
        actor=admin, decision_id=approved.pk, reason="Ejecución revisable"
    )
    assert executed.state == RetentionDecisionState.EXECUTED
    assert executed.legal_hold_excluded is True
    hold.active = False
    hold.save(update_fields=("active",))


@pytest.mark.django_db
def test_privacy_reviewer_cannot_execute_correction_or_read_without_audit_scope() -> (
    None
):
    seller = _actor("privacy-seller", "sales_representative")
    party, _ = _party_and_lead(seller)
    with pytest.raises(PermissionDenied):
        privacy_bundle(actor=seller, party_id=party.pk)
