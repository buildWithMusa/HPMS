
from django.contrib import admin

from .models import Department, ServiceArea, Ward


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "name",
        "is_active",
        "created_at",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "code",
        "name",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(ServiceArea)
class ServiceAreaAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "name",
        "department",
        "area_type",
        "is_active",
    )

    list_filter = (
        "department",
        "area_type",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
        "department__name",
    )

    autocomplete_fields = (
        "department",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )


@admin.register(Ward)
class WardAdmin(admin.ModelAdmin):

    list_display = (
        "code",
        "name",
        "service_area",
        "ward_type",
        "capacity",
        "is_active",
    )

    list_filter = (
        "ward_type",
        "service_area",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
        "service_area__name",
    )

    autocomplete_fields = (
        "service_area",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
    )
