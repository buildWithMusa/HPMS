
from django.contrib import admin
from .models import Medicine, MedicineCategory


@admin.register(MedicineCategory)
class MedicineCategoryAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "is_active",
        "created_at",
    )

    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Medicine)
class MedicineAdmin(admin.ModelAdmin):
    list_display = (
        "generic_name",
        "brand_name",
        "category",
        "strength",
        "dosage_form",
        "unit_of_measure",
        "is_active",
    )

    search_fields = (
        "generic_name",
        "brand_name",
        "strength",
    )

    list_filter = (
        "category",
        "dosage_form",
        "unit_of_measure",
        "is_active",
    )

    list_select_related = ("category",)

    readonly_fields = (
        "created_at",
        "updated_at",
    )
