"""Seed the approved controlled catalog baseline without overwriting stewardship."""

from typing import Any

from django.db import migrations


def seed_baseline_catalogs(apps: Any, schema_editor: Any) -> None:
    """Create missing stable codes only; existing labels are explicit steward data."""
    Campaign = apps.get_model("simple_crm_crm", "Campaign")
    LeadStatus = apps.get_model("simple_crm_crm", "LeadStatus")
    InteractionChannel = apps.get_model("simple_crm_crm", "InteractionChannel")
    InteractionOutcome = apps.get_model("simple_crm_crm", "InteractionOutcome")
    Specialty = apps.get_model("simple_crm_crm", "Specialty")
    Country = apps.get_model("simple_crm_crm", "Country")
    Province = apps.get_model("simple_crm_crm", "Province")
    Locality = apps.get_model("simple_crm_crm", "Locality")

    for model, values in (
        (Campaign, [{"code": "GENERAL", "label": "General", "sort_order": 10, "accepts_new_leads": True}]),
        (LeadStatus, [
            {"code": "NUEVO", "label": "Nuevo", "sort_order": 10, "is_closed": False},
            {"code": "EN_GESTION", "label": "En gestión", "sort_order": 20, "is_closed": False},
            {"code": "CERRADO", "label": "Cerrado", "sort_order": 30, "is_closed": True},
        ]),
        (InteractionChannel, [
            {"code": "TELEFONO", "label": "Teléfono", "sort_order": 10, "allows_inbound": True},
            {"code": "EMAIL", "label": "Correo electrónico", "sort_order": 20, "allows_inbound": True},
            {"code": "WHATSAPP", "label": "WhatsApp", "sort_order": 30, "allows_inbound": True},
            {"code": "WEB", "label": "Web", "sort_order": 40, "allows_inbound": False},
        ]),
        (InteractionOutcome, [
            {"code": "CONTACTADO", "label": "Contactado", "sort_order": 10, "requires_follow_up": False},
            {"code": "SIN_RESPUESTA", "label": "Sin respuesta", "sort_order": 20, "requires_follow_up": True},
            {"code": "SEGUIMIENTO", "label": "Requiere seguimiento", "sort_order": 30, "requires_follow_up": True},
        ]),
        (Specialty, [{"code": "GENERAL", "label": "General", "sort_order": 10, "is_clinical": True}]),
        (Country, [{"code": "AR", "label": "Argentina", "sort_order": 10, "is_domestic": True}]),
    ):
        for defaults in values:
            model.objects.get_or_create(code=defaults["code"], defaults=defaults)

    country = Country.objects.get(code="AR")
    province, _ = Province.objects.get_or_create(
        code="AR-CBA",
        defaults={
            "label": "Córdoba",
            "sort_order": 10,
            "country": country,
            "is_capital_region": True,
        },
    )
    Locality.objects.get_or_create(
        code="AR-CBA-CORDOBA",
        defaults={
            "label": "Córdoba",
            "sort_order": 10,
            "province": province,
            "is_capital": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [("simple_crm_crm", "0001_initial")]

    operations = [migrations.RunPython(seed_baseline_catalogs, migrations.RunPython.noop)]
