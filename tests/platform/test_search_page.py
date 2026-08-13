import pytest
from django.contrib.auth import get_user_model
from django.test import Client

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


@pytest.mark.django_db
def test_search_page_renders_reason_and_permission_checked_link() -> None:
    user = get_user_model().objects.create_user(
        username="search-page", password="safe-pass"
    )
    profile = IdentityProfile.objects.get(user=user)
    RoleAssignment.objects.create(
        identity=profile, role=Role.objects.get(code="sales_manager")
    )
    campaign = Campaign.objects.get(code="GENERAL")
    ScopeGrant.objects.create(
        identity=profile, scope_type=ScopeType.CAMPAIGN, campaign=campaign
    )
    party, _ = create_organization_party(
        display_name="Organización Navegable",
        contact_inputs=(
            ContactInput(kind=ContactKind.EMAIL, raw_value="navegable@example.com"),
        ),
    )
    lead, _ = create_lead(
        actor=profile,
        campaign=campaign,
        owner=profile,
        parties=((party, LeadPartyRole.ACCOUNT),),
    )

    client = Client()
    client.force_login(user)
    response = client.get("/buscar/?q=navegable@example.com")

    assert response.status_code == 200
    body = response.content.decode()
    assert "Organización Navegable" in body
    assert "Correo o teléfono exacto" in body
    assert f"/leads/{lead.lead_number}/" in body
    assert "SELECT" not in body


def test_anonymous_search_redirects_to_configured_login(client: Client) -> None:
    response = client.get("/buscar/?q=algo")

    assert response.status_code == 302
    assert response.url.startswith("/auth/local/login/")
