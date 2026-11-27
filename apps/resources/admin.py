from django.contrib import admin

from .models import Facility


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "category",
        "type",
        "location",
        "price",
        "rating",
        "availability",
    )
    list_filter = ("category", "type", "availability")
    search_fields = ("name", "description", "category", "type", "location")
    ordering = ("name",)
