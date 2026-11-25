from django.contrib import admin
from .models import Prescription, PrescriptionLine


class PrescriptionLineInline(admin.TabularInline):
    model = PrescriptionLine
    extra = 0
    readonly_fields = ("created_at",)


@admin.register(Prescription)
class PrescriptionAdmin(admin.ModelAdmin):
    list_display = (
        "prescription_number",
        "patient",
        "source",
        "status",
        "recorded_by",
        "verified_by",
        "created_at",
    )
    list_filter = ("source", "status", "created_at")
    search_fields = (
        "prescription_number",
        "patient__hospital_number",
        "patient__first_name",
        "patient__last_name",
    )
    readonly_fields = (
        "prescription_number",
        "submitted_at",
        "verified_at",
        "rejected_at",
        "created_at",
        "updated_at",
    )
    inlines = [PrescriptionLineInline]


@admin.register(PrescriptionLine)
class PrescriptionLineAdmin(admin.ModelAdmin):
    list_display = (
        "prescription",
        "medicine",
        "dose",
        "frequency",
        "duration_days",
        "quantity",
    )
    search_fields = (
        "prescription__prescription_number",
        "medicine__generic_name",
    )
