from django.contrib.auth.models import Group
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User
from .forms import (
    HPMSUserCreationForm,
    HPMSUserChangeForm, 
)


@admin.register(User)
class HPMSUserAdmin(UserAdmin):
    



    form = HPMSUserChangeForm
    add_form = HPMSUserCreationForm

    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "is_superuser",
    )

    list_filter = (
        "is_staff",
        "is_active",
        "is_superuser",
        "groups",
    )

    search_fields = (
        "email",
        "first_name",
        "last_name",
    )

    ordering = ("email",)

    fieldsets = (
        (
            "Account Information",
            {
                "fields": (
                    "email",
                    "password",
                )
            },
        ),
        (
            "Personal Information",
            {
                "fields": (
                    "first_name",
                    "last_name",
                )
            },
        ),
        (
            "Access Control",
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
        (
            "Account Dates",
            {
                "fields": (
                    "last_login",
                    "date_joined",
                )
            },
        ),
    )

    add_fieldsets = (
        (
            "Register Hospital Staff",
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "password1",
                    "password2",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )

    filter_horizontal = (
        "groups",
        "user_permissions",
    )
    # Register Django Groups for HPMS role management

admin.site.unregister(Group)


@admin.register(Group)
class HPMSGroupAdmin(admin.ModelAdmin):

    list_display = ("name",)

    search_fields = ("name",)

    filter_horizontal = ("permissions",)


# HPMS Administration Branding

admin.site.site_header = "HPMS Administration"
admin.site.site_title = "Hospital Pharmacy Management"
admin.site.index_title = "Hospital Pharmacy Management System"
