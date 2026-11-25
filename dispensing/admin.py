from django.contrib import admin
from .models import Dispensing, DispensingBatchAllocation


class DispensingBatchAllocationInline(admin.TabularInline):
    model = DispensingBatchAllocation
    extra = 0
    readonly_fields = ("batch", "quantity", "stock_movement")
    can_delete = False


@admin.register(Dispensing)
class DispensingAdmin(admin.ModelAdmin):
    list_display = (
        "reference", "prescription", "prescription_line",
        "quantity", "dispensed_by", "created_at",
    )
    list_filter = ("created_at",)
    search_fields = (
        "reference", "prescription__prescription_number",
        "prescription__patient__hospital_number",
    )
    readonly_fields = (
        "reference", "prescription", "prescription_line",
        "quantity", "dispensed_by", "notes", "created_at",
    )
    inlines = [DispensingBatchAllocationInline]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
