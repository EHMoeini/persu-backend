from __future__ import annotations

import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _


class Facility(models.Model):
    """A venue users can search for, such as a soccer field or pool."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(_("name"), max_length=255)
    type = models.CharField(_("type"), max_length=100, blank=True, default="")
    location = models.CharField(_("location"), max_length=255, blank=True, default="")

    class Meta:
        db_table = "facilities"
        verbose_name = _("facility")
        verbose_name_plural = _("facilities")
        ordering = ("name",)

    def __str__(self) -> str:
        return self.name
