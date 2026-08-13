import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import Client
from django.urls import reverse

from simple_crm.crm.models import Campaign


@pytest.mark.django_db
def test_data_stewards_get_only_bounded_catalog_maintenance_permissions() -> None:
    group = Group.objects.get(name="Data Stewards")
    granted = set(group.permissions.values_list("codename", flat=True))
    expected = {
        f"{verb}_{model}"
        for verb in ("add", "change", "view")
        for model in (
            "campaign",
            "leadstatus",
            "interactionchannel",
            "interactionoutcome",
            "specialty",
            "country",
            "province",
            "locality",
        )
    }

    assert granted == expected
    assert not Permission.objects.filter(
        group=group, codename__startswith="delete_"
    ).exists()


@pytest.mark.django_db
def test_unauthorized_admin_requests_cannot_create_or_change_catalogs(
    client: Client,
) -> None:
    user = get_user_model().objects.create_user(
        username="unauthorized", password="safe-password"
    )
    user.is_staff = True
    user.save()
    campaign = Campaign.objects.get(code="GENERAL")
    original_label = campaign.label

    client.force_login(user)
    add_response = client.post(
        reverse("admin:simple_crm_crm_campaign_add"),
        {"code": "NO_AUTORIZADA", "label": "No autorizada", "sort_order": 1},
    )
    change_response = client.post(
        reverse("admin:simple_crm_crm_campaign_change", args=[campaign.pk]),
        {
            "code": "CAMBIO_FORZADO",
            "label": "Cambio forzado",
            "sort_order": 1,
            "is_active": "on",
        },
    )

    assert add_response.status_code == 403
    assert change_response.status_code == 403
    assert not Campaign.objects.filter(code="NO_AUTORIZADA").exists()
    campaign.refresh_from_db()
    assert campaign.code == "GENERAL"
    assert campaign.label == original_label


@pytest.mark.django_db
def test_steward_cannot_mutate_code_through_crafted_admin_post(client: Client) -> None:
    user = get_user_model().objects.create_user(
        username="steward", password="safe-password", is_staff=True
    )
    user.groups.add(Group.objects.get(name="Data Stewards"))
    campaign = Campaign.objects.get(code="GENERAL")

    client.force_login(user)
    response = client.post(
        reverse("admin:simple_crm_crm_campaign_change", args=[campaign.pk]),
        {
            "code": "CAMBIO_FORZADO",
            "label": "Etiqueta editada",
            "sort_order": 4,
            "is_active": "on",
            "accepts_new_leads": "on",
        },
    )

    assert response.status_code == 302
    campaign.refresh_from_db()
    assert campaign.code == "GENERAL"
    assert campaign.label == "Etiqueta editada"
