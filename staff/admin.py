
from django.contrib import admin

from .models import StaffProfile, StaffAssignment


class StaffAssignmentInline(admin.TabularInline):
    model = StaffAssignment
    extra = 1


@admin.register(StaffProfile)
class StaffProfileAdmin(admin.ModelAdmin):

    list_display = (
        "staff_number",
        "first_name",
        "last_name",
        "job_title",
        "employment_status",
        "user",
    )

    list_filter = (
        "employment_status",
    )

    search_fields = (
        "staff_number",
        "first_name",
        "last_name",
        "user__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )

    inlines = [
        StaffAssignmentInline,
    ]


@admin.register(StaffAssignment)
class StaffAssignmentAdmin(admin.ModelAdmin):

    list_display = (
        "staff",
        "department",
        "service_area",
        "is_primary",
        "start_date",
        "end_date",
        "is_active",
    )

    list_filter = (
        "department",
        "is_primary",
        "is_active",
    )

    search_fields = (
        "staff__staff_number",
        "staff__first_name",
        "staff__last_name",
        "department__name",
    )

    autocomplete_fields = (
        "staff",
        "department",
        "service_area",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
