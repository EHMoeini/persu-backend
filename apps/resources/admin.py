from django.contrib import admin

from .models import Facility


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "type",
        "city",
        "price",
        "rating",
        "availability",
        "source_name",
    )
    list_filter = ("category", "type", "availability", "province", "source_name")
    search_fields = ("name", "description", "category", "type", "location", "city", "address", "phone")
    ordering = ("name",)
