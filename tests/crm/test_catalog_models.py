from importlib import import_module

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction

from simple_crm.crm.forms import CatalogChoiceField, selectable_catalog_values
from simple_crm.crm.models import (
    Campaign,
    CatalogAuditEntry,
    CatalogDeletionNotAllowed,
    Country,
    LeadStatus,
    Province,
)


@pytest.mark.django_db
def test_baseline_seed_is_idempotent_and_preserves_steward_label() -> None:
    campaign = Campaign.objects.get(code="GENERAL")
    campaign.label = "Etiqueta aprobada por administración"
    campaign.save()

    seed = import_module("simple_crm.crm.migrations.0002_seed_baseline_catalogs")
    seed.seed_baseline_catalogs(apps, None)

    assert Campaign.objects.filter(code="GENERAL").count() == 1
    assert (
        Campaign.objects.get(code="GENERAL").label
        == "Etiqueta aprobada por administración"
    )
    assert LeadStatus.objects.filter(code="NUEVO").count() == 1


@pytest.mark.django_db
def test_inactive_values_are_readable_but_not_offered_for_new_selection() -> None:
    active = LeadStatus.objects.get(code="NUEVO")
    inactive = LeadStatus.objects.get(code="EN_GESTION")
    inactive.is_active = False
    inactive.save()

    new_codes = list(
        selectable_catalog_values(LeadStatus).values_list("code", flat=True)
    )
    historical_codes = list(
        selectable_catalog_values(LeadStatus, inactive).values_list("code", flat=True)
    )
    new_field = CatalogChoiceField(LeadStatus, required=False)
    historical_field = CatalogChoiceField(LeadStatus, current=inactive, required=False)

    assert active.code in new_codes
    assert inactive.code not in new_codes
    assert inactive.code in historical_codes
    assert inactive.display_label.endswith("(inactivo)")
    assert inactive.pk not in new_field.queryset.values_list("pk", flat=True)
    assert inactive.pk in historical_field.queryset.values_list("pk", flat=True)


@pytest.mark.django_db
def test_codes_and_catalog_deletion_are_protected_and_changes_are_audited() -> None:
    user = get_user_model().objects.create_user(username="steward")
    campaign = Campaign.objects.get(code="GENERAL")
    campaign.code = "CAMBIADO"
    with pytest.raises(ValidationError, match="código estable"):
        campaign.save(actor=user)

    campaign = Campaign.objects.get(code="GENERAL")
    campaign.is_active = False
    campaign.save(actor=user)
    audit = CatalogAuditEntry.objects.filter(catalog_code="GENERAL").latest("pk")

    assert audit.action == CatalogAuditEntry.Action.DEACTIVATED
    assert audit.actor == user
    assert audit.changes["is_active"] == {"before": True, "after": False}
    assert audit.snapshot["code"] == "GENERAL"
    with pytest.raises(CatalogDeletionNotAllowed):
        campaign.delete()
    with pytest.raises(ValidationError, match="inmutable"):
        audit.save()
    with pytest.raises(CatalogDeletionNotAllowed):
        audit.delete()


@pytest.mark.django_db
def test_database_unique_and_geography_foreign_key_constraints_hold() -> None:
    country = Country.objects.get(code="AR")
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            Campaign.objects.create(code="GENERAL", label="Duplicada")
    with connection.constraint_checks_disabled():
        Province.objects.create(code="INVALIDA", label="Inválida", country_id=999999)
    with pytest.raises(IntegrityError):
        connection.check_constraints()
    Province.objects.filter(code="INVALIDA").delete()
    with transaction.atomic():
        with pytest.raises(IntegrityError):
            Province.objects.create(code="AR-OTRA", label="Córdoba", country=country)
