import pytest
from django.contrib.auth import get_user_model
from django.test import Client

from simple_crm.crm.lead_services import create_lead
from simple_crm.crm.models import Campaign, LeadPartyRole
from simple_crm.crm.services import create_organization_party
from simple_crm.identity.models import (
    IdentityProfile,
    Role,
    RoleAssignment,
    ScopeGrant,
    ScopeType,
)


@pytest.mark.django_db
def test_segments_page_renders_business_labels_and_reset_control() -> None:
    user = get_user_model().objects.create_user(
        username="segments-page", password="safe-pass"
    )
    profile = IdentityProfile.objects.get(user=user)
    RoleAssignment.objects.create(
        identity=profile, role=Role.objects.get(code="sales_manager")
    )
    campaign = Campaign.objects.get(code="GENERAL")
    ScopeGrant.objects.create(
        identity=profile, scope_type=ScopeType.CAMPAIGN, campaign=campaign
    )
    party, _ = create_organization_party(display_name="Segmento visible")
    lead, _ = create_lead(
        actor=profile,
        campaign=campaign,
        owner=profile,
        parties=((party, LeadPartyRole.ACCOUNT),),
    )

    client = Client()
    client.force_login(user)
    response = client.get("/segmentos/?stage=NUEVO")

    assert response.status_code == 200
    body = response.content.decode()
    assert "Segmentos" in body
    assert "Etapa" in body
    assert "Restablecer" in body
    assert lead.lead_number in body
    assert "current_stage__code" not in body
    assert "SELECT" not in body


def test_anonymous_segments_redirects_to_configured_login(client: Client) -> None:
    response = client.get("/segmentos/")

    assert response.status_code == 302
    assert response.url.startswith("/auth/local/login/")
