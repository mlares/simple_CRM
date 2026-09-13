"""Controlled, durable reference catalogs owned by the CRM app."""

from __future__ import annotations

from typing import Any, cast

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from .normalization import comparison_key, normalize_contact_value


class CatalogDeletionNotAllowed(ValidationError):
    """Raised when code attempts to remove historical reference data."""


class CatalogBase(models.Model):
    """Common stable-code behavior for all controlled catalogs.

    Labels and ordering are deliberately steward-maintained.  Codes are machine
    identifiers: they are created once and never change, preserving references
    made by later owning domain records.
    """

    code = models.CharField(max_length=40, unique=True)
    label = models.CharField(max_length=120)
    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ("sort_order", "label", "code")
        constraints = [
            models.CheckConstraint(
                condition=Q(code__gt=""),
                name="%(app_label)s_%(class)s_code_not_empty",
            ),
            models.CheckConstraint(
                condition=Q(label__gt=""),
                name="%(app_label)s_%(class)s_label_not_empty",
            ),
        ]

    def __str__(self) -> str:
        suffix = " (inactivo)" if not self.is_active else ""
        return f"{self.label}{suffix}"

    @property
    def display_label(self) -> str:
        """Return a readable value even when it is no longer selectable."""
        return str(self)

    def _snapshot(self) -> dict[str, Any]:
        values: dict[str, Any] = {}
        for field in self._meta.concrete_fields:
            value = getattr(self, field.attname)
            values[field.name] = (
                value.isoformat() if hasattr(value, "isoformat") else value
            )
        return values

    def _validate_immutable_code(self) -> None:
        if not self.pk:
            return
        original_code = (
            cast(Any, type(self))
            .objects.filter(pk=self.pk)
            .values_list("code", flat=True)
            .first()
        )
        if original_code is not None and original_code != self.code:
            raise ValidationError({"code": "El código estable no puede modificarse."})

    def save(
        self, *args: Any, actor: models.Model | None = None, **kwargs: Any
    ) -> None:
        self._validate_immutable_code()
        old_snapshot: dict[str, Any] | None = None
        if self.pk:
            original = cast(Any, type(self)).objects.filter(pk=self.pk).first()
            if original is not None:
                old_snapshot = original._snapshot()
        super().save(*args, **kwargs)
        new_snapshot = self._snapshot()
        if old_snapshot is None:
            CatalogAuditEntry.record(self, "created", actor, {}, new_snapshot)
        elif old_snapshot != new_snapshot:
            action = "deactivated" if not self.is_active else "updated"
            if not old_snapshot["is_active"] and self.is_active:
                action = "activated"
            changed = {
                key: {"before": old_snapshot.get(key), "after": value}
                for key, value in new_snapshot.items()
                if old_snapshot.get(key) != value
            }
            CatalogAuditEntry.record(self, action, actor, changed, new_snapshot)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise CatalogDeletionNotAllowed("Los catálogos no se eliminan; desactívelos.")


class Campaign(CatalogBase):
    accepts_new_leads = models.BooleanField(default=True)

    class Meta(CatalogBase.Meta):
        verbose_name = "Campaña"
        verbose_name_plural = "Campañas"


class LeadStatus(CatalogBase):
    is_closed = models.BooleanField(default=False)

    class Meta(CatalogBase.Meta):
        verbose_name = "Estado de lead"
        verbose_name_plural = "Estados de lead"


class InteractionChannel(CatalogBase):
    allows_inbound = models.BooleanField(default=True)

    class Meta(CatalogBase.Meta):
        verbose_name = "Canal de interacción"
        verbose_name_plural = "Canales de interacción"


class InteractionOutcome(CatalogBase):
    requires_follow_up = models.BooleanField(default=False)

    class Meta(CatalogBase.Meta):
        verbose_name = "Resultado de interacción"
        verbose_name_plural = "Resultados de interacción"


class Specialty(CatalogBase):
    is_clinical = models.BooleanField(default=True)

    class Meta(CatalogBase.Meta):
        verbose_name = "Especialidad"
        verbose_name_plural = "Especialidades"


class Country(CatalogBase):
    is_domestic = models.BooleanField(default=False)

    class Meta(CatalogBase.Meta):
        verbose_name = "País"
        verbose_name_plural = "Países"


class Province(CatalogBase):
    country = models.ForeignKey(
        Country, on_delete=models.PROTECT, related_name="provinces"
    )
    is_capital_region = models.BooleanField(default=False)

    class Meta(CatalogBase.Meta):
        verbose_name = "Provincia"
        verbose_name_plural = "Provincias"
        constraints = [
            *CatalogBase.Meta.constraints,
            models.UniqueConstraint(
                fields=("country", "label"), name="crm_province_country_label_unique"
            ),
        ]


class Locality(CatalogBase):
    province = models.ForeignKey(
        Province, on_delete=models.PROTECT, related_name="localities"
    )
    is_capital = models.BooleanField(default=False)

    class Meta(CatalogBase.Meta):
        verbose_name = "Localidad"
        verbose_name_plural = "Localidades"
        constraints = [
            *CatalogBase.Meta.constraints,
            models.UniqueConstraint(
                fields=("province", "label"), name="crm_locality_province_label_unique"
            ),
        ]


class CatalogAuditEntry(models.Model):
    """Append-only evidence for catalog creation and stewardship changes."""

    class Action(models.TextChoices):
        CREATED = "created", "Creado"
        UPDATED = "updated", "Actualizado"
        ACTIVATED = "activated", "Activado"
        DEACTIVATED = "deactivated", "Desactivado"

    catalog_model = models.CharField(max_length=80)
    catalog_code = models.CharField(max_length=40)
    action = models.CharField(max_length=16, choices=Action.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="catalog_audit_entries",
    )
    changes = models.JSONField(default=dict)
    snapshot = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "Auditoría de catálogo"
        verbose_name_plural = "Auditoría de catálogos"
        indexes = [models.Index(fields=("catalog_model", "catalog_code"))]

    @classmethod
    def record(
        cls,
        catalog: CatalogBase,
        action: str,
        actor: models.Model | None,
        changes: dict[str, Any],
        snapshot: dict[str, Any],
    ) -> None:
        cls.objects.create(
            catalog_model=catalog._meta.label_lower,
            catalog_code=catalog.code,
            action=action,
            actor=actor if getattr(actor, "pk", None) else None,
            changes=changes,
            snapshot=snapshot,
        )

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            raise ValidationError("La auditoría de catálogos es inmutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise CatalogDeletionNotAllowed("La auditoría de catálogos es inmutable.")


class PartyConcurrencyError(ValidationError):
    """Raised when a stale party edit would overwrite a newer version."""


class PartyDeletionNotAllowed(ValidationError):
    """Parties are archived so source evidence and relationships remain."""


class PartyType(models.TextChoices):
    PERSON = "PERSON", "Persona"
    ORGANIZATION = "ORGANIZATION", "Organización"


class PartyLifecycle(models.TextChoices):
    ACTIVE = "ACTIVE", "Activo"
    ARCHIVED = "ARCHIVED", "Archivado"


class DataReadiness(models.TextChoices):
    UNREVIEWED = "UNREVIEWED", "Sin revisar"
    NEEDS_RESEARCH = "NEEDS_RESEARCH", "Requiere investigación"
    CONTACTABLE = "CONTACTABLE", "Contactable"
    VERIFIED = "VERIFIED", "Verificado"


class ContactKind(models.TextChoices):
    EMAIL = "EMAIL", "Correo electrónico"
    PHONE = "PHONE", "Teléfono"
    WHATSAPP = "WHATSAPP", "WhatsApp"
    WEBSITE = "WEBSITE", "Sitio web"
    SOCIAL = "SOCIAL", "Red social"


class ContactQuality(models.TextChoices):
    UNREVIEWED = "UNREVIEWED", "Sin revisar"
    VALID = "VALID", "Válido"
    INVALID = "INVALID", "Inválido"
    AMBIGUOUS = "AMBIGUOUS", "Ambiguo"


class PartyManager(models.Manager["Party"]):
    def active(self) -> models.QuerySet["Party"]:
        return self.get_queryset().filter(lifecycle=PartyLifecycle.ACTIVE)


class Person(models.Model):
    honorific = models.CharField(max_length=40, blank=True)
    given_names = models.CharField(max_length=160, blank=True)
    family_names = models.CharField(max_length=160, blank=True)

    class Meta:
        verbose_name = "Persona"
        verbose_name_plural = "Personas"

    def __str__(self) -> str:
        return " ".join(part for part in (self.given_names, self.family_names) if part)


class Organization(models.Model):
    legal_name = models.CharField(max_length=240, blank=True)
    organization_type = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Organización"
        verbose_name_plural = "Organizaciones"

    def __str__(self) -> str:
        return self.legal_name or "Organización sin razón social"


class Party(models.Model):
    party_type = models.CharField(max_length=16, choices=PartyType.choices)
    display_name = models.CharField(max_length=240)
    canonical_name = models.CharField(max_length=240, db_index=True)
    data_readiness = models.CharField(
        max_length=20, choices=DataReadiness.choices, default=DataReadiness.UNREVIEWED
    )
    lifecycle = models.CharField(
        max_length=16, choices=PartyLifecycle.choices, default=PartyLifecycle.ACTIVE
    )
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    person = models.OneToOneField(
        Person,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="party",
    )
    organization = models.OneToOneField(
        Organization,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="party",
    )

    objects = PartyManager()

    class Meta:
        ordering = ("canonical_name", "pk")
        verbose_name = "Parte"
        verbose_name_plural = "Partes"
        constraints = [
            models.CheckConstraint(
                condition=(
                    Q(
                        party_type=PartyType.PERSON,
                        person__isnull=False,
                        organization__isnull=True,
                    )
                    | Q(
                        party_type=PartyType.ORGANIZATION,
                        person__isnull=True,
                        organization__isnull=False,
                    )
                ),
                name="crm_party_exactly_one_subtype",
            ),
            models.CheckConstraint(
                condition=Q(display_name__gt="") & Q(canonical_name__gt=""),
                name="crm_party_names_not_empty",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            current = type(self).objects.get(pk=self.pk)
            if self.version != current.version:
                raise PartyConcurrencyError(
                    "El registro cambió; recargue la parte antes de guardar."
                )
            self.version += 1
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"version", "updated_at"}
        super().save(*args, **kwargs)

    def archive(self, *, expected_version: int | None = None) -> None:
        if expected_version is not None and expected_version != self.version:
            raise PartyConcurrencyError(
                "El registro cambió; recargue la parte antes de archivarla."
            )
        self.lifecycle = PartyLifecycle.ARCHIVED
        self.save(update_fields=("lifecycle",))

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise PartyDeletionNotAllowed("Las partes se archivan; no se eliminan.")

    def __str__(self) -> str:
        return self.display_name


class OrganizationPerson(models.Model):
    organization = models.ForeignKey(
        Party, on_delete=models.PROTECT, related_name="organization_relationships"
    )
    person = models.ForeignKey(
        Party, on_delete=models.PROTECT, related_name="organization_affiliations"
    )
    relationship_type = models.CharField(max_length=60, default="AFFILIATED")
    role_title = models.CharField(max_length=160, blank=True)
    area_title = models.CharField(max_length=160, blank=True)
    valid_from = models.DateField(null=True, blank=True)
    valid_to = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("organization", "person", "relationship_type"),
                name="crm_organization_person_unique",
            ),
            models.CheckConstraint(
                condition=Q(valid_to__isnull=True)
                | Q(valid_from__isnull=True)
                | Q(valid_to__gte=F("valid_from")),
                name="crm_organization_person_dates_valid",
            ),
            models.CheckConstraint(
                condition=~Q(organization=F("person")),
                name="crm_organization_person_distinct",
            ),
        ]
        verbose_name = "Relación organización-persona"
        verbose_name_plural = "Relaciones organización-persona"

    def clean(self) -> None:
        super().clean()
        if self.organization_id == self.person_id:
            raise ValidationError("La organización y la persona deben ser distintas.")
        if self.organization_id:
            organization = Party.objects.get(pk=self.organization_id)
            if organization.party_type != PartyType.ORGANIZATION:
                raise ValidationError({"organization": "Debe ser una organización."})
        if self.person_id:
            person = Party.objects.get(pk=self.person_id)
            if person.party_type != PartyType.PERSON:
                raise ValidationError({"person": "Debe ser una persona."})

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)


class PartySpecialty(models.Model):
    party = models.ForeignKey(
        Party, on_delete=models.PROTECT, related_name="specialties"
    )
    specialty = models.ForeignKey(
        Specialty, on_delete=models.PROTECT, related_name="party_links"
    )
    raw_label = models.CharField(max_length=160, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("party", "specialty"), name="crm_party_specialty_unique"
            )
        ]
        verbose_name = "Especialidad de parte"
        verbose_name_plural = "Especialidades de partes"


class ContactPoint(models.Model):
    kind = models.CharField(max_length=16, choices=ContactKind.choices)
    platform = models.CharField(max_length=80, blank=True)
    raw_value = models.CharField(max_length=500)
    normalized_value = models.CharField(
        max_length=500, null=True, blank=True, db_index=True
    )
    phone_extension = models.CharField(max_length=20, blank=True)
    quality_state = models.CharField(
        max_length=16,
        choices=ContactQuality.choices,
        default=ContactQuality.UNREVIEWED,
    )
    is_active = models.BooleanField(default=True)
    is_suppressed = models.BooleanField(default=False)
    suppression_reason = models.CharField(max_length=300, blank=True)
    provenance = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=("kind", "normalized_value"))]
        constraints = [
            models.CheckConstraint(
                condition=Q(raw_value__gt=""), name="crm_contact_raw_not_empty"
            ),
            models.CheckConstraint(
                condition=Q(is_suppressed=False) | Q(suppression_reason__gt=""),
                name="crm_contact_suppression_reason_required",
            ),
        ]
        verbose_name = "Punto de contacto"
        verbose_name_plural = "Puntos de contacto"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            current = type(self).objects.get(pk=self.pk)
            if current.is_suppressed and not self.is_suppressed:
                raise ValidationError(
                    "Un punto de contacto suprimido no puede reactivarse desde este flujo."
                )
        self.normalized_value, self.quality_state = normalize_contact_value(
            self.kind, self.raw_value
        )
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {
                "normalized_value",
                "quality_state",
                "updated_at",
            }
        super().save(*args, **kwargs)

    @classmethod
    def selectable_for_outreach(cls) -> models.QuerySet["ContactPoint"]:
        return cls.objects.filter(
            is_active=True,
            is_suppressed=False,
            quality_state=ContactQuality.VALID,
        )

    def suppress(self, reason: str) -> None:
        if not reason.strip():
            raise ValidationError("La supresión requiere un motivo.")
        self.is_suppressed = True
        self.suppression_reason = reason.strip()
        self.save(update_fields=("is_suppressed", "suppression_reason"))


class PartyContactPoint(models.Model):
    party = models.ForeignKey(
        Party, on_delete=models.PROTECT, related_name="contact_point_links"
    )
    contact_point = models.ForeignKey(
        ContactPoint, on_delete=models.PROTECT, related_name="party_links"
    )
    purpose = models.CharField(max_length=100, blank=True)
    is_primary = models.BooleanField(default=False)
    is_verified = models.BooleanField(default=False)
    verification_note = models.CharField(max_length=300, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("party", "contact_point"), name="crm_party_contact_point_unique"
            )
        ]
        verbose_name = "Contacto de parte"
        verbose_name_plural = "Contactos de partes"


class Address(models.Model):
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name="addresses")
    address_line = models.CharField(max_length=300, blank=True)
    country = models.ForeignKey(
        Country,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="party_addresses",
    )
    province = models.ForeignKey(
        Province,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="party_addresses",
    )
    locality = models.ForeignKey(
        Locality,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="party_addresses",
    )
    sales_region = models.CharField(max_length=120, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Domicilio"
        verbose_name_plural = "Domicilios"

    def clean(self) -> None:
        super().clean()
        if self.province_id and self.country_id:
            province = Province.objects.get(pk=self.province_id)
            if province.country_id != self.country_id:
                raise ValidationError(
                    {"province": "La provincia no pertenece al país."}
                )
        if self.locality_id and self.province_id:
            locality = Locality.objects.get(pk=self.locality_id)
            if locality.province_id != self.province_id:
                raise ValidationError(
                    {"locality": "La localidad no pertenece a la provincia."}
                )

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.full_clean()
        super().save(*args, **kwargs)


class PartyAlias(models.Model):
    party = models.ForeignKey(Party, on_delete=models.PROTECT, related_name="aliases")
    alias_value = models.CharField(max_length=240)
    alias_normalized = models.CharField(max_length=240)
    alias_type = models.CharField(max_length=60, default="SOURCE_NAME")
    provenance = models.JSONField(default=dict)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("party", "alias_normalized", "alias_type"),
                name="crm_party_alias_unique",
            )
        ]
        indexes = [models.Index(fields=("alias_normalized",))]
        verbose_name = "Alias de parte"
        verbose_name_plural = "Aliases de partes"

    def save(self, *args: Any, **kwargs: Any) -> None:
        self.alias_normalized = comparison_key(self.alias_value)
        super().save(*args, **kwargs)


class LeadConcurrencyError(ValidationError):
    """Raised when a stale lead edit would overwrite a newer version."""


class LeadDeletionNotAllowed(ValidationError):
    """Leads are archived instead of destructively deleted."""


class LeadLifecycle(models.TextChoices):
    ACTIVE = "ACTIVE", "Activo"
    ARCHIVED = "ARCHIVED", "Archivado"


class LeadPartyRole(models.TextChoices):
    ACCOUNT = "ACCOUNT", "Cuenta"
    PRIMARY_CONTACT = "PRIMARY_CONTACT", "Contacto principal"
    SECONDARY_CONTACT = "SECONDARY_CONTACT", "Contacto secundario"
    SECRETARY = "SECRETARY", "Secretaría"
    OTHER = "OTHER", "Otro"


class AssignmentRole(models.TextChoices):
    PRIMARY = "PRIMARY", "Principal"
    SECONDARY = "SECONDARY", "Secundario"


class LeadManager(models.Manager["Lead"]):
    def active(self) -> models.QuerySet["Lead"]:
        return self.get_queryset().filter(lifecycle=LeadLifecycle.ACTIVE)


class Lead(models.Model):
    lead_number = models.CharField(max_length=24, unique=True, blank=True, null=True)
    campaign = models.ForeignKey(
        Campaign, on_delete=models.PROTECT, related_name="leads"
    )
    team = models.ForeignKey(
        "simple_crm_identity.Team",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="leads",
    )
    current_stage = models.ForeignKey(
        LeadStatus, on_delete=models.PROTECT, related_name="current_leads"
    )
    data_readiness = models.CharField(
        max_length=20, choices=DataReadiness.choices, default=DataReadiness.UNREVIEWED
    )
    lifecycle = models.CharField(
        max_length=16, choices=LeadLifecycle.choices, default=LeadLifecycle.ACTIVE
    )
    source_attribution = models.JSONField(default=dict)
    next_task_description = models.CharField(max_length=300, blank=True)
    next_task_due_at = models.DateTimeField(null=True, blank=True)
    next_task_reason = models.CharField(max_length=500, blank=True)
    version = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = LeadManager()

    class Meta:
        ordering = ("-created_at", "-pk")
        verbose_name = "Lead"
        verbose_name_plural = "Leads"
        constraints = [
            models.CheckConstraint(
                condition=Q(lead_number__gt=""), name="crm_lead_number_not_empty"
            ),
            models.CheckConstraint(
                condition=(
                    Q(next_task_description__gt="", next_task_due_at__isnull=False)
                    | Q(next_task_reason__gt="")
                    | (
                        Q(next_task_description="")
                        & Q(next_task_due_at__isnull=True)
                        & Q(next_task_reason="")
                    )
                ),
                name="crm_lead_next_action_shape_valid",
            ),
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            current = type(self).objects.get(pk=self.pk)
            if self.version != current.version:
                raise LeadConcurrencyError(
                    "El lead cambió; recárguelo antes de guardar."
                )
            self.version += 1
            update_fields = kwargs.get("update_fields")
            if update_fields is not None:
                kwargs["update_fields"] = set(update_fields) | {"version", "updated_at"}
        super().save(*args, **kwargs)
        if not self.lead_number:
            self.lead_number = f"LEAD-{self.pk:06d}"
            super().save(update_fields=("lead_number",))

    @property
    def has_next_action(self) -> bool:
        return bool(
            (self.next_task_description.strip() and self.next_task_due_at)
            or self.next_task_reason.strip()
        )

    def archive(self, *, expected_version: int | None = None) -> None:
        if expected_version is not None and expected_version != self.version:
            raise LeadConcurrencyError(
                "El lead cambió; recárguelo antes de archivarlo."
            )
        self.lifecycle = LeadLifecycle.ARCHIVED
        self.save(update_fields=("lifecycle",))

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise LeadDeletionNotAllowed("Los leads se archivan; no se eliminan.")

    def __str__(self) -> str:
        return self.lead_number or f"Lead {self.pk}"


class LeadParty(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name="party_links")
    party = models.ForeignKey(
        Party, on_delete=models.PROTECT, related_name="lead_links"
    )
    party_role = models.CharField(max_length=24, choices=LeadPartyRole.choices)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("lead", "party", "party_role"), name="crm_lead_party_unique"
            ),
            models.UniqueConstraint(
                fields=("lead",),
                condition=Q(party_role=LeadPartyRole.ACCOUNT),
                name="crm_one_account_per_lead",
            ),
            models.UniqueConstraint(
                fields=("lead",),
                condition=Q(party_role=LeadPartyRole.PRIMARY_CONTACT),
                name="crm_one_primary_contact_per_lead",
            ),
        ]
        verbose_name = "Parte del lead"
        verbose_name_plural = "Partes de los leads"


class LeadAssignment(models.Model):
    lead = models.ForeignKey(Lead, on_delete=models.PROTECT, related_name="assignments")
    identity = models.ForeignKey(
        "simple_crm_identity.IdentityProfile",
        on_delete=models.PROTECT,
        related_name="lead_assignments",
    )
    assignment_role = models.CharField(max_length=12, choices=AssignmentRole.choices)
    assigned_at = models.DateTimeField(default=timezone.now)
    unassigned_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="lead_assignments_made",
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(unassigned_at__isnull=True)
                | Q(unassigned_at__gte=F("assigned_at")),
                name="crm_lead_assignment_dates_valid",
            ),
            models.UniqueConstraint(
                fields=("lead", "assignment_role"),
                condition=Q(unassigned_at__isnull=True),
                name="crm_active_lead_assignment_unique",
            ),
        ]
        verbose_name = "Asignación de lead"
        verbose_name_plural = "Asignaciones de leads"


class LeadStageHistory(models.Model):
    lead = models.ForeignKey(
        Lead, on_delete=models.PROTECT, related_name="stage_history"
    )
    from_stage = models.ForeignKey(
        LeadStatus,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="stage_history_from",
    )
    to_stage = models.ForeignKey(
        LeadStatus, on_delete=models.PROTECT, related_name="stage_history_to"
    )
    occurred_at = models.DateTimeField(default=timezone.now)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="lead_stage_changes",
    )
    reason = models.CharField(max_length=500, blank=True)
    transition_fields = models.JSONField(default=dict)

    class Meta:
        ordering = ("occurred_at", "pk")
        verbose_name = "Historial de etapa"
        verbose_name_plural = "Historial de etapas"

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk:
            raise ValidationError("El historial de etapas es inmutable.")
        super().save(*args, **kwargs)

    def delete(self, *args: Any, **kwargs: Any) -> tuple[int, dict[str, int]]:
        raise ValidationError("El historial de etapas es inmutable.")
