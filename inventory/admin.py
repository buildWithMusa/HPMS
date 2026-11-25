from django.contrib import admin

from .models import (
    StockLocation,
    StockBatch,
    StockBalance,
    StockMovement,
)


@admin.register(StockLocation)
class StockLocationAdmin(admin.ModelAdmin):
    list_display = ("name", "location_type", "ward", "is_active")
    list_filter = ("location_type", "is_active")
    search_fields = ("name", "ward__name")
    readonly_fields = ("created_at", "updated_at")


@admin.register(StockBatch)
class StockBatchAdmin(admin.ModelAdmin):
    list_display = (
        "medicine",
        "batch_number",
        "manufacture_date",
        "expiry_date",
        "purchase_price",
        "selling_price",
        "is_active",
    )
    list_filter = ("is_active", "expiry_date")
    search_fields = ("medicine__generic_name", "batch_number")
    list_select_related = ("medicine",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(StockBalance)
class StockBalanceAdmin(admin.ModelAdmin):
    list_display = ("batch", "location", "quantity", "updated_at")
    list_filter = ("location",)
    search_fields = ("batch__medicine__generic_name", "batch__batch_number")
    list_select_related = ("batch", "location")


@admin.register(StockMovement)
class StockMovementAdmin(admin.ModelAdmin):
    list_display = (
        "batch",
        "movement_type",
        "source_location",
        "destination_location",
        "quantity",
        "performed_by",
        "created_at",
    )
    list_filter = ("movement_type", "created_at")
    search_fields = (
        "batch__batch_number",
        "batch__medicine__generic_name",
        "reference",
    )
    list_select_related = (
        "batch",
        "batch__medicine",
        "source_location",
        "destination_location",
        "performed_by",
    )
    readonly_fields = (
        "batch",
        "movement_type",
        "source_location",
        "destination_location",
        "quantity",
        "performed_by",
        "reference",
        "notes",
        "created_at",
    )
