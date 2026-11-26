from django.contrib import admin

from .models import Invoice, InvoiceLine, Payment


class InvoiceLineInline(admin.TabularInline):
    model = InvoiceLine
    extra = 0
    readonly_fields = (
        "dispensing_allocation",
        "medicine_name",
        "batch_number",
        "quantity",
        "unit_price",
        "line_total",
    )


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "reference",
        "patient",
        "total_amount",
        "status",
        "created_at",
    )
    list_filter = ("status",)
    search_fields = (
        "reference",
        "patient__first_name",
        "patient__last_name",
    )
    readonly_fields = (
        "reference",
        "dispensing",
        "patient",
        "total_amount",
        "created_by",
        "created_at",
        "updated_at",
    )
    inlines = [InvoiceLineInline]


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_reference",
        "invoice",
        "method",
        "amount",
        "status",
        "initiated_by",
        "created_at",
    )
    list_filter = ("method", "status")
    search_fields = (
        "transaction_reference",
        "receipt_number",
        "invoice__reference",
    )
    readonly_fields = [
        field.name for field in Payment._meta.fields
    ]


    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
