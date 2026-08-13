from datetime import date

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
def test_reports_page_renders_governed_metadata_and_business_labels() -> None:
    user = get_user_model().objects.create_user(
        username="reports-page", password="safe-pass"
    )
    profile = IdentityProfile.objects.get(user=user)
    RoleAssignment.objects.create(
        identity=profile, role=Role.objects.get(code="sales_manager")
    )
    campaign = Campaign.objects.get(code="GENERAL")
    ScopeGrant.objects.create(
        identity=profile, scope_type=ScopeType.CAMPAIGN, campaign=campaign
    )
    party, _ = create_organization_party(display_name="Reporte visible")
    create_lead(
        actor=profile,
        campaign=campaign,
        owner=profile,
        parties=((party, LeadPartyRole.ACCOUNT),),
    )

    client = Client()
    client.force_login(user)
    response = client.get(
        f"/informes/?from={date.today().isoformat()}&to={date.today().isoformat()}"
    )

    assert response.status_code == 200
    body = response.content.decode()
    assert "Informes" in body
    assert "Período" in body
    assert "Alcance autorizado actual" in body
    assert "Lead contactable" in body
    assert "v1" in body
    assert "current_stage__code" not in body
    assert "SELECT" not in body


def test_anonymous_reports_redirects_to_configured_login(client: Client) -> None:
    response = client.get("/informes/")

    assert response.status_code == 302
    assert response.url.startswith("/auth/local/login/")
