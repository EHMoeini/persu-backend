from django.contrib import admin

from .models import Facility


@admin.register(Facility)
class FacilityAdmin(admin.ModelAdmin):
    list_display = ("name", "type", "location")
    list_filter = ("type",)
    search_fields = ("name", "type", "location")
    ordering = ("name",)
