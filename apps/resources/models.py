from __future__ import annotations

import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _


class Facility(models.Model):
    """A venue users can search for, such as a soccer field or pool."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("name"), max_length=255)
    description = models.TextField(_("description"), blank=True, default="")
    category = models.CharField(
        _("category"), max_length=100, blank=True, default=""
    )
    type = models.CharField(_("type"), max_length=100, blank=True, default="")
    location = models.CharField(_("location"), max_length=255, blank=True, default="")
    price = models.DecimalField(
        _("price"),
        max_digits=12,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
        help_text=_("Price per booking."),
    )
    picture = models.URLField(_("picture"), max_length=500, blank=True, default="")
    rating = models.DecimalField(
        _("rating"),
        max_digits=2,
        decimal_places=1,
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    availability = models.BooleanField(_("availability"), default=True)

    class Meta:
        db_table = "facilities"
        verbose_name = _("facility")
        verbose_name_plural = _("facilities")
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name
