from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model

from simple_crm.activity.models import InteractionDirection, InteractionResult
from simple_crm.activity.services import quick_contact
from simple_crm.crm.lead_services import create_lead
from simple_crm.crm.models import Campaign, ContactKind, LeadPartyRole
from simple_crm.crm.services import ContactInput, create_organization_party
from simple_crm.identity.models import (
    IdentityProfile,
    Role,
    RoleAssignment,
    ScopeGrant,
    ScopeType,
)
from simple_crm.reporting.metrics import dashboard


def _actor(username: str, role_code: str = "sales_manager") -> IdentityProfile:
    user = get_user_model().objects.create_user(username=username, password="safe-pass")
    profile = IdentityProfile.objects.get(user=user)
    RoleAssignment.objects.create(
        identity=profile, role=Role.objects.get(code=role_code)
    )
    return profile


def _lead(actor: IdentityProfile, name: str, email: str = ""):
    campaign = Campaign.objects.get(code="GENERAL")
    ScopeGrant.objects.get_or_create(
        identity=actor, scope_type=ScopeType.CAMPAIGN, campaign=campaign
    )
    party, _ = create_organization_party(
        display_name=name,
        contact_inputs=(
            (ContactInput(kind=ContactKind.EMAIL, raw_value=email),) if email else ()
        ),
    )
    return create_lead(
        actor=actor,
        campaign=campaign,
        owner=actor,
        parties=((party, LeadPartyRole.ACCOUNT),),
    )[0]


@pytest.mark.django_db
def test_dashboard_metrics_use_occurrence_dates_and_exclude_attempts_from_response_rate() -> (
    None
):
    actor = _actor("metrics-owner")
    _lead(actor, "Contactable", "contactable@example.com")
    contacted = _lead(actor, "Contactado")
    quick_contact(
        actor=actor,
        lead=contacted,
        occurrence_date=date.today(),
        direction=InteractionDirection.OUTBOUND,
        channel_code="EMAIL",
        outcome_code="SEGUIMIENTO",
        result=InteractionResult.COMPLETED,
        note="Se acordó enviar propuesta.",
    )
    quick_contact(
        actor=actor,
        lead=contacted,
        occurrence_date=date.today(),
        direction=InteractionDirection.INBOUND,
        channel_code="EMAIL",
        outcome_code="CONTACTADO",
        result=InteractionResult.RESPONSE,
        note="Respondió con interés.",
    )
    attempted = _lead(actor, "Intento")
    quick_contact(
        actor=actor,
        lead=attempted,
        occurrence_date=date.today(),
        direction=InteractionDirection.OUTBOUND,
        channel_code="TELEFONO",
        outcome_code="SIN_RESPUESTA",
        result=InteractionResult.ATTEMPTED,
        note="No atendió la llamada.",
    )

    report = dashboard(actor=actor, start_date=date.today(), end_date=date.today())
    metrics = {metric.code: metric for metric in report.metrics}
    assert report.result_count == 3
    assert metrics["CONTACTABLE_LEAD"].numerator == 1
    assert metrics["CONTACTED_LEAD"].numerator == 1
    assert metrics["RESPONSE_RATE"].numerator == 1
    assert metrics["RESPONSE_RATE"].denominator == 1
    assert {section.code for section in report.sections} == {
        "attention_today",
        "pipeline",
        "activity",
        "response",
        "source",
        "stage_age",
    }
    assert report.scope_label == "Alcance autorizado actual"
    assert report.freshness_label == "Calculado en vivo"


@pytest.mark.django_db
def test_dashboard_scope_excludes_other_campaign_rows_and_stale_uses_local_cutoff() -> (
    None
):
    actor = _actor("metrics-scope")
    visible = _lead(actor, "Visible")
    visible_time = visible.updated_at - timedelta(days=20)
    type(visible).objects.filter(pk=visible.pk).update(updated_at=visible_time)
    outsider = _actor("metrics-outsider")
    hidden_campaign = Campaign.objects.create(code="METRIC-HIDDEN", label="Oculta")
    ScopeGrant.objects.create(
        identity=outsider, scope_type=ScopeType.CAMPAIGN, campaign=hidden_campaign
    )
    hidden_party, _ = create_organization_party(display_name="No visible")
    create_lead(
        actor=outsider,
        campaign=hidden_campaign,
        owner=outsider,
        parties=((hidden_party, LeadPartyRole.ACCOUNT),),
    )

    report = dashboard(
        actor=actor, start_date=date.today() - timedelta(days=30), end_date=date.today()
    )
    metrics = {metric.code: metric for metric in report.metrics}
    assert report.result_count == 1
    assert metrics["STALE_LEAD"].numerator == 1
