from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .forms import UserChangeForm, UserCreationForm
from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm

    list_display = (
        "phone_e164",
        "nick_name",
        "is_staff",
        "is_active",
        "created_at",
    )
    list_filter = ("is_staff", "is_active", "is_superuser", "groups")
    search_fields = ("phone_e164", "nick_name")
    ordering = ("phone_e164",)
    readonly_fields = ("id", "created_at", "updated_at", "last_login")

    fieldsets = (
        (None, {"fields": ("id", "phone_e164", "password")}),
        ("Profile", {"fields": ("nick_name", "avatar")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "created_at", "updated_at")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("phone_e164", "nick_name", "password1", "password2"),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")
