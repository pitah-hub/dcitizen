from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ("email",)
    list_display = ("email", "full_name", "national_id", "phone", "is_staff", "posting_suspended")
    list_filter = ("is_staff", "posting_suspended")
    search_fields = ("email", "full_name", "national_id")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Personal info", {"fields": ("full_name", "national_id", "phone")}),
        ("Moderation", {"fields": ("posting_suspended", "suspension_reason")}),
        (
            "Permissions",
            {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")},
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email", "full_name", "national_id", "phone",
                    "password1", "password2", "is_staff",
                ),
            },
        ),
    )
