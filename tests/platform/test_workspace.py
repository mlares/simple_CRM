from datetime import date, timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import Client
from django.utils import timezone

from simple_crm.activity.models import InteractionDirection, InteractionResult
from simple_crm.activity.services import NextTaskSpec, quick_contact
from simple_crm.crm.lead_services import create_lead, transition_lead
from simple_crm.crm.models import Campaign, LeadAssignment, LeadPartyRole
from simple_crm.crm.services import create_organization_party
from simple_crm.identity.models import (
    IdentityProfile,
    Role,
    RoleAssignment,
    ScopeGrant,
    ScopeType,
)
from simple_crm.platform.workspace import today_workspace


def _manager(username: str, role_code: str = "sales_manager") -> IdentityProfile:
    user = get_user_model().objects.create_user(username=username, password="safe-pass")
    profile = IdentityProfile.objects.get(user=user)
    RoleAssignment.objects.create(
        identity=profile, role=Role.objects.get(code=role_code)
    )
    return profile


def _lead(actor: IdentityProfile, name: str = "Cuenta de prueba"):
    campaign = Campaign.objects.get(code="GENERAL")
    ScopeGrant.objects.create(
        identity=actor, scope_type=ScopeType.CAMPAIGN, campaign=campaign
    )
    party, _ = create_organization_party(display_name=name)
    lead, _ = create_lead(
        actor=actor,
        campaign=campaign,
        owner=actor,
        parties=((party, LeadPartyRole.ACCOUNT),),
    )
    return lead


@pytest.mark.django_db
def test_today_classifies_fixed_urgency_and_manager_unassigned_work() -> None:
    actor = _manager("workspace-manager")
    overdue = _lead(actor, "Cuenta vencida")
    due_today = _lead(actor, "Cuenta de hoy")
    response_lead = _lead(actor, "Cuenta con respuesta")
    stale = _lead(actor, "Cuenta estancada")
    unassigned = _lead(actor, "Cuenta sin dueño")

    quick_contact(
        actor=actor,
        lead=overdue,
        occurrence_date=date.today(),
        direction=InteractionDirection.OUTBOUND,
        channel_code="EMAIL",
        outcome_code="SEGUIMIENTO",
        result=InteractionResult.COMPLETED,
        note="Se acordó un seguimiento.",
        next_task=NextTaskSpec("Llamar nuevamente", date.today() - timedelta(days=1)),
    )
    quick_contact(
        actor=actor,
        lead=due_today,
        occurrence_date=date.today(),
        direction=InteractionDirection.OUTBOUND,
        channel_code="EMAIL",
        outcome_code="SEGUIMIENTO",
        result=InteractionResult.COMPLETED,
        note="Se envió información.",
        next_task=NextTaskSpec("Confirmar recepción", date.today()),
    )
    quick_contact(
        actor=actor,
        lead=response_lead,
        occurrence_date=date.today(),
        direction=InteractionDirection.INBOUND,
        channel_code="EMAIL",
        outcome_code="CONTACTADO",
        result=InteractionResult.RESPONSE,
        note="Respondió al correo.",
    )
    transition_lead(
        actor=actor,
        lead=stale,
        target_stage_code="EN_GESTION",
        reason="Seguimiento abierto",
        transition_fields={"next_task_reason": "Esperando información"},
    )
    stale_time = timezone.now() - timedelta(days=20)
    type(stale).objects.filter(pk=stale.pk).update(updated_at=stale_time)
    LeadAssignment.objects.filter(lead=unassigned, unassigned_at__isnull=True).update(
        unassigned_at=timezone.now()
    )

    workspace = today_workspace(actor, now=timezone.now())
    categories = [item.category for item in workspace.items]
    assert categories[:2] == ["overdue", "due_today"]
    assert {"response", "stale", "unassigned"} <= set(categories)
    assert workspace.shows_unassigned is True


@pytest.mark.django_db
def test_seller_workspace_is_scoped_and_hides_manager_only_unassigned_cards() -> None:
    seller = _manager("workspace-seller", "sales_representative")
    lead = _lead(seller, "Cuenta visible")
    LeadAssignment.objects.filter(lead=lead, unassigned_at__isnull=True).update(
        unassigned_at=timezone.now()
    )

    workspace = today_workspace(seller)
    assert workspace.items == ()
    assert workspace.shows_unassigned is False

    client = Client()
    client.force_login(seller.user)
    response = client.get("/today/")
    assert response.status_code == 200
    assert "Calidad de datos" in response.content.decode()
    assert "Cuenta visible" not in response.content.decode()


@pytest.mark.django_db
def test_today_and_lead_detail_render_plain_spanish_scoped_content() -> None:
    actor = _manager("workspace-render")
    lead = _lead(actor, "Organización Renderizada")
    client = Client()
    client.force_login(actor.user)

    today_response = client.get("/today/")
    assert today_response.status_code == 200
    today_body = today_response.content.decode()
    assert '<html lang="es-AR">' in today_body
    assert "Hoy" in today_body
    assert "SELECT" not in today_body

    detail_response = client.get(f"/leads/{lead.lead_number}/")
    assert detail_response.status_code == 200
    detail_body = detail_response.content.decode()
    assert "Organización Renderizada" in detail_body
    assert "Línea de tiempo" in detail_body
    assert f"/leads/{lead.pk}/" not in detail_body


def test_anonymous_today_redirects_to_configured_login(client: Client) -> None:
    response = client.get("/today/")

    assert response.status_code == 302
    assert response.url.startswith("/auth/local/login/")
