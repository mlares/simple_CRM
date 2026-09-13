"""Reusable catalog selections that preserve historical inactive values."""

from __future__ import annotations

from typing import Any, TypeVar, cast

from django import forms
from django.db.models import Q, QuerySet

from .models import CatalogBase

CatalogType = TypeVar("CatalogType", bound=CatalogBase)


def selectable_catalog_values(
    model: type[CatalogType], current: CatalogType | None = None
) -> QuerySet[CatalogType]:
    """Offer active values, plus the current inactive one for historical forms."""
    allowed = Q(is_active=True)
    if current is not None and current.pk is not None:
        allowed |= Q(pk=current.pk)
    return (
        cast(Any, model).objects.filter(allowed).order_by("sort_order", "label", "code")
    )


class CatalogChoiceField(forms.ModelChoiceField):
    """A model choice field with the catalog activation policy built in."""

    def __init__(
        self,
        catalog_model: type[CatalogType],
        *,
        current: CatalogType | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(
            queryset=selectable_catalog_values(catalog_model, current),
            **cast(Any, kwargs),
        )
