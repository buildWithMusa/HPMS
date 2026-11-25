
from django.contrib import admin

from .models import (
    Patient,
    PatientIdentifier,
    PatientGuardian,
)


class PatientIdentifierInline(admin.TabularInline):
    model = PatientIdentifier
    extra = 0


class PatientGuardianInline(admin.TabularInline):
    model = PatientGuardian
    extra = 0


@admin.register(Patient)
class PatientAdmin(admin.ModelAdmin):

    list_display = (
        "hospital_number",
        "first_name",
        "last_name",
        "sex",
        "phone_number",
        "is_active",
        "registered_at",
    )

    search_fields = (
        "hospital_number",
        "first_name",
        "middle_name",
        "last_name",
        "phone_number",
    )

    list_filter = (
        "sex",
        "is_active",
        "registered_at",
    )

    readonly_fields = (
        "hospital_number",
        "registered_at",
        "updated_at",
    )

    inlines = [
        PatientIdentifierInline,
        PatientGuardianInline,
    ]

    list_per_page = 25


@admin.register(PatientIdentifier)
class PatientIdentifierAdmin(admin.ModelAdmin):

    list_display = (
        "patient",
        "identifier_type",
        "is_primary",
        "created_at",
    )

    search_fields = (
        "patient__hospital_number",
        "patient__first_name",
        "patient__last_name",
    )

    list_filter = (
        "identifier_type",
        "is_primary",
    )


@admin.register(PatientGuardian)
class PatientGuardianAdmin(admin.ModelAdmin):

    list_display = (
        "full_name",
        "patient",
        "relationship",
        "phone_number",
        "is_primary",
        "is_active",
    )

    search_fields = (
        "full_name",
        "patient__hospital_number",
        "phone_number",
    )

    list_filter = (
        "relationship",
        "is_primary",
        "is_active",
    )
